"""
Redis Event Publisher Implementation

Fallback event publisher using Redis pub/sub.
Used when NATS is unavailable.
"""

import os
import json
import logging
from typing import Optional, List

from redis.asyncio import Redis

from app.domain.ports.event_port import EventPort, DomainEvent


logger = logging.getLogger(__name__)


class RedisEventPublisher(EventPort):
    """
    Redis-based event publisher implementing EventPort.

    Publishes events via Redis pub/sub as fallback when NATS unavailable.
    Note: Redis pub/sub is not durable - messages lost if no subscribers.
    """

    def __init__(self, redis_url: str = None):
        """
        Initialize Redis event publisher.

        Args:
            redis_url: Redis server URL (defaults to REDIS_URL env var or localhost)
        """
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self._client: Optional[Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to Redis server."""
        try:
            self._client = await Redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self._client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self._redis_url}")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self._connected = False

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("Disconnected from Redis")

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish event via Redis pub/sub.

        Events are published to channel: trading:{event_type}
        Example: trading:signal.received, trading:order.placed

        Args:
            event: Domain event to publish
        """
        if not self._connected:
            logger.warning(f"Redis not connected, event dropped: {event.event_type}")
            return

        try:
            # Build Redis channel from event type
            channel = f"trading:{event.event_type.value}"

            # Serialize event to JSON
            payload = self._serialize_event(event)

            # Publish to Redis
            subscribers = await self._client.publish(channel, payload)
            logger.debug(f"Published event to {channel} ({subscribers} subscribers)")

        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")

    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """
        Publish multiple events.

        Note: Redis pub/sub doesn't support batch operations,
        so events are published sequentially.

        Args:
            events: List of domain events to publish
        """
        for event in events:
            await self.publish(event)

    def _serialize_event(self, event: DomainEvent) -> str:
        """
        Serialize domain event to JSON string.

        Args:
            event: Domain event to serialize

        Returns:
            JSON-encoded string
        """
        event_dict = {
            "event_type": event.event_type.value,
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat(),
            "aggregate_id": event.aggregate_id,
            "correlation_id": event.correlation_id,
        }
        return json.dumps(event_dict)
