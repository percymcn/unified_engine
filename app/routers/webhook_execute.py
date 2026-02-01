"""
Webhook Execute Endpoint - TradingView Alert Execution

Standardized endpoint for immediate trade execution from TradingView alerts.
Supports multi-account routing with configurable strategies.

Payload format:
{
    "webhook_key": "unique-per-account-key",  // REQUIRED
    "action": "buy" | "sell" | "close",       // REQUIRED
    "symbol": "EURUSD",                       // REQUIRED
    "quantity": 0.1,                          // Optional, default 0.01
    "sl": 1.0800,                             // Optional stop loss
    "tp": 1.0900,                             // Optional take profit
    "timestamp": "2026-01-25T10:00:00Z",      // Optional for staleness check
    "strategy_id": "my_strategy",             // Optional (used for rules_based routing)
    "comment": "TV alert",                    // Optional
    "target_account_ids": [1, 2, 3]           // Optional: override routing to specific accounts
}

Routing Strategies (configured in WebhookConfig):
- direct_account_key: Webhook key matches a single account's webhook_key
- all_accounts: Route to all signal-enabled accounts for the user
- specific_accounts: Route to accounts in specific_account_ids list
- rules_based: Apply routing_rules by symbol/strategy
- default_only: Route only to default_account_id
"""
import logging
import uuid
import json
import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.models.models import WebhookLog, ExecutionLog, BrokerType as ModelsBrokerType, Signal as SignalORM, SignalSource as ModelsSignalSource, SymbolAlias
from app.models.database_models import TradingAccount, DiscardBin, WebhookConfig
from app.models.schemas import WebhookLogCreate
from app.dependencies import get_container
from app.application.dto.signal_dto import ProcessSignalRequest
from app.domain.enums import SignalSource, SignalAction
from app.services.signal_intelligence_guard import SignalIntelligenceGuard, GuardDecision
from app.domain.entities.signal import Signal
from app.domain.value_objects import SignalId, Symbol, Volume, Price, StopLoss, TakeProfit, AccountId
from app.domain.services.account_routing_service import AccountRoutingService

logger = logging.getLogger(__name__)


def resolve_symbol_for_broker(
    db: Session,
    user_id: int,
    source_symbol: str,
    broker_type: str
) -> str:
    """
    Resolve a source symbol to the broker-specific format using symbol aliases.

    Looks up user's symbol alias table to map TradingView symbols to broker-specific formats.
    E.g., "BTCUSD" -> "BTC/USD" for TradeLocker, or "BTCUSD" -> "BTCUSD.ecn" for MT5.

    Args:
        db: Database session
        user_id: User ID to look up aliases for
        source_symbol: The incoming symbol (e.g., from TradingView)
        broker_type: The broker type (e.g., "tradelocker", "mt5", "projectx")

    Returns:
        The mapped symbol for the broker, or the original symbol if no mapping found.
    """
    source_upper = source_symbol.upper().strip()
    broker_lower = broker_type.lower().strip()

    # Look up alias for this user/symbol/broker combination
    alias = db.query(SymbolAlias).filter(
        SymbolAlias.user_id == user_id,
        SymbolAlias.source_symbol == source_upper,
        SymbolAlias.broker_type == broker_lower
    ).first()

    if alias and alias.target_symbol:
        logger.info(f"Symbol mapped: {source_symbol} -> {alias.target_symbol} for {broker_type}")
        return alias.target_symbol

    # No alias found - return original symbol
    return source_symbol


router = APIRouter()


class TradingViewPayload(BaseModel):
    """Standardized TradingView webhook payload"""
    webhook_key: str = Field(..., description="Unique webhook key for account identification")
    action: str = Field(..., description="Trade action: buy, sell, or close")
    symbol: str = Field(..., description="Trading symbol")
    quantity: Optional[float] = Field(0.01, description="Trade quantity/lots")
    sl: Optional[float] = Field(None, description="Stop loss price (alias: stop_loss)")
    tp: Optional[float] = Field(None, description="Take profit price (alias: take_profit)")
    stop_loss: Optional[float] = Field(None, description="Stop loss price (alias: sl)")
    take_profit: Optional[float] = Field(None, description="Take profit price (alias: tp)")
    trailing_stop: Optional[float] = Field(None, description="Trailing stop distance (in ticks for ProjectX)")
    order_type: Optional[str] = Field("market", description="Order type: market or limit")
    limit_price: Optional[float] = Field(None, description="Limit price for limit orders")
    timestamp: Optional[str] = Field(None, description="Signal timestamp for staleness check")
    strategy_id: Optional[str] = Field(None, description="Strategy identifier")
    comment: Optional[str] = Field(None, description="Trade comment")
    target_account_ids: Optional[List[int]] = Field(None, description="Override routing to specific accounts")


class AccountExecutionResult(BaseModel):
    """Result for a single account execution"""
    account_id: int
    broker: str
    success: bool
    status: str
    error: Optional[str] = None
    execution_id: Optional[str] = None


class ExecuteResponse(BaseModel):
    """Standard execution response with multi-account support"""
    success: bool
    signal_id: str
    status: str  # executed, partial, rejected, paused, failed
    webhook_id: str
    routing_strategy: str = "default_only"
    routing_reason: Optional[str] = None
    total_accounts: int = 0
    successful_accounts: int = 0
    failed_accounts: int = 0
    account_results: List[AccountExecutionResult] = []
    # Legacy single-account fields for backwards compatibility
    account_id: Optional[int] = None
    broker: Optional[str] = None
    errors: list = []
    guard_decision: Optional[str] = None
    guard_reason: Optional[str] = None
    modal_data: Optional[Dict[str, Any]] = None
    processing_time_ms: int = 0


def log_event(event_type: str, **kwargs):
    """Structured logging helper (structlog-compatible format)"""
    log_data = {"event": event_type, "ts": datetime.utcnow().isoformat(), **kwargs}
    logger.info(json.dumps(log_data))


@router.post("/execute", response_model=ExecuteResponse)
async def execute_tradingview_signal(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Execute a TradingView signal immediately.

    Flow:
    1. Parse JSON payload → require webhook_key
    2. Lookup account by webhook_key
    3. Run signal intelligence guard
    4. Execute via broker if approved
    5. Persist execution log

    Returns:
        200: Execution completed (success or failure)
        202: Awaiting confirmation (guard modal required)
        403: Invalid webhook_key
        422: Invalid payload
    """
    start_time = datetime.utcnow()
    webhook_id = str(uuid.uuid4())

    try:
        # Parse JSON payload
        raw_payload = await request.json()
    except Exception as e:
        logger.warning(f"Invalid JSON payload: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON payload"
        )

    # Log webhook received
    log_event("webhook_received", webhook_id=webhook_id, has_key=bool(raw_payload.get("webhook_key")))

    # Validate required fields
    webhook_key = raw_payload.get("webhook_key")
    if not webhook_key:
        log_event("webhook_rejected_missing_key", webhook_id=webhook_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required field: webhook_key"
        )

    action_str = raw_payload.get("action", "").lower()
    if action_str not in ["buy", "sell", "close"]:
        log_event("webhook_rejected_invalid_action", webhook_id=webhook_id, action=action_str)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid action: {action_str}. Must be 'buy', 'sell', or 'close'"
        )

    # Accept both 'symbol' and 'ticker' for compatibility with different brokers
    symbol = raw_payload.get("symbol") or raw_payload.get("ticker")
    if not symbol:
        log_event("webhook_rejected_missing_symbol", webhook_id=webhook_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required field: symbol or ticker"
        )

    # Create webhook log
    try:
        webhook_log = WebhookLog(
            webhook_id=webhook_id,
            source="tradingview",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(raw_payload)
        )
        db.add(webhook_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to create webhook log: {e}")

    # Global try/except to ensure errors are always saved to webhook_log
    try:
        return await _execute_tradingview_signal_inner(
            request=request,
            db=db,
            webhook_id=webhook_id,
            webhook_log=webhook_log,
            raw_payload=raw_payload,
            webhook_key=webhook_key,
            action_str=action_str,
            symbol=symbol,
            start_time=start_time
        )
    except HTTPException:
        # Re-raise HTTP exceptions (they have their own error handling)
        raise
    except Exception as e:
        # Catch-all: save error to webhook_log
        logger.exception(f"Unhandled error in webhook execution: {e}")
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        try:
            if 'webhook_log' in locals() and webhook_log:
                webhook_log.processed = False
                webhook_log.error_message = str(e)[:500]
                webhook_log.response_status = 500
                webhook_log.processing_time_ms = processing_time_ms
                webhook_log.response_body = json.dumps({
                    "success": False,
                    "error": str(e)[:200],
                    "errors": [f"Internal error: {str(e)[:200]}"],
                    "processing_time_ms": processing_time_ms
                })
                db.commit()
        except Exception as log_err:
            logger.error(f"Failed to save error to webhook_log: {log_err}")
            db.rollback()

        return ExecuteResponse(
            success=False,
            signal_id=None,
            status="error",
            webhook_id=webhook_id,
            errors=[str(e)[:200]],
            processing_time_ms=processing_time_ms
        )


async def _execute_tradingview_signal_inner(
    request: Request,
    db: Session,
    webhook_id: str,
    webhook_log: WebhookLog,
    raw_payload: dict,
    webhook_key: str,
    action_str: str,
    symbol: str,
    start_time: datetime
):
    """Inner implementation of webhook execution with all the main logic."""
    # === MULTI-ACCOUNT ROUTING ===
    routing_service = AccountRoutingService(db)
    strategy_id = raw_payload.get("strategy_id")
    target_account_ids_override = raw_payload.get("target_account_ids")

    # If payload specifies target_account_ids, use them directly
    if target_account_ids_override:
        accounts = db.query(TradingAccount).filter(
            TradingAccount.id.in_(target_account_ids_override),
            TradingAccount.is_active == True
        ).all()
        routing_strategy = "payload_override"
        routing_reason = f"Target accounts specified in payload: {target_account_ids_override}"
        user_id = accounts[0].user_id if accounts else 0
    else:
        # Use routing service to resolve accounts
        routing_decision = routing_service.resolve_accounts(
            webhook_key=webhook_key,
            symbol=symbol,
            strategy_id=strategy_id,
            action=action_str
        )
        accounts = routing_decision.accounts
        routing_strategy = routing_decision.strategy_used
        routing_reason = routing_decision.reason
        user_id = routing_decision.user_id

    # Log routing decision
    log_event(
        "routing_decision",
        webhook_id=webhook_id,
        strategy=routing_strategy,
        reason=routing_reason,
        account_count=len(accounts),
        account_ids=[a.id for a in accounts] if accounts else []
    )

    if not accounts:
        log_event(
            "webhook_rejected_invalid_key",
            webhook_id=webhook_id,
            webhook_key_prefix=webhook_key[:12] + "..." if len(webhook_key) > 12 else webhook_key
        )

        # Log to discard_bin
        try:
            discard_entry = DiscardBin(
                user_id=0,  # Unknown user
                received_at=datetime.utcnow(),
                reason="invalid_webhook_key",
                age_ms=0,
                symbol=symbol,
                side=action_str,
                raw_payload=json.dumps(raw_payload)[:500]
            )
            db.add(discard_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log discard: {e}")

        # Update webhook log
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        try:
            webhook_log.processed = False
            webhook_log.response_status = 403
            webhook_log.error_message = "Invalid webhook_key - no accounts found"
            webhook_log.processing_time_ms = processing_time_ms
            webhook_log.response_body = json.dumps({
                "success": False,
                "error": "Invalid webhook_key",
                "errors": ["Invalid webhook_key - no accounts found for routing"],
                "processing_time_ms": processing_time_ms
            })
            db.commit()
        except:
            pass

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook_key. Signal not executed."
        )

    # Accounts found - log context
    log_event(
        "webhook_accounts_resolved",
        webhook_id=webhook_id,
        account_ids=[a.id for a in accounts],
        user_id=user_id,
        brokers=[a.broker.value if hasattr(a.broker, 'value') else str(a.broker) for a in accounts],
        routing_strategy=routing_strategy
    )

    # Map action
    action_map = {
        "buy": SignalAction.BUY,
        "sell": SignalAction.SELL,
        "close": SignalAction.CLOSE,
    }
    action = action_map[action_str]

    # Build signal entity for guard evaluation
    # Accept quantity, contracts, or volume for compatibility with different brokers
    quantity = float(
        raw_payload.get("quantity") or
        raw_payload.get("contracts") or
        raw_payload.get("volume") or
        0.01
    )
    # Support both short (sl, tp) and long (stop_loss, take_profit) field names
    sl_price = raw_payload.get("sl") or raw_payload.get("stop_loss")
    tp_price = raw_payload.get("tp") or raw_payload.get("take_profit")
    trailing_stop = raw_payload.get("trailing_stop")  # Trailing stop distance
    order_type_payload = raw_payload.get("order_type", "market").lower()
    limit_price = raw_payload.get("limit_price")
    signal_uuid = str(uuid.uuid4())

    signal_entity = Signal(
        id=SignalId(signal_uuid),
        source=SignalSource.TRADINGVIEW,
        symbol=Symbol(symbol),
        action=action,
        volume=Volume(Decimal(str(quantity))),
        price=None,  # Market order
        stop_loss=StopLoss(Price(Decimal(str(sl_price)))) if sl_price else None,
        take_profit=TakeProfit(Price(Decimal(str(tp_price)))) if tp_price else None,
        target_accounts=[AccountId(str(a.id)) for a in accounts],
        comment=raw_payload.get("comment"),
        strategy_id=raw_payload.get("strategy_id"),
        strategy_name=None,
        raw_payload=raw_payload,
    )

    # === PERSIST SIGNAL TO DATABASE ===
    # This must happen before any ExecutionLog entries (foreign key constraint)
    try:
        signal_orm = SignalORM(
            signal_id=signal_uuid,
            user_id=accounts[0].user_id if accounts else None,
            source=ModelsSignalSource.TRADINGVIEW,
            symbol=symbol,
            action=action_str.upper(),
            volume=quantity,
            price=None,  # Market order
            stop_loss=float(sl_price) if sl_price else None,
            take_profit=float(tp_price) if tp_price else None,
            comment=raw_payload.get("comment"),
            status="pending"
        )
        db.add(signal_orm)
        db.commit()
        logger.debug(f"Persisted signal {signal_uuid} to database")
    except Exception as e:
        logger.error(f"Failed to persist signal: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist signal: {e}"
        )

    # === SIGNAL INTELLIGENCE GUARD ===
    guard = SignalIntelligenceGuard(db)

    # Get open positions summary for ALL target accounts
    open_positions_summary = {}
    try:
        from app.models.models import Position
        for account in accounts:
            positions = db.query(Position).filter(
                Position.account_id == account.id,
                Position.status == "open"
            ).all()
            total_margin = sum(p.margin or 0.0 for p in positions) if positions else (account.margin or 0.0)
            open_positions_summary[account.id] = {
                "total_margin": total_margin,
                "positions_count": len(positions) if positions else 0
            }
    except Exception as e:
        logger.debug(f"Could not query positions: {e}")
        for account in accounts:
            open_positions_summary[account.id] = {"total_margin": account.margin or 0.0, "positions_count": 0}

    # Evaluate guard (using first account for user context)
    first_account = accounts[0]
    guard_result = await guard.evaluate(
        signal=signal_entity,
        user_id=first_account.user_id,
        account_ids=[a.id for a in accounts],
        open_positions_summary=open_positions_summary
    )

    # Log guard decision
    log_event(
        "guard_decision",
        webhook_id=webhook_id,
        signal_id=signal_entity.id.value,
        account_ids=[a.id for a in accounts],
        decision=guard_result.decision.value,
        annotations=guard_result.annotations
    )

    # Handle guard decisions
    processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    if guard_result.decision == GuardDecision.SKIP:
        # Signal discarded (stale, etc.)
        guard_reason = guard_result.annotations.get("discard_reason") or guard_result.annotations.get("history_tag") or "guard_rejected"
        try:
            webhook_log.processed = False
            webhook_log.response_status = 200
            webhook_log.processing_time_ms = processing_time_ms
            webhook_log.response_body = json.dumps({
                "signal_id": signal_entity.id.value,
                "status": "rejected",
                "guard_decision": "skip",
                "guard_reason": guard_reason,
                "total_accounts": len(accounts),
                "successful": 0,
                "failed": len(accounts),
            })
            db.commit()

            # Create ExecutionLog entries for each account showing the rejection
            for account in accounts:
                try:
                    broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker)
                    models_broker = ModelsBrokerType(broker_str.lower())
                    exec_log = ExecutionLog(
                        signal_id=signal_entity.id.value,
                        account_id=account.id,
                        broker=models_broker,
                        action=action_str.upper(),
                        symbol=symbol,
                        volume=float(quantity),
                        status="failed",
                        error_message=f"Guard rejected: {guard_reason}",
                        execution_time_ms=processing_time_ms,
                    )
                    db.add(exec_log)
                except Exception as e:
                    logger.warning(f"Failed to create rejection ExecutionLog: {e}")
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to update webhook_log for SKIP: {e}")

        return ExecuteResponse(
            success=False,
            signal_id=signal_entity.id.value,
            status="rejected",
            webhook_id=webhook_id,
            routing_strategy=routing_strategy,
            routing_reason=routing_reason,
            total_accounts=len(accounts),
            account_id=first_account.id,
            broker=first_account.broker.value if hasattr(first_account.broker, 'value') else str(first_account.broker),
            guard_decision="skip",
            guard_reason=guard_result.annotations.get("discard_reason", "guard_rejected"),
            processing_time_ms=processing_time_ms
        )

    if guard_result.decision == GuardDecision.WARN_MODAL_REQUIRED:
        # Needs user confirmation
        try:
            webhook_log.processed = False
            webhook_log.response_status = 202
            webhook_log.response_body = json.dumps({"status": "pending_confirmation"})
            webhook_log.processing_time_ms = processing_time_ms
            db.commit()
        except:
            pass

        # Persist signal for UI confirmation flow
        try:
            existing_signal = db.query(SignalORM).filter(
                SignalORM.signal_id == signal_entity.id.value
            ).first()
            if not existing_signal:
                db_signal = SignalORM(
                    signal_id=signal_entity.id.value,
                    user_id=first_account.user_id,
                    source=ModelsSignalSource.TRADINGVIEW,
                    symbol=symbol,
                    action=action_str,
                    volume=float(quantity),
                    price=None,
                    stop_loss=float(sl_price) if sl_price else None,
                    take_profit=float(tp_price) if tp_price else None,
                    comment=raw_payload.get("comment"),
                    status="pending_confirmation",
                    target_accounts=[a.id for a in accounts],
                    raw_payload=raw_payload,
                    signal_data={
                        "guard_decision": "warn",
                        "guard_reason": guard_result.annotations.get("history_tag", "momentum_warning"),
                        "annotations": guard_result.annotations,
                        "modal_data": guard_result.modal_data,
                        "routing_strategy": routing_strategy,
                    },
                    strategy_id=raw_payload.get("strategy_id"),
                )
                db.add(db_signal)
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist pending confirmation signal: {e}")

        return ExecuteResponse(
            success=False,
            signal_id=signal_entity.id.value,
            status="pending_confirmation",
            webhook_id=webhook_id,
            routing_strategy=routing_strategy,
            routing_reason=routing_reason,
            total_accounts=len(accounts),
            account_id=first_account.id,
            broker=first_account.broker.value if hasattr(first_account.broker, 'value') else str(first_account.broker),
            guard_decision="warn",
            guard_reason=guard_result.annotations.get("history_tag", "momentum_warning"),
            modal_data=guard_result.modal_data,
            processing_time_ms=processing_time_ms
        )

    if guard_result.decision == GuardDecision.PAUSE_NEW_ENTRIES:
        # Paused - don't execute new entries
        if action != SignalAction.CLOSE:
            guard_reason = guard_result.annotations.get("history_tag") or "paused_new_entries"
            try:
                webhook_log.processed = False
                webhook_log.response_status = 200
                webhook_log.processing_time_ms = processing_time_ms
                webhook_log.response_body = json.dumps({
                    "signal_id": signal_entity.id.value,
                    "status": "paused",
                    "guard_decision": "pause",
                    "guard_reason": guard_reason,
                    "total_accounts": len(accounts),
                    "successful": 0,
                    "failed": len(accounts),
                })
                db.commit()

                # Create ExecutionLog entries for each account showing the pause
                for account in accounts:
                    try:
                        broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker)
                        models_broker = ModelsBrokerType(broker_str.lower())
                        exec_log = ExecutionLog(
                            signal_id=signal_entity.id.value,
                            account_id=account.id,
                            broker=models_broker,
                            action=action_str.upper(),
                            symbol=symbol,
                            volume=float(quantity),
                            status="failed",
                            error_message=f"Paused: {guard_reason}",
                            execution_time_ms=processing_time_ms,
                        )
                        db.add(exec_log)
                    except Exception as e:
                        logger.warning(f"Failed to create pause ExecutionLog: {e}")
                db.commit()
            except Exception as e:
                logger.warning(f"Failed to update webhook_log for PAUSE: {e}")

            return ExecuteResponse(
                success=False,
                signal_id=signal_entity.id.value,
                status="paused",
                webhook_id=webhook_id,
                routing_strategy=routing_strategy,
                routing_reason=routing_reason,
                total_accounts=len(accounts),
                account_id=first_account.id,
                broker=first_account.broker.value if hasattr(first_account.broker, 'value') else str(first_account.broker),
                guard_decision="pause",
                guard_reason=guard_reason,
                modal_data=guard_result.modal_data,
                processing_time_ms=processing_time_ms
            )

    # === EXECUTE ON ALL TARGET ACCOUNTS ===
    # Guard passed - execute the signal on all routed accounts using account-specific executors
    account_results: List[AccountExecutionResult] = []
    all_errors: List[str] = []
    successful_count = 0
    failed_count = 0

    # Import the account-specific executor creation
    from app.services.signal_processor import _create_account_executor
    from app.models.pydantic_schemas import OrderRequest

    for account in accounts:
        account_start = datetime.utcnow()
        broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker)

        # Resolve symbol for this specific broker (symbol mapping)
        # Do this early so it's available for both execution and logging
        mapped_symbol = resolve_symbol_for_broker(
            db=db,
            user_id=account.user_id,
            source_symbol=symbol,
            broker_type=broker_str
        )

        try:
            # Create account-specific executor with credentials
            executor, needs_cleanup = await _create_account_executor(account, db)

            if not executor:
                raise Exception(f"Could not create executor for {broker_str}")

            # Ensure executor is initialized
            if not getattr(executor, 'is_connected', False):
                try:
                    await executor.initialize()
                except Exception as init_err:
                    logger.warning(f"Executor init warning for account {account.id}: {init_err}")

            # Handle close action separately - need to find and close positions
            if action_str == "close":
                # Helper to get attribute from dict or object
                def get_attr(obj, key, default=''):
                    if isinstance(obj, dict):
                        return obj.get(key, default)
                    return getattr(obj, key, default)

                # Get positions and close matching ones (check both original and mapped symbol)
                try:
                    positions = await executor.get_positions()
                    matching_positions = [
                        p for p in (positions or [])
                        if symbol.upper() in (get_attr(p, 'symbol', '') or '').upper()
                        or mapped_symbol.upper() in (get_attr(p, 'symbol', '') or '').upper()
                    ]

                    if not matching_positions:
                        # No positions to close - return success
                        order_result = type('Result', (), {
                            'success': True,
                            'order_id': 'no_positions',
                            'error': None
                        })()
                    else:
                        # Close each matching position
                        closed = 0
                        close_errors = []
                        for pos in matching_positions:
                            pos_id = get_attr(pos, 'id') or get_attr(pos, 'position_id') or get_attr(pos, 'contract_id')
                            if pos_id:
                                close_result = await executor.close_position(str(pos_id), quantity if quantity > 0 else None)
                                if close_result.success if hasattr(close_result, 'success') else close_result.get('success'):
                                    closed += 1
                                else:
                                    err = close_result.error if hasattr(close_result, 'error') else close_result.get('error')
                                    if err:
                                        close_errors.append(str(err))

                        order_result = type('Result', (), {
                            'success': closed > 0,
                            'order_id': f'closed_{closed}',
                            'error': '; '.join(close_errors) if close_errors and closed == 0 else None
                        })()
                except Exception as close_err:
                    logger.error(f"Error during close: {close_err}")
                    order_result = type('Result', (), {
                        'success': False,
                        'order_id': None,
                        'error': str(close_err)
                    })()
            else:
                # Build order request - support market, limit, and trailing stop
                effective_order_type = f"{order_type_payload}_{action_str}"  # e.g., "market_buy", "limit_sell"
                order_request = OrderRequest(
                    account_id=account.id,
                    symbol=mapped_symbol,  # Use broker-specific symbol
                    order_type=effective_order_type,
                    quantity=quantity,
                    price=limit_price,  # For limit orders
                    stop_loss=sl_price,
                    take_profit=tp_price,
                    trailing_stop=trailing_stop,  # For trailing stop orders
                    comment=raw_payload.get("comment"),  # Trade comment for MT4/MT5
                )

                # Execute the order directly
                order_result = await executor.place_order(order_request)
            execution_success = order_result.success if hasattr(order_result, 'success') else order_result.get('success', False)
            execution_error = order_result.error if hasattr(order_result, 'error') else order_result.get('error')
            order_id = order_result.order_id if hasattr(order_result, 'order_id') else order_result.get('order_id')

            # Cleanup executor if needed
            if needs_cleanup and hasattr(executor, 'disconnect'):
                try:
                    await executor.disconnect()
                except:
                    pass

            # Build result similar to use_case response
            class UseCaseResult:
                def __init__(self, success, error=None, order_id=None):
                    self.status = type('Status', (), {'value': 'executed' if success else 'failed'})()
                    self.executions = 1 if success else 0
                    self.errors = [error] if error and not success else []
                    self.signal_id = order_id

            use_case_result = UseCaseResult(execution_success, execution_error, order_id)

            # Log execution result
            log_event(
                "account_execution_result",
                webhook_id=webhook_id,
                signal_id=signal_uuid,
                account_id=account.id,
                broker=broker_str,
                success=execution_success,
                status=use_case_result.status.value,
                executions=use_case_result.executions,
                errors=use_case_result.errors
            )

            # Persist execution log for this account (use mapped_symbol to show what was actually sent)
            try:
                models_broker = ModelsBrokerType(broker_str.lower())
                exec_log = ExecutionLog(
                    signal_id=signal_uuid,
                    account_id=account.id,
                    broker=models_broker,
                    action=action_str.upper(),
                    symbol=mapped_symbol,  # Use the broker-specific mapped symbol
                    volume=quantity,
                    price=None,
                    status="success" if execution_success else "failed",
                    broker_response={"executions": use_case_result.executions, "original_symbol": symbol} if execution_success else None,
                    error_message="; ".join(use_case_result.errors) if use_case_result.errors else None,
                    execution_time_ms=int((datetime.utcnow() - account_start).total_seconds() * 1000)
                )
                db.add(exec_log)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to persist execution log for account {account.id}: {e}")
                db.rollback()

            if execution_success:
                successful_count += 1
                account_results.append(AccountExecutionResult(
                    account_id=account.id,
                    broker=broker_str,
                    success=True,
                    status="executed",
                    execution_id=use_case_result.signal_id
                ))
            else:
                failed_count += 1
                error_msg = "; ".join(use_case_result.errors) if use_case_result.errors else "Unknown error"
                all_errors.append(f"Account {account.id}: {error_msg}")
                account_results.append(AccountExecutionResult(
                    account_id=account.id,
                    broker=broker_str,
                    success=False,
                    status="failed",
                    error=error_msg
                ))

        except Exception as e:
            logger.exception(f"Execution error for account {account.id}: {e}")
            failed_count += 1
            error_msg = str(e)
            all_errors.append(f"Account {account.id}: {error_msg}")

            # Persist failed execution log (use mapped_symbol to show what was attempted)
            try:
                db.rollback()
                models_broker = ModelsBrokerType(broker_str.lower())
                exec_log = ExecutionLog(
                    signal_id=signal_uuid,
                    account_id=account.id,
                    broker=models_broker,
                    action=action_str.upper(),
                    symbol=mapped_symbol,  # Use the broker-specific mapped symbol
                    volume=quantity,
                    status="failed",
                    error_message=error_msg,
                    execution_time_ms=int((datetime.utcnow() - account_start).total_seconds() * 1000)
                )
                db.add(exec_log)
                db.commit()
            except Exception as log_err:
                logger.error(f"Failed to persist error log: {log_err}")
                db.rollback()

            account_results.append(AccountExecutionResult(
                account_id=account.id,
                broker=broker_str,
                success=False,
                status="failed",
                error=error_msg
            ))

    # Determine overall status
    processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    if successful_count == len(accounts):
        overall_status = "executed"
        overall_success = True
    elif successful_count > 0:
        overall_status = "partial"
        overall_success = True  # At least one succeeded
    else:
        overall_status = "failed"
        overall_success = False

    # === UPDATE SIGNAL STATUS IN DATABASE ===
    try:
        signal_to_update = db.query(SignalORM).filter(
            SignalORM.signal_id == signal_uuid
        ).first()
        if signal_to_update:
            signal_to_update.status = overall_status
            signal_to_update.updated_at = datetime.utcnow()
            # Store execution results in signal_data
            signal_to_update.signal_data = {
                **(signal_to_update.signal_data or {}),
                "execution_results": {
                    "total_accounts": len(accounts),
                    "successful": successful_count,
                    "failed": failed_count,
                    "errors": all_errors,
                    "processing_time_ms": processing_time_ms,
                }
            }
            db.commit()
            logger.debug(f"Updated signal {signal_uuid} status to {overall_status}")
    except Exception as e:
        logger.error(f"Failed to update signal status: {e}")
        db.rollback()

    # Update webhook log
    try:
        webhook_log.processed = overall_success
        webhook_log.response_status = 200
        webhook_log.processing_time_ms = processing_time_ms
        webhook_log.response_body = json.dumps({
            "signal_id": signal_uuid,
            "status": overall_status,
            "total_accounts": len(accounts),
            "successful": successful_count,
            "failed": failed_count,
            "errors": all_errors[:3] if all_errors else [],  # Limit errors stored
        })
        db.commit()
    except:
        pass

    # Log overall result
    log_event(
        "multi_account_execution_complete",
        webhook_id=webhook_id,
        signal_id=signal_uuid,
        total_accounts=len(accounts),
        successful=successful_count,
        failed=failed_count,
        routing_strategy=routing_strategy
    )

    return ExecuteResponse(
        success=overall_success,
        signal_id=signal_uuid,
        status=overall_status,
        webhook_id=webhook_id,
        routing_strategy=routing_strategy,
        routing_reason=routing_reason,
        total_accounts=len(accounts),
        successful_accounts=successful_count,
        failed_accounts=failed_count,
        account_results=account_results,
        # Legacy single-account fields (first account)
        account_id=first_account.id,
        broker=first_account.broker.value if hasattr(first_account.broker, 'value') else str(first_account.broker),
        errors=all_errors,
        guard_decision="execute",
        processing_time_ms=processing_time_ms
    )
