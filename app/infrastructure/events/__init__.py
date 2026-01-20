"""
Event Publisher Implementations Package

Contains concrete implementations of EventPort for publishing domain events:
- NatsEventPublisher: Publishes events to NATS message broker (primary)
- RedisEventPublisher: Publishes events via Redis Pub/Sub (fallback)
- CompositeEventPublisher: Multi-backend with automatic fallback

Each publisher:
- Implements app.domain.ports.event_port.EventPort
- Handles event serialization for the target system
- Manages connection lifecycle to event infrastructure
- Supports both single and batch event publishing
"""

from app.infrastructure.events.nats_event_publisher import (
    NatsEventPublisher,
    CompositeEventPublisher,
)
from app.infrastructure.events.redis_event_publisher import RedisEventPublisher

__all__ = [
    "NatsEventPublisher",
    "RedisEventPublisher",
    "CompositeEventPublisher",
]
