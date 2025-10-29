"""
Redis 连接管理
"""
from redis.asyncio import Redis
from typing import Optional

from app.config import settings

_redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """
    获取 Redis 客户端实例（单例模式）

    Returns:
        Redis: Redis 异步客户端实例
    """
    global _redis_client

    if _redis_client is None:
        # 创建 Redis 连接
        _redis_client = Redis.from_url(
            settings.REDIS_URL,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=False,  # 保持字节响应，用于存储二进制数据
            encoding="utf-8"
        )

    return _redis_client


async def close_redis():
    """
    关闭 Redis 连接
    在应用关闭时调用
    """
    global _redis_client

    if _redis_client:
        await _redis_client.close()
        _redis_client = None


async def ping_redis() -> bool:
    """
    测试 Redis 连接是否正常

    Returns:
        bool: 连接正常返回 True，否则返回 False
    """
    try:
        redis = await get_redis()
        await redis.ping()
        return True
    except Exception:
        return False
