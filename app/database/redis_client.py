"""
Redis client for caching
"""

import json
import redis
from typing import Any, Optional
from ..config import settings


class RedisClient:
    """Redis client wrapper"""
    
    def __init__(self):
        self.redis = redis.from_url(settings.redis_url, decode_responses=True)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            return self.redis.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            print(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            return bool(self.redis.delete(key))
        except Exception as e:
            print(f"Redis delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            return bool(self.redis.exists(key))
        except Exception as e:
            print(f"Redis exists error: {e}")
            return False
    
    def set_hash(self, key: str, field: str, value: Any, ttl: int = 3600) -> bool:
        """Set hash field with TTL"""
        try:
            self.redis.hset(key, field, json.dumps(value, default=str))
            self.redis.expire(key, ttl)
            return True
        except Exception as e:
            print(f"Redis hset error: {e}")
            return False
    
    def get_hash(self, key: str, field: str) -> Optional[Any]:
        """Get hash field value"""
        try:
            value = self.redis.hget(key, field)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Redis hget error: {e}")
            return None
    
    def get_all_hash(self, key: str) -> dict:
        """Get all hash fields"""
        try:
            hash_data = self.redis.hgetall(key)
            return {k: json.loads(v) for k, v in hash_data.items()}
        except Exception as e:
            print(f"Redis hgetall error: {e}")
            return {}
    
    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return self.redis.ping()
        except Exception as e:
            print(f"Redis ping error: {e}")
            return False


# Global Redis client instance
redis_client = RedisClient()


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