import redis
import json
import logging
from typing import Optional, Any, Dict, List
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    async def ping(self) -> bool:
        """Check Redis connection"""
        if self.redis_client:
            try:
                return self.redis_client.ping()
            except Exception as e:
                logger.error(f"Redis ping failed: {e}")
                return False
        return False
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set key-value pair with optional expiration"""
        if not self.redis_client:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            ttl = expire or settings.REDIS_CACHE_TTL
            return self.redis_client.set(key, serialized_value, ex=ttl)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value by key"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete key"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis_client:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern"""
        if not self.redis_client:
            return []
        
        try:
            return self.redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"Redis keys error for pattern {pattern}: {e}")
            return []
    
    async def hset(self, name: str, key: str, value: Any) -> bool:
        """Set hash field"""
        if not self.redis_client:
            return False
        
        try:
            serialized_value = json.dumps(value, default=str)
            return bool(self.redis_client.hset(name, key, serialized_value))
        except Exception as e:
            logger.error(f"Redis hset error for {name}.{key}: {e}")
            return False
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """Get hash field"""
        if not self.redis_client:
            return None
        
        try:
            value = self.redis_client.hget(name, key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis hget error for {name}.{key}: {e}")
            return None
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """Get all hash fields"""
        if not self.redis_client:
            return {}
        
        try:
            hash_data = self.redis_client.hgetall(name)
            result = {}
            for key, value in hash_data.items():
                try:
                    result[key] = json.loads(value)
                except:
                    result[key] = value
            return result
        except Exception as e:
            logger.error(f"Redis hgetall error for {name}: {e}")
            return {}
    
    async def publish(self, channel: str, message: Any) -> bool:
        """Publish message to channel"""
        if not self.redis_client:
            return False
        
        try:
            serialized_message = json.dumps(message, default=str)
            return bool(self.redis_client.publish(channel, serialized_message))
        except Exception as e:
            logger.error(f"Redis publish error for channel {channel}: {e}")
            return False
    
    async def subscribe(self, channels: List[str]):
        """Subscribe to channels (returns pubsub object)"""
        if not self.redis_client:
            return None
        
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            logger.error(f"Redis subscribe error for channels {channels}: {e}")
            return None

# Global Redis client instance
redis_client = RedisClient()