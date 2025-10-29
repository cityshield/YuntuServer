"""
API 限流器 - 基于 Redis 滑动窗口算法
实现蓝图文档 8.3.3 节的限流策略
"""
from datetime import datetime
from typing import Optional, Tuple
from redis.asyncio import Redis
from fastapi import HTTPException, status, Request

from app.db.redis import get_redis


class RateLimiter:
    """
    Redis 滑动窗口限流器

    使用 Redis Sorted Set 实现滑动窗口算法:
    - Key: rate_limit:{resource_type}:{identifier}
    - Score: 时间戳
    - Value: 请求唯一ID (时间戳)
    """

    def __init__(self, redis: Redis):
        self.redis = redis

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        identifier: str = ""
    ) -> Tuple[bool, dict]:
        """
        检查是否超过限流阈值

        Args:
            key: 限流键前缀 (如 'login', 'sms')
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口大小(秒)
            identifier: 标识符 (IP地址、手机号、用户ID等)

        Returns:
            Tuple[bool, dict]: (是否允许, 限流信息)
                - bool: True=允许请求, False=限流
                - dict: {
                    'limit': 最大请求数,
                    'remaining': 剩余请求数,
                    'reset': 重置时间戳,
                    'retry_after': 重试等待秒数 (仅限流时)
                  }
        """
        now = datetime.utcnow().timestamp()
        window_start = now - window_seconds

        # 构建完整的 Redis key
        rate_limit_key = f"rate_limit:{key}:{identifier}"

        # 清除窗口外的请求记录
        await self.redis.zremrangebyscore(rate_limit_key, 0, window_start)

        # 统计当前窗口内的请求数
        current_requests = await self.redis.zcard(rate_limit_key)

        # 判断是否超限
        if current_requests >= max_requests:
            # 获取最早的请求时间,计算重置时间
            oldest_request = await self.redis.zrange(rate_limit_key, 0, 0, withscores=True)
            if oldest_request:
                oldest_timestamp = oldest_request[0][1]
                reset_time = oldest_timestamp + window_seconds
                retry_after = int(reset_time - now)
            else:
                reset_time = now + window_seconds
                retry_after = window_seconds

            return False, {
                'limit': max_requests,
                'remaining': 0,
                'reset': int(reset_time),
                'retry_after': max(1, retry_after)
            }

        # 允许请求,记录本次请求
        await self.redis.zadd(rate_limit_key, {str(now): now})

        # 设置 key 的过期时间 (避免内存泄漏)
        await self.redis.expire(rate_limit_key, window_seconds)

        # 计算剩余请求数
        remaining = max_requests - current_requests - 1

        return True, {
            'limit': max_requests,
            'remaining': remaining,
            'reset': int(now + window_seconds)
        }

    async def check_multiple_limits(
        self,
        limits: list[dict],
    ) -> Tuple[bool, dict]:
        """
        检查多个限流规则 (全部通过才允许)

        Args:
            limits: 限流规则列表,每个规则包含:
                - key: 限流键
                - max_requests: 最大请求数
                - window_seconds: 时间窗口
                - identifier: 标识符

        Returns:
            Tuple[bool, dict]: (是否允许, 限流信息)

        Example:
            limits = [
                {'key': 'sms', 'max_requests': 1, 'window_seconds': 60, 'identifier': '13800138000'},
                {'key': 'sms', 'max_requests': 5, 'window_seconds': 3600, 'identifier': '13800138000'},
                {'key': 'sms_ip', 'max_requests': 10, 'window_seconds': 3600, 'identifier': '1.2.3.4'},
            ]
        """
        for limit in limits:
            allowed, info = await self.check_rate_limit(
                key=limit['key'],
                max_requests=limit['max_requests'],
                window_seconds=limit['window_seconds'],
                identifier=limit['identifier']
            )

            if not allowed:
                # 任意一个规则超限即返回
                return False, info

        # 所有规则都通过,返回最严格的限制信息
        return True, info


async def check_rate_limit_dependency(
    request: Request,
    key: str,
    max_requests: int,
    window_seconds: int,
    identifier_type: str = "ip"
) -> None:
    """
    FastAPI 依赖注入函数 - 单一限流检查

    Args:
        request: FastAPI Request 对象
        key: 限流键前缀
        max_requests: 最大请求数
        window_seconds: 时间窗口(秒)
        identifier_type: 标识符类型 ('ip', 'user_id')

    Raises:
        HTTPException: 429 Too Many Requests
    """
    redis = await get_redis()
    limiter = RateLimiter(redis)

    # 获取标识符
    if identifier_type == "ip":
        identifier = request.client.host
    elif identifier_type == "user_id":
        # 从 request.state 中获取用户ID (需要在认证中间件中设置)
        identifier = getattr(request.state, "user_id", request.client.host)
    else:
        identifier = request.client.host

    # 检查限流
    allowed, info = await limiter.check_rate_limit(
        key=key,
        max_requests=max_requests,
        window_seconds=window_seconds,
        identifier=identifier
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "message": f"请求过于频繁,请在 {info['retry_after']} 秒后重试",
                "limit": info['limit'],
                "retry_after": info['retry_after'],
                "reset": info['reset']
            },
            headers={
                "X-RateLimit-Limit": str(info['limit']),
                "X-RateLimit-Remaining": str(info['remaining']),
                "X-RateLimit-Reset": str(info['reset']),
                "Retry-After": str(info['retry_after'])
            }
        )


def get_client_ip(request: Request) -> str:
    """
    获取客户端真实 IP 地址

    考虑代理、负载均衡器的 X-Forwarded-For 和 X-Real-IP 头部

    Args:
        request: FastAPI Request 对象

    Returns:
        str: 客户端 IP 地址
    """
    # 优先从 X-Forwarded-For 获取 (nginx/CDN)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For: client, proxy1, proxy2
        # 取第一个IP (客户端真实IP)
        return forwarded_for.split(",")[0].strip()

    # 其次从 X-Real-IP 获取
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # 最后使用直连IP
    return request.client.host if request.client else "unknown"
