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
        """Initialize NATS connection if available - non-blocking, graceful fallback"""
        if not NATS_AVAILABLE:
            logger.info("NATS library not available, using logging fallback")
            self.nats_connected = False
            return

        self.nats_url = nats_url or "nats://nats:4222"
        logger.info(f"Attempting to connect to NATS at {self.nats_url}...")

        try:
            # Try to connect with aggressive timeout to avoid blocking startup
            import asyncio
            # Use shorter timeout and explicit connection parameters
            self.nats_client = await asyncio.wait_for(
                nats.connect(
                    self.nats_url,
                    max_reconnect_attempts=0,  # No retries
                    connect_timeout=2,  # 2 second connection timeout
                    allow_reconnect=False,  # Disable reconnection
                    verbose=False  # Reduce logging noise
                ),
                timeout=2.0  # 2 second overall timeout
            )
            self.nats_connected = True
            logger.info(f"✅ Connected to NATS at {self.nats_url}")
        except asyncio.TimeoutError:
            logger.warning(f"⚠️  NATS connection timed out after 2 seconds at {self.nats_url}")
            logger.warning("⚠️  Continuing without NATS - events will be logged instead")
            self.nats_connected = False
            self.nats_client = None
        except Exception as e:
            logger.warning(f"⚠️  Failed to connect to NATS at {self.nats_url}: {type(e).__name__}: {e}")
            logger.warning("⚠️  Continuing without NATS - events will be logged instead")
            self.nats_connected = False
            self.nats_client = None
    
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
