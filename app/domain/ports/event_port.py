"""
Event Port Interface

Abstract interface for domain event publishing.
Adapters (NATS, Redis PubSub, WebSocket, etc.) implement this interface.
Domain services publish events through this interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """Domain event types"""
    SIGNAL_RECEIVED = "signal.received"
    SIGNAL_PROCESSED = "signal.processed"
    SIGNAL_FAILED = "signal.failed"

    ORDER_PLACED = "order.placed"
    ORDER_FILLED = "order.filled"
    ORDER_CANCELLED = "order.cancelled"
    ORDER_REJECTED = "order.rejected"

    POSITION_OPENED = "position.opened"
    POSITION_CLOSED = "position.closed"
    POSITION_MODIFIED = "position.modified"

    TRADE_EXECUTED = "trade.executed"
    TRADE_CLOSED = "trade.closed"

    ACCOUNT_CONNECTED = "account.connected"
    ACCOUNT_DISCONNECTED = "account.disconnected"
    ACCOUNT_MARGIN_CALL = "account.margin_call"
    ACCOUNT_STOP_OUT = "account.stop_out"


@dataclass
class DomainEvent:
    """
    Domain event representing something that happened.

    Events are immutable records of domain state changes.
    """
    event_type: EventType
    payload: Dict[str, Any]
    timestamp: datetime
    aggregate_id: Optional[str] = None  # ID of the entity that generated event
    correlation_id: Optional[str] = None  # For tracing across systems

    @classmethod
    def create(cls, event_type: EventType, payload: Dict[str, Any],
               aggregate_id: Optional[str] = None,
               correlation_id: Optional[str] = None) -> "DomainEvent":
        """Factory method to create a new domain event with current timestamp"""
        return cls(
            event_type=event_type,
            payload=payload,
            timestamp=datetime.utcnow(),
            aggregate_id=aggregate_id,
            correlation_id=correlation_id,
        )


class EventPort(ABC):
    """
    Port interface for event publishing.

    Adapters (NATS, Redis PubSub, WebSocket, etc.) implement this interface.
    Domain services publish events through this interface.
    """

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event.
        Implementation handles delivery to subscribers.
        """
        pass

    @abstractmethod
    async def publish_batch(self, events: list[DomainEvent]) -> None:
        """
        Publish multiple events atomically if possible.
        """
        pass
