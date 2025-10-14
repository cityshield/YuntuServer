"""
简单的内存缓存实现
用于存储验证码等临时数据
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger


class SimpleCache:
    """简单的内存缓存"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def set(self, key: str, value: Any, expire: int = 0) -> bool:
        """
        设置缓存

        Args:
            key: 缓存键
            value: 缓存值
            expire: 过期时间(秒)，0表示永不过期

        Returns:
            bool: 是否设置成功
        """
        async with self._lock:
            expire_at = None
            if expire > 0:
                expire_at = datetime.now() + timedelta(seconds=expire)

            self._cache[key] = {
                "value": value,
                "expire_at": expire_at
            }

            logger.debug(f"Cache set: {key} = {value}, expire in {expire}s")
            return True

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            Any: 缓存值，不存在或已过期返回None
        """
        async with self._lock:
            if key not in self._cache:
                return None

            item = self._cache[key]

            # 检查是否过期
            if item["expire_at"] and datetime.now() > item["expire_at"]:
                del self._cache[key]
                logger.debug(f"Cache expired and removed: {key}")
                return None

            logger.debug(f"Cache get: {key} = {item['value']}")
            return item["value"]

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            bool: 是否删除成功
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache deleted: {key}")
                return True
            return False

    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            bool: 是否存在
        """
        value = await self.get(key)
        return value is not None

    async def ttl(self, key: str) -> int:
        """
        获取缓存剩余过期时间

        Args:
            key: 缓存键

        Returns:
            int: 剩余秒数，-1表示永不过期，-2表示不存在
        """
        async with self._lock:
            if key not in self._cache:
                return -2

            item = self._cache[key]
            if not item["expire_at"]:
                return -1

            remaining = (item["expire_at"] - datetime.now()).total_seconds()
            if remaining <= 0:
                del self._cache[key]
                return -2

            return int(remaining)

    async def clear(self) -> bool:
        """清空所有缓存"""
        async with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
            return True

    async def cleanup_expired(self):
        """清理过期的缓存项"""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, item in self._cache.items()
                if item["expire_at"] and now > item["expire_at"]
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache items")


# 创建全局缓存实例
cache = SimpleCache()
