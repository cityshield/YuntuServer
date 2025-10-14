"""
Redis 客户端
"""
import redis.asyncio as redis
from typing import Optional

from app.config import settings


class RedisClient:
    """Redis 客户端单例"""

    _instance: Optional[redis.Redis] = None

    @classmethod
    async def get_instance(cls) -> redis.Redis:
        """获取 Redis 实例"""
        if cls._instance is None:
            cls._instance = await redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                encoding="utf-8",
                decode_responses=True,
            )
        return cls._instance

    @classmethod
    async def close(cls):
        """关闭 Redis 连接"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None


async def get_redis() -> redis.Redis:
    """依赖注入：获取 Redis 客户端"""
    return await RedisClient.get_instance()
