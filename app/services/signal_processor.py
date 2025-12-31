"""
Signal Processor Service
Handles signal processing, routing, and execution across all brokers
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import settings
from app.cache.redis_client import redis_client
from app.models.models import Signal, WebhookLog, Account as AccountModel
from app.models.pydantic_schemas import (
    SignalRequest, SignalResponse, OrderRequest, OrderResponse,
    TradeRequest, TradeResponse, WebhookRequest
)
from app.brokers.mt4_executor import MT4Executor
from app.brokers.mt5_executor import MT5Executor
from app.brokers.tradelocker_executor import TradeLockerExecutor
from app.brokers.tradovate_executor import TradovateExecutor
from app.brokers.projectx_executor import ProjectXExecutor
from app.db.database import get_db

logger = logging.getLogger(__name__)

class SignalProcessor:
    """Unified signal processor for all brokers"""
    
    def __init__(self):
        self.brokers = {
            "mt4": MT4Executor(),
            "mt5": MT5Executor(),
            "tradelocker": TradeLockerExecutor(),
            "tradovate": TradovateExecutor(),
            "projectx": ProjectXExecutor()
        }
        self.active_connections = {}
        self.signal_queue = asyncio.Queue()
        
    async def initialize(self):
        """Initialize all broker connections"""
        for broker_name, broker in self.brokers.items():
            try:
                success = await broker.initialize()
                if success:
                    logger.info(f"Initialized {broker_name} broker")
                else:
                    logger.warning(f"Failed to initialize {broker_name} broker")
            except Exception as e:
                logger.error(f"Error initializing {broker_name}: {e}")
    
    async def shutdown(self):
        """Shutdown all broker connections"""
        for broker_name, broker in self.brokers.items():
            try:
                await broker.disconnect()
                logger.info(f"Disconnected {broker_name} broker")
            except Exception as e:
                logger.error(f"Error disconnecting {broker_name}: {e}")
    
    async def process_signal(self, signal_request: SignalRequest) -> SignalResponse:
        """Process trading signal and route to appropriate broker"""
        try:
            # Log signal
            signal_id = await self._log_signal(signal_request)
            
            # Validate signal
            validation_result = await self._validate_signal(signal_request)
            if not validation_result["valid"]:
                return SignalResponse(
                    success=False,
                    signal_id=signal_id,
                    error=validation_result["error"],
                    timestamp=datetime.now()
                )
            
            # Route signal to broker
            execution_result = await self._execute_signal(signal_request, signal_id)
            
            # Update signal status
            await self._update_signal_status(signal_id, execution_result)
            
            return SignalResponse(
                success=execution_result["success"],
                signal_id=signal_id,
                order_id=execution_result.get("order_id"),
                broker=execution_result.get("broker"),
                status=execution_result.get("status"),
                error=execution_result.get("error"),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return SignalResponse(
                success=False,
                error=str(e),
                timestamp=datetime.now()
            )
    
    async def _log_signal(self, signal_request: SignalRequest) -> str:
        """Log signal to database"""
        try:
            db = next(get_db())
            
            # Extract strategy info if present
            strategy_info = {}
            if isinstance(signal_request, dict) and "strategy_info" in signal_request:
                strategy_info = signal_request["strategy_info"]
            elif hasattr(signal_request, "strategy_info"):
                strategy_info = signal_request.strategy_info or {}
            
            signal = Signal(
                broker=signal_request.broker if hasattr(signal_request, "broker") else signal_request.get("broker"),
                account_id=signal_request.account_id if hasattr(signal_request, "account_id") else signal_request.get("account_id"),
                symbol=signal_request.symbol if hasattr(signal_request, "symbol") else signal_request.get("symbol"),
                action=signal_request.action if hasattr(signal_request, "action") else signal_request.get("action"),
                quantity=signal_request.quantity if hasattr(signal_request, "quantity") else signal_request.get("quantity"),
                price=signal_request.price if hasattr(signal_request, "price") else signal_request.get("price"),
                stop_loss=signal_request.stop_loss if hasattr(signal_request, "stop_loss") else signal_request.get("stop_loss"),
                take_profit=signal_request.take_profit if hasattr(signal_request, "take_profit") else signal_request.get("take_profit"),
                magic_number=signal_request.magic_number if hasattr(signal_request, "magic_number") else signal_request.get("magic_number"),
                comment=signal_request.comment if hasattr(signal_request, "comment") else signal_request.get("comment"),
                source=signal_request.source if hasattr(signal_request, "source") else signal_request.get("source", "unknown"),
                status="pending",
                # Strategy tracking fields
                strategy_id=strategy_info.get("strategy_id"),
                strategy_version=strategy_info.get("strategy_version"),
                strategy_name=strategy_info.get("strategy_name"),
                strategy_source="tradingview" if strategy_info else "manual",
                created_at=datetime.now()
            )
            
            db.add(signal)
            db.commit()
            db.refresh(signal)
            
            signal_id = str(signal.id)
            
            # Also cache to Redis
            await redis_client.set(
                f"signal:{signal_id}",
                json.dumps({
                    "id": signal_id,
                    "status": "pending",
                    "created_at": signal.created_at.isoformat()
                }),
                ex=3600
            )
            
            return signal_id
            
        except Exception as e:
            logger.error(f"Error logging signal: {e}")
            return f"signal_{datetime.now().timestamp()}"
    
    async def _validate_signal(self, signal_request: SignalRequest) -> Dict[str, Any]:
        """Validate signal request"""
        try:
            # Check if broker is supported
            if signal_request.broker not in self.brokers:
                return {
                    "valid": False,
                    "error": f"Unsupported broker: {signal_request.broker}"
                }
            
            # Check if broker is connected
            broker = self.brokers[signal_request.broker]
            if not broker.is_connected:
                return {
                    "valid": False,
                    "error": f"Broker {signal_request.broker} is not connected"
                }
            
            # Validate account
            account = await broker.get_account_info(signal_request.account_id)
            if not account:
                return {
                    "valid": False,
                    "error": f"Account {signal_request.account_id} not found"
                }
            
            # Validate symbol
            symbols = await broker.get_symbols()
            if signal_request.symbol not in symbols:
                return {
                    "valid": False,
                    "error": f"Symbol {signal_request.symbol} not available"
                }
            
            # Risk management checks
            risk_check = await self._check_risk_limits(signal_request)
            if not risk_check["passed"]:
                return {
                    "valid": False,
                    "error": risk_check["error"]
                }
            
            return {"valid": True}
            
        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }
    
    async def _check_risk_limits(self, signal_request: SignalRequest) -> Dict[str, Any]:
        """Check risk management limits"""
        try:
            if not settings.RISK_MANAGEMENT_ENABLED:
                return {"passed": True}
            
            # Get current positions
            broker = self.brokers[signal_request.broker]
            positions = await broker.get_positions(signal_request.account_id)
            
            # Calculate total exposure
            total_exposure = sum(pos.size for pos in positions if pos.symbol == signal_request.symbol)
            
            # Check maximum position size
            if signal_request.quantity > settings.MAX_POSITION_SIZE:
                return {
                    "passed": False,
                    "error": f"Position size {signal_request.quantity} exceeds maximum {settings.MAX_POSITION_SIZE}"
                }
            
            # Check daily loss limits (would need to implement daily P&L tracking)
            # This is a placeholder for more sophisticated risk management
            
            return {"passed": True}
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return {"passed": True}  # Allow on error
    
    async def _execute_signal(self, signal_request: SignalRequest, signal_id: str) -> Dict[str, Any]:
        """Execute signal on appropriate broker"""
        try:
            broker = self.brokers[signal_request.broker]
            
            # Convert signal to order
            order_request = OrderRequest(
                account_id=signal_request.account_id,
                symbol=signal_request.symbol,
                order_type=self._map_action_to_order_type(signal_request.action),
                quantity=signal_request.quantity,
                price=signal_request.price,
                stop_loss=signal_request.stop_loss,
                take_profit=signal_request.take_profit,
                magic_number=signal_request.magic_number,
                comment=signal_request.comment or f"Signal {signal_id}"
            )
            
            # Execute order
            order_response = await broker.place_order(order_request)
            
            if order_response.success:
                return {
                    "success": True,
                    "order_id": order_response.order_id,
                    "broker": signal_request.broker,
                    "status": order_response.status
                }
            else:
                return {
                    "success": False,
                    "error": order_response.error
                }
                
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _map_action_to_order_type(self, action: str) -> str:
        """Map signal action to order type"""
        action_map = {
            "buy": "market_buy",
            "sell": "market_sell",
            "buy_limit": "buy_limit",
            "sell_limit": "sell_limit",
            "buy_stop": "buy_stop",
            "sell_stop": "sell_stop"
        }
        return action_map.get(action.lower(), "market_buy")
    
    async def _update_signal_status(self, signal_id: str, execution_result: Dict[str, Any]):
        """Update signal status in database and cache"""
        try:
            db = next(get_db())
            
            signal = db.query(Signal).filter(Signal.id == int(signal_id)).first()
            if signal:
                signal.status = "executed" if execution_result["success"] else "failed"
                signal.order_id = execution_result.get("order_id")
                signal.error_message = execution_result.get("error")
                signal.executed_at = datetime.now()
                
                db.commit()
            
            # Update Redis cache
            await redis_client.set(
                f"signal:{signal_id}",
                json.dumps({
                    "id": signal_id,
                    "status": signal.status,
                    "order_id": execution_result.get("order_id"),
                    "updated_at": datetime.now().isoformat()
                }),
                ex=3600
            )
            
        except Exception as e:
            logger.error(f"Error updating signal status: {e}")
    
    async def process_webhook(self, webhook_request: WebhookRequest) -> Dict[str, Any]:
        """Process webhook signal"""
        try:
            # Log webhook
            webhook_id = await self._log_webhook(webhook_request)
            
            # Parse webhook payload
            signal_request = await self._parse_webhook_payload(webhook_request.payload)
            
            if not signal_request:
                return {
                    "success": False,
                    "webhook_id": webhook_id,
                    "error": "Failed to parse webhook payload"
                }
            
            # Process the signal
            signal_response = await self.process_signal(signal_request)
            
            return {
                "success": signal_response.success,
                "webhook_id": webhook_id,
                "signal_id": signal_response.signal_id,
                "order_id": signal_response.order_id,
                "error": signal_response.error
            }
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _log_webhook(self, webhook_request: WebhookRequest) -> str:
        """Log webhook to database"""
        try:
            db = next(get_db())
            
            webhook_log = WebhookLog(
                source=webhook_request.source,
                payload=json.dumps(webhook_request.payload),
                headers=json.dumps(webhook_request.headers),
                ip_address=webhook_request.ip_address,
                user_agent=webhook_request.user_agent,
                status="received",
                created_at=datetime.now()
            )
            
            db.add(webhook_log)
            db.commit()
            db.refresh(webhook_log)
            
            return str(webhook_log.id)
            
        except Exception as e:
            logger.error(f"Error logging webhook: {e}")
            return f"webhook_{datetime.now().timestamp()}"
    
    async def _parse_webhook_payload(self, payload: Dict[str, Any]) -> Optional[SignalRequest]:
        """Parse webhook payload into signal request"""
        try:
            # Handle TradingView webhooks
            if "ticker" in payload and "action" in payload:
                return SignalRequest(
                    broker=self._detect_broker_from_payload(payload),
                    account_id=self._get_account_from_payload(payload),
                    symbol=payload["ticker"],
                    action=payload["action"].lower(),
                    quantity=float(payload.get("quantity", 1)),
                    price=float(payload.get("price", 0)),
                    stop_loss=float(payload.get("stop_loss", 0)),
                    take_profit=float(payload.get("take_profit", 0)),
                    source="tradingview"
                )
            
            # Handle TrailHacker webhooks
            elif "symbol" in payload and "signal" in payload:
                return SignalRequest(
                    broker=self._detect_broker_from_payload(payload),
                    account_id=self._get_account_from_payload(payload),
                    symbol=payload["symbol"],
                    action=payload["signal"].lower(),
                    quantity=float(payload.get("size", 1)),
                    price=float(payload.get("entry", 0)),
                    stop_loss=float(payload.get("stop", 0)),
                    take_profit=float(payload.get("target", 0)),
                    source="trailhacker"
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing webhook payload: {e}")
            return None
    
    def _detect_broker_from_payload(self, payload: Dict[str, Any]) -> str:
        """Detect target broker from payload"""
        # Check for explicit broker specification
        if "broker" in payload:
            return payload["broker"].lower()
        
        # Default to first available broker
        # In production, this would be more sophisticated
        return "mt4"
    
    def _get_account_from_payload(self, payload: Dict[str, Any]) -> str:
        """Get account ID from payload"""
        if "account_id" in payload:
            return str(payload["account_id"])
        elif "account" in payload:
            return str(payload["account"])
        
        # Default account (in production, this would be user-specific)
        return "1"
    
    async def get_signal_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get signal history"""
        try:
            db = next(get_db())
            
            signals = db.query(Signal).order_by(Signal.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": str(signal.id),
                    "broker": signal.broker,
                    "account_id": signal.account_id,
                    "symbol": signal.symbol,
                    "action": signal.action,
                    "quantity": signal.quantity,
                    "price": signal.price,
                    "status": signal.status,
                    "order_id": signal.order_id,
                    "created_at": signal.created_at.isoformat(),
                    "executed_at": signal.executed_at.isoformat() if signal.executed_at else None
                }
                for signal in signals
            ]
            
        except Exception as e:
            logger.error(f"Error getting signal history: {e}")
            return []
    
    async def get_webhook_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get webhook history"""
        try:
            db = next(get_db())
            
            webhooks = db.query(WebhookLog).order_by(WebhookLog.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": str(webhook.id),
                    "source": webhook.source,
                    "status": webhook.status,
                    "ip_address": webhook.ip_address,
                    "created_at": webhook.created_at.isoformat()
                }
                for webhook in webhooks
            ]
            
        except Exception as e:
            logger.error(f"Error getting webhook history: {e}")
            return []

# Global signal processor instance
signal_processor = SignalProcessor()