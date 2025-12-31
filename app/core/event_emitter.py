"""
Event Emitter with NATS Integration
Emits events to NATS if available, falls back to logging
"""
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import NATS
try:
    import nats
    from nats.aio.client import Client as NATS
    NATS_AVAILABLE = True
except ImportError:
    NATS_AVAILABLE = False
    logger.warning("NATS not available, using logging fallback")

class EventEmitter:
    """Event emitter with NATS support and logging fallback"""
    
    def __init__(self):
        self.nats_client: Optional[NATS] = None
        self.nats_connected = False
        self.nats_url = None
        
    async def initialize(self, nats_url: Optional[str] = None):
        """Initialize NATS connection if available"""
        if not NATS_AVAILABLE:
            logger.info("NATS not available, using logging fallback")
            return
        
        self.nats_url = nats_url or "nats://localhost:4222"
        
        try:
            self.nats_client = await nats.connect(self.nats_url)
            self.nats_connected = True
            logger.info(f"Connected to NATS at {self.nats_url}")
        except Exception as e:
            logger.warning(f"Failed to connect to NATS: {e}, using logging fallback")
            self.nats_connected = False
    
    async def emit(self, subject: str, event_type: str, data: Dict[str, Any]):
        """Emit an event to NATS or log it"""
        event = {
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        # Try NATS first
        if self.nats_connected and self.nats_client:
            try:
                await self.nats_client.publish(
                    subject,
                    json.dumps(event).encode()
                )
                logger.debug(f"Emitted event to NATS: {subject}/{event_type}")
                return
            except Exception as e:
                logger.warning(f"Failed to emit to NATS: {e}, falling back to logging")
        
        # Fallback to logging
        logger.info(f"[EVENT] {subject}/{event_type}: {json.dumps(event)}")
    
    async def shutdown(self):
        """Shutdown NATS connection"""
        if self.nats_client and self.nats_connected:
            try:
                await self.nats_client.close()
                logger.info("NATS connection closed")
            except Exception as e:
                logger.error(f"Error closing NATS connection: {e}")

# Global event emitter instance
event_emitter = EventEmitter()

# Convenience functions for common events
async def emit_user_event(event_type: str, user_id: int, data: Dict[str, Any]):
    """Emit user-related event"""
    await event_emitter.emit(
        f"empire.user.{event_type}",
        event_type,
        {"user_id": user_id, **data}
    )

async def emit_account_event(event_type: str, account_id: int, data: Dict[str, Any]):
    """Emit account-related event"""
    await event_emitter.emit(
        f"empire.account.{event_type}",
        event_type,
        {"account_id": account_id, **data}
    )

async def emit_signal_event(event_type: str, signal_id: str, data: Dict[str, Any]):
    """Emit signal-related event"""
    await event_emitter.emit(
        f"empire.signal.{event_type}",
        event_type,
        {"signal_id": signal_id, **data}
    )

async def emit_order_event(event_type: str, order_id: str, data: Dict[str, Any]):
    """Emit order-related event"""
    await event_emitter.emit(
        f"empire.order.{event_type}",
        event_type,
        {"order_id": order_id, **data}
    )

async def emit_position_event(event_type: str, position_id: str, data: Dict[str, Any]):
    """Emit position-related event"""
    await event_emitter.emit(
        f"empire.position.{event_type}",
        event_type,
        {"position_id": position_id, **data}
    )
