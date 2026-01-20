"""
NATS Event Publisher Implementation

Publishes domain events to NATS message broker with graceful degradation.
Primary event publishing mechanism for distributed observability.
"""

import os
import json
import logging
from typing import Optional, List

import nats
from nats.aio.client import Client

from app.domain.ports.event_port import EventPort, DomainEvent


logger = logging.getLogger(__name__)


class NatsEventPublisher(EventPort):
    """
    NATS-based event publisher implementing EventPort.

    Publishes events to NATS JetStream for durable message delivery.
    Degrades gracefully when NATS is unavailable.
    """

    def __init__(self, nats_url: str = None):
        """
        Initialize NATS event publisher.

        Args:
            nats_url: NATS server URL (defaults to NATS_URL env var or localhost)
        """
        self._nats_url = nats_url or os.getenv("NATS_URL", "nats://localhost:4222")
        self._client: Optional[Client] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to NATS server."""
        try:
            self._client = await nats.connect(self._nats_url)
            self._connected = True
            logger.info(f"Connected to NATS at {self._nats_url}")
        except Exception as e:
            logger.warning(f"NATS connection failed: {e}")
            self._connected = False

    async def disconnect(self) -> None:
        """Disconnect from NATS server."""
        if self._client:
            await self._client.close()
            self._connected = False
            logger.info("Disconnected from NATS")

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish single domain event to NATS.

        Events are published to subject: trading.{event_type}
        Example: trading.signal.received, trading.order.placed

        Args:
            event: Domain event to publish
        """
        if not self._connected:
            logger.warning(f"NATS not connected, event dropped: {event.event_type}")
            return

        try:
            # Build NATS subject from event type
            subject = f"trading.{event.event_type.value}"

            # Serialize event to JSON
            payload = self._serialize_event(event)

            # Publish to NATS
            await self._client.publish(subject, payload)
            logger.debug(f"Published event to {subject}")

        except Exception as e:
            logger.error(f"Failed to publish event {event.event_type}: {e}")

    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """
        Publish multiple events.

        Note: NATS doesn't support true batch operations,
        so events are published sequentially.

        Args:
            events: List of domain events to publish
        """
        for event in events:
            await self.publish(event)

    def _serialize_event(self, event: DomainEvent) -> bytes:
        """
        Serialize domain event to JSON bytes.

        Args:
            event: Domain event to serialize

        Returns:
            JSON-encoded bytes
        """
        event_dict = {
            "event_type": event.event_type.value,
            "payload": event.payload,
            "timestamp": event.timestamp.isoformat(),
            "aggregate_id": event.aggregate_id,
            "correlation_id": event.correlation_id,
        }
        return json.dumps(event_dict).encode()


class CompositeEventPublisher(EventPort):
    """
    Publishes to multiple backends with fallback behavior.

    Tries publishers in order until one succeeds.
    Typical configuration: [NatsEventPublisher, RedisEventPublisher]

    This provides resilience when primary event broker is unavailable.
    """

    def __init__(self, publishers: List[EventPort] = None):
        """
        Initialize composite publisher.

        Args:
            publishers: List of event publishers to try in order
        """
        self._publishers = publishers or []

    async def connect(self) -> None:
        """Connect all publishers."""
        for publisher in self._publishers:
            await publisher.connect()

    async def disconnect(self) -> None:
        """Disconnect all publishers."""
        for publisher in self._publishers:
            await publisher.disconnect()

    async def publish(self, event: DomainEvent) -> None:
        """
        Publish event to first available publisher.

        Tries each publisher in order, stops on first success.

        Args:
            event: Domain event to publish
        """
        # Try each publisher, stop on first success
        for publisher in self._publishers:
            try:
                await publisher.publish(event)
                return  # Success - don't try remaining publishers
            except Exception as e:
                logger.debug(f"Publisher {type(publisher).__name__} failed: {e}")
                continue  # Try next publisher

        # All publishers failed
        logger.warning(f"All publishers failed for event {event.event_type}")

    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """
        Publish batch of events.

        Args:
            events: List of domain events to publish
        """
        for event in events:
            await self.publish(event)
