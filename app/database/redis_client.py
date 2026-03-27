"""
In-memory TTL cache (drop-in replacement for Redis).

For a single-process personal tool this is simpler and has no external
dependency. Restart clears the cache, which is fine — data is in SQLite.
"""

import time
from typing import Any, Optional


class InMemoryCache:
    """Simple TTL-based in-memory cache."""

    def __init__(self):
        # key -> (value, expire_at_epoch_seconds | None)
        self._store: dict = {}

    def _expired(self, key: str) -> bool:
        _, exp = self._store[key]
        return exp is not None and time.time() > exp

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        if self._expired(key):
            del self._store[key]
            return None
        return self._store[key][0]

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        self._store[key] = (value, time.time() + ttl)
        return True

    def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    # Hash helpers kept for interface compatibility (stored as plain dicts)
    def set_hash(self, key: str, field: str, value: Any, ttl: int = 3600) -> bool:
        bucket = self.get(key) or {}
        bucket[field] = value
        return self.set(key, bucket, ttl)

    def get_hash(self, key: str, field: str) -> Optional[Any]:
        bucket = self.get(key)
        return bucket.get(field) if bucket else None

    def get_all_hash(self, key: str) -> dict:
        return self.get(key) or {}

    def ping(self) -> bool:
        return True


# Global cache instance
redis_client = InMemoryCache()


# Cache key generators
def get_price_cache_key(symbol: str) -> str:
    """Get price cache key"""
    return f"price:{symbol}"


def get_indicator_cache_key(symbol: str, indicator_type: str) -> str:
    """Get indicator cache key"""
    return f"indicator:{symbol}:{indicator_type}"


def get_risk_gate_cache_key(user_id: int) -> str:
    """Get risk gate cache key"""
    return f"risk_gate:{user_id}"


def get_portfolio_cache_key(user_id: int) -> str:
    """Get portfolio cache key"""
    return f"portfolio:{user_id}" 