"""
Event Publisher Implementations Package

Contains concrete implementations of EventPort for publishing domain events:
- NATSEventPublisher: Publishes events to NATS message broker
- RedisEventPublisher: Publishes events via Redis Pub/Sub
- WebSocketEventPublisher: Broadcasts events to WebSocket clients

Each publisher:
- Implements app.domain.ports.event_port.EventPort
- Handles event serialization for the target system
- Manages connection lifecycle to event infrastructure
- Supports both single and batch event publishing

Implementation in Plan 05-05.
"""

# Event publisher exports
# Will be populated in Plan 05-05

__all__ = [
    # "NATSEventPublisher",
    # "RedisEventPublisher",
    # "WebSocketEventPublisher",
]
