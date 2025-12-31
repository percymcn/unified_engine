"""
Redis cache client
"""
import redis
import json
import os
from typing import Any, Optional
from datetime import timedelta


class RedisCache:
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Redis GET error: {e}")
            return None

    def set(self, key: str, value: Any, expire: Optional[int] = None):
        """Set value in cache with optional expiration (seconds)"""
        try:
            serialized = json.dumps(value)
            if expire:
                self.redis_client.setex(key, expire, serialized)
            else:
                self.redis_client.set(key, serialized)
        except Exception as e:
            print(f"Redis SET error: {e}")

    def delete(self, key: str):
        """Delete key from cache"""
        try:
            self.redis_client.delete(key)
        except Exception as e:
            print(f"Redis DELETE error: {e}")

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            print(f"Redis EXISTS error: {e}")
            return False

    def expire(self, key: str, seconds: int):
        """Set expiration on key"""
        try:
            self.redis_client.expire(key, seconds)
        except Exception as e:
            print(f"Redis EXPIRE error: {e}")

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            print(f"Redis INCREMENT error: {e}")
            return 0

    def get_hash(self, key: str, field: str) -> Optional[str]:
        """Get hash field value"""
        try:
            return self.redis_client.hget(key, field)
        except Exception as e:
            print(f"Redis HGET error: {e}")
            return None

    def set_hash(self, key: str, field: str, value: str):
        """Set hash field value"""
        try:
            self.redis_client.hset(key, field, value)
        except Exception as e:
            print(f"Redis HSET error: {e}")

    def get_all_hash(self, key: str) -> dict:
        """Get all hash fields"""
        try:
            return self.redis_client.hgetall(key)
        except Exception as e:
            print(f"Redis HGETALL error: {e}")
            return {}

    def publish(self, channel: str, message: str):
        """Publish message to channel"""
        try:
            self.redis_client.publish(channel, message)
        except Exception as e:
            print(f"Redis PUBLISH error: {e}")

    def ping(self) -> bool:
        """Check Redis connection"""
        try:
            return self.redis_client.ping()
        except Exception as e:
            print(f"Redis PING error: {e}")
            return False


# Global cache instance
cache = RedisCache()
