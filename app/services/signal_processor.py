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
from app.domain.services.symbol_normalization_service import SymbolNormalizationService
from app.services.signal_deduplication_service import (
    SignalDeduplicationService,
    DuplicateCheckResult,
    DeduplicationScope
)
from app.models.database_models import RejectedSignal, RejectedSignalReason, TradingAccount

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
        self.symbol_service = SymbolNormalizationService()
        
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

            # Get available symbols and resolve the signal symbol
            symbols = await broker.get_symbols()
            original_symbol = signal_request.symbol

            # Try to resolve symbol if not directly available
            if signal_request.symbol not in symbols:
                # Get user_id from signal_request if available, default to 0 for system
                user_id = getattr(signal_request, 'user_id', 0) or 0

                resolved_symbol = await self._resolve_symbol_for_broker(
                    source_symbol=signal_request.symbol,
                    user_id=user_id,
                    broker_type=signal_request.broker,
                    available_symbols=symbols
                )

                if resolved_symbol and resolved_symbol != signal_request.symbol:
                    logger.info(
                        f"Symbol resolved: {original_symbol} -> {resolved_symbol} "
                        f"for broker {signal_request.broker}"
                    )
                    # Update signal request with resolved symbol
                    signal_request.symbol = resolved_symbol
                elif resolved_symbol is None:
                    return {
                        "valid": False,
                        "error": f"Symbol {signal_request.symbol} not available on {signal_request.broker}"
                    }

            # Risk management checks
            risk_check = await self._check_risk_limits(signal_request)
            if not risk_check["passed"]:
                return {
                    "valid": False,
                    "error": risk_check["error"]
                }

            return {"valid": True, "resolved_symbol": signal_request.symbol}

        except Exception as e:
            logger.error(f"Error validating signal: {e}")
            return {
                "valid": False,
                "error": f"Validation error: {str(e)}"
            }

    async def _resolve_symbol_for_broker(
        self,
        source_symbol: str,
        user_id: int,
        broker_type: str,
        available_symbols: List[str]
    ) -> Optional[str]:
        """
        Resolve TradingView symbol to broker format.

        Uses SymbolNormalizationService for resolution:
        1. Check user aliases first
        2. Check auto-detected aliases
        3. Check known static mappings
        4. Try fuzzy matching against available symbols

        Args:
            source_symbol: TradingView symbol
            user_id: User ID for alias lookup
            broker_type: Target broker type
            available_symbols: List of symbols available on broker

        Returns:
            Resolved symbol or original if no match (graceful degradation)
        """
        try:
            # Try to get alias repository for user-specific resolution
            alias_repository = None
            try:
                from app.infrastructure.repositories.symbol_alias_repository import SQLAlchemySymbolAliasRepository
                from sqlalchemy.ext.asyncio import AsyncSession
                from app.db.database import get_async_session

                # Only use repository if user_id is valid
                if user_id and user_id > 0:
                    async for session in get_async_session():
                        alias_repository = SQLAlchemySymbolAliasRepository(session)
                        break
            except Exception as e:
                logger.debug(f"Could not initialize alias repository: {e}")

            # Use normalization service for resolution
            resolved = await self.symbol_service.resolve_symbol(
                user_id=user_id or 0,
                source_symbol=source_symbol,
                broker_type=broker_type,
                available_symbols=available_symbols,
                alias_repository=alias_repository
            )

            if resolved:
                return resolved

            # Fallback to original symbol (let broker handle error)
            logger.warning(
                f"Could not resolve symbol {source_symbol} for {broker_type}, "
                f"using original"
            )
            return source_symbol

        except Exception as e:
            logger.error(f"Error resolving symbol: {e}")
            return source_symbol
    
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

    async def _check_deduplication(
        self,
        signal_request: SignalRequest,
        account_id: int,
        user_id: int
    ) -> Dict[str, Any]:
        """
        Check for duplicate entry signals.

        Prevents entering a new position when one already exists in the same direction.
        Close/exit signals bypass this check. Reversal signals are allowed.

        Args:
            signal_request: The incoming signal request
            account_id: Internal account ID (not account number)
            user_id: User ID for global scope and rejection logging

        Returns:
            Dict with 'passed' bool and 'error' string if blocked
        """
        try:
            db = next(get_db())

            # Get user to check deduplication settings
            from app.models.models import User
            user = db.query(User).filter(User.id == user_id).first()

            # Check if deduplication is enabled for this user (default: True)
            enable_deduplication = getattr(user, 'enable_deduplication', True) if user else True
            if not enable_deduplication:
                logger.debug(f"Deduplication disabled for user {user_id}")
                return {"passed": True}

            # Get deduplication scope (default: per_account)
            scope_str = getattr(user, 'deduplication_scope', 'per_account') if user else 'per_account'
            scope = DeduplicationScope.GLOBAL if scope_str == 'global' else DeduplicationScope.PER_ACCOUNT

            # Create deduplication service and check
            dedup_service = SignalDeduplicationService(db)
            result = dedup_service.check_duplicate_entry(
                account_id=account_id,
                symbol=signal_request.symbol,
                action=signal_request.action,
                user_id=user_id,
                scope=scope
            )

            if result.is_duplicate:
                # Log rejection to database
                self._log_duplicate_rejection(
                    db=db,
                    user_id=user_id,
                    account_id=account_id,
                    signal_request=signal_request,
                    result=result
                )

                return {
                    "passed": False,
                    "error": f"Duplicate entry: position already open for {signal_request.symbol} in {result.existing_direction} direction"
                }

            return {"passed": True}

        except Exception as e:
            logger.error(f"Error checking deduplication: {e}")
            return {"passed": True}  # Allow on error (fail open)

    def _log_duplicate_rejection(
        self,
        db: Session,
        user_id: int,
        account_id: int,
        signal_request: SignalRequest,
        result: DuplicateCheckResult
    ):
        """Log a duplicate entry rejection to the database"""
        try:
            rejection = RejectedSignal(
                user_id=user_id,
                account_id=account_id,
                symbol=signal_request.symbol,
                action=signal_request.action,
                quantity=signal_request.quantity,
                source=getattr(signal_request, 'source', 'unknown'),
                reason=RejectedSignalReason.DUPLICATE_ENTRY,
                reason_detail=f"Position already open in {result.existing_direction} direction (ID: {result.existing_position_id})",
                limit_value=1.0,  # Max positions per symbol per direction
                current_value=1.0,  # Existing position count
                original_payload=signal_request.dict() if hasattr(signal_request, 'dict') else None
            )
            db.add(rejection)
            db.commit()
            logger.info(f"Logged duplicate entry rejection for account {account_id}, symbol {signal_request.symbol}")
        except Exception as e:
            logger.error(f"Failed to log duplicate rejection: {e}")
            db.rollback()

    async def _calculate_position_size(
        self,
        signal_request: SignalRequest,
        account
    ) -> float:
        """Calculate position size for signal based on account settings"""
        from app.domain.services.position_sizing_service import (
            PositionSizingService, PositionSizingConfig, PositionSizingMode
        )
        from app.domain.services.symbol_specs_service import SymbolSpecsService

        sizing_service = PositionSizingService()
        specs_service = SymbolSpecsService(self.brokers)

        # Build config from account settings
        config = PositionSizingConfig(
            mode=PositionSizingMode(account.position_sizing_mode or "fixed"),
            fixed_lot_size=account.fixed_lot_size or 0.01,
            percent_of_balance=account.percent_of_balance or 1.0,
            percent_of_equity=account.percent_of_equity or 1.0,
            risk_percent_per_trade=account.risk_percent_per_trade or 1.0,
            max_position_size=account.max_position_size
        )

        # Get symbol specs
        specs = await specs_service.get_specs(
            signal_request.symbol,
            signal_request.broker
        )

        # Calculate stop loss pips if provided
        stop_loss_pips = None
        if signal_request.stop_loss and signal_request.price:
            stop_loss_pips = sizing_service.calculate_stop_loss_pips(
                signal_request.price,
                signal_request.stop_loss,
                specs.digits
            )

        # Calculate position size
        result = sizing_service.calculate_position_size(
            config=config,
            balance=account.balance or 10000,  # Default if not synced
            equity=account.equity or account.balance or 10000,
            symbol_specs=specs,
            stop_loss_pips=stop_loss_pips
        )

        logger.info(
            f"Position size calculated: {result.adjusted_size} lots "
            f"({result.mode_used}: {result.calculation_detail})"
        )

        return result.adjusted_size
    
    async def _execute_signal(self, signal_request: SignalRequest, signal_id: str) -> Dict[str, Any]:
        """Execute signal on appropriate broker"""
        try:
            broker = self.brokers[signal_request.broker]

            # Get account for sizing
            from app.models.database_models import TradingAccount
            db = next(get_db())
            account = db.query(TradingAccount).filter(
                TradingAccount.account_number == str(signal_request.account_id)
            ).first()

            # Calculate position size if account found and not using fixed mode
            quantity = signal_request.quantity
            if account and account.position_sizing_mode and account.position_sizing_mode != "fixed":
                try:
                    quantity = await self._calculate_position_size(signal_request, account)
                    logger.info(f"Position size adjusted: {signal_request.quantity} -> {quantity} lots")
                except Exception as e:
                    logger.warning(f"Position sizing failed, using signal quantity: {e}")

            # Convert signal to order
            order_request = OrderRequest(
                account_id=signal_request.account_id,
                symbol=signal_request.symbol,
                order_type=self._map_action_to_order_type(signal_request.action),
                quantity=quantity,
                price=signal_request.price,
                stop_loss=signal_request.stop_loss,
                take_profit=signal_request.take_profit,
                magic_number=signal_request.magic_number,
                comment=signal_request.comment or f"Signal {signal_id}"
            )

            # Execute order
            order_response = await broker.place_order(order_request)

            if order_response.success:
                # Update account balance after successful trade
                if account:
                    await self._update_account_balance(account.id, signal_request.broker)

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

    async def _update_account_balance(self, account_id: int, broker_type: str):
        """Refresh account balance after trade"""
        try:
            from app.models.database_models import TradingAccount
            db = next(get_db())
            account = db.query(TradingAccount).filter(
                TradingAccount.id == account_id
            ).first()

            if not account:
                return

            broker = self.brokers.get(broker_type)
            if not broker:
                return

            # Get fresh account info
            account_info = await broker.get_account_info(account.account_number)
            if account_info:
                account.balance = account_info.get('balance', account.balance)
                account.equity = account_info.get('equity', account.equity)
                account.free_margin = account_info.get('free_margin', account.free_margin)
                account.last_sync = datetime.utcnow()
                db.commit()

                logger.debug(f"Updated account {account_id} balance: ${account.balance}")

        except Exception as e:
            logger.warning(f"Failed to update account balance: {e}")
    
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