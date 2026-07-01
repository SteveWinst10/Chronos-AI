import asyncio
import os
import time
from typing import Optional

from app.core.constants import CACHE_TTL_SECONDS

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = None


class SystemCache:
    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._memory_store: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()
        self._redis = Redis.from_url(redis_url) if Redis and redis_url else None

    async def get(self, key: str) -> Optional[str]:
        if self._redis is not None:
            try:
                value = await self._redis.get(key)
                if value is None:
                    return None
                return value.decode("utf-8") if isinstance(value, bytes) else str(value)
            except Exception:
                self._redis = None

        async with self._lock:
            item = self._memory_store.get(key)
            if item is None:
                return None

            value, expires_at = item
            if expires_at <= time.monotonic():
                self._memory_store.pop(key, None)
                return None

            return value

    async def set(self, key: str, value: str, ttl: int = CACHE_TTL_SECONDS) -> None:
        if self._redis is not None:
            try:
                await self._redis.set(key, value, ex=ttl)
                return
            except Exception:
                self._redis = None

        expires_at = time.monotonic() + ttl
        async with self._lock:
            self._memory_store[key] = (value, expires_at)

    async def clear_expired(self) -> None:
        now = time.monotonic()
        async with self._lock:
            expired_keys = [
                key for key, (_, expires_at) in self._memory_store.items() if expires_at <= now
            ]
            for key in expired_keys:
                self._memory_store.pop(key, None)


cache = SystemCache(redis_url=os.getenv("REDIS_URL"))
