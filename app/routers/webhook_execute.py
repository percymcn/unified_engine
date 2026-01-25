"""
Webhook Execute Endpoint - TradingView Alert Execution

Standardized endpoint for immediate trade execution from TradingView alerts.
Single JSON payload with webhook_key for account identification.

Payload format:
{
    "webhook_key": "unique-per-account-key",  // REQUIRED
    "action": "buy" | "sell" | "close",       // REQUIRED
    "symbol": "EURUSD",                       // REQUIRED
    "quantity": 0.1,                          // Optional, default 0.01
    "sl": 1.0800,                             // Optional stop loss
    "tp": 1.0900,                             // Optional take profit
    "timestamp": "2026-01-25T10:00:00Z",      // Optional for staleness check
    "strategy_id": "my_strategy",             // Optional
    "comment": "TV alert"                     // Optional
}
"""
import logging
import uuid
import json
import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.models.models import WebhookLog, ExecutionLog, BrokerType as ModelsBrokerType
from app.models.database_models import TradingAccount, DiscardBin, WebhookConfig
from app.models.schemas import WebhookLogCreate
from app.dependencies import get_container
from app.application.dto.signal_dto import ProcessSignalRequest
from app.domain.enums import SignalSource, SignalAction
from app.services.signal_intelligence_guard import SignalIntelligenceGuard, GuardDecision
from app.domain.entities.signal import Signal
from app.domain.value_objects import SignalId, Symbol, Volume, Price, StopLoss, TakeProfit, AccountId

logger = logging.getLogger(__name__)

router = APIRouter()


class TradingViewPayload(BaseModel):
    """Standardized TradingView webhook payload"""
    webhook_key: str = Field(..., description="Unique webhook key for account identification")
    action: str = Field(..., description="Trade action: buy, sell, or close")
    symbol: str = Field(..., description="Trading symbol")
    quantity: Optional[float] = Field(0.01, description="Trade quantity/lots")
    sl: Optional[float] = Field(None, description="Stop loss price")
    tp: Optional[float] = Field(None, description="Take profit price")
    timestamp: Optional[str] = Field(None, description="Signal timestamp for staleness check")
    strategy_id: Optional[str] = Field(None, description="Strategy identifier")
    comment: Optional[str] = Field(None, description="Trade comment")


class ExecuteResponse(BaseModel):
    """Standard execution response"""
    success: bool
    signal_id: str
    status: str  # executed, rejected, paused, failed
    webhook_id: str
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

    symbol = raw_payload.get("symbol")
    if not symbol:
        log_event("webhook_rejected_missing_symbol", webhook_id=webhook_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Missing required field: symbol"
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

    # Lookup account by webhook_key (account-level keys)
    account = db.query(TradingAccount).filter(
        TradingAccount.webhook_key == webhook_key
    ).first()

    # Fall back to primary webhook config keys (user-level keys)
    if not account:
        webhook_config = db.query(WebhookConfig).filter(
            WebhookConfig.webhook_key == webhook_key,
            WebhookConfig.is_active == True
        ).first()
        logger.info(
            "Webhook execute fallback: webhook_config_found=%s webhook_key_prefix=%s",
            bool(webhook_config),
            webhook_key[:12] + "..." if len(webhook_key) > 12 else webhook_key
        )

        if webhook_config:
            candidate_account_id = webhook_config.default_account_id
            if not candidate_account_id and webhook_config.specific_account_ids:
                candidate_account_id = webhook_config.specific_account_ids[0]

            if candidate_account_id:
                account = db.query(TradingAccount).filter(
                    TradingAccount.id == candidate_account_id,
                    TradingAccount.user_id == webhook_config.user_id
                ).first()
            else:
                account = db.query(TradingAccount).filter(
                    TradingAccount.user_id == webhook_config.user_id
                ).order_by(TradingAccount.updated_at.desc()).first()

            logger.info(
                "Webhook execute resolved account: account_id=%s user_id=%s",
                account.id if account else None,
                webhook_config.user_id
            )

    if not account:
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
        try:
            webhook_log.processed = False
            webhook_log.response_status = 403
            webhook_log.response_body = json.dumps({"error": "Invalid webhook_key"})
            db.commit()
        except:
            pass

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook_key. Signal not executed."
        )

    # Account found - log context
    log_event(
        "webhook_account_resolved",
        webhook_id=webhook_id,
        account_id=account.id,
        user_id=account.user_id,
        broker=account.broker.value if hasattr(account.broker, 'value') else str(account.broker)
    )

    # Map action
    action_map = {
        "buy": SignalAction.BUY,
        "sell": SignalAction.SELL,
        "close": SignalAction.CLOSE,
    }
    action = action_map[action_str]

    # Build signal entity for guard evaluation
    quantity = float(raw_payload.get("quantity", 0.01) or 0.01)
    sl_price = raw_payload.get("sl")
    tp_price = raw_payload.get("tp")

    signal_entity = Signal(
        id=SignalId(str(uuid.uuid4())),
        source=SignalSource.TRADINGVIEW,
        symbol=Symbol(symbol),
        action=action,
        volume=Volume(Decimal(str(quantity))),
        price=None,  # Market order
        stop_loss=StopLoss(Price(Decimal(str(sl_price)))) if sl_price else None,
        take_profit=TakeProfit(Price(Decimal(str(tp_price)))) if tp_price else None,
        target_accounts=[AccountId(str(account.id))],
        comment=raw_payload.get("comment"),
        strategy_id=raw_payload.get("strategy_id"),
        strategy_name=None,
        raw_payload=raw_payload,
    )

    # === SIGNAL INTELLIGENCE GUARD ===
    guard = SignalIntelligenceGuard(db)

    # Get open positions summary for exposure check
    open_positions_summary = {}
    try:
        from app.models.models import Position
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
        open_positions_summary[account.id] = {"total_margin": account.margin or 0.0, "positions_count": 0}

    # Evaluate guard
    guard_result = await guard.evaluate(
        signal=signal_entity,
        user_id=account.user_id,
        account_ids=[account.id],
        open_positions_summary=open_positions_summary
    )

    # Log guard decision
    log_event(
        "guard_decision",
        webhook_id=webhook_id,
        signal_id=signal_entity.id.value,
        account_id=account.id,
        decision=guard_result.decision.value,
        annotations=guard_result.annotations
    )

    # Handle guard decisions
    processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    if guard_result.decision == GuardDecision.SKIP:
        # Signal discarded (stale, etc.)
        try:
            webhook_log.processed = False
            webhook_log.response_status = 200
            webhook_log.processing_time_ms = processing_time_ms
            db.commit()
        except:
            pass

        return ExecuteResponse(
            success=False,
            signal_id=signal_entity.id.value,
            status="rejected",
            webhook_id=webhook_id,
            account_id=account.id,
            broker=account.broker.value if hasattr(account.broker, 'value') else str(account.broker),
            guard_decision="skip",
            guard_reason=guard_result.annotations.get("discard_reason", "guard_rejected"),
            processing_time_ms=processing_time_ms
        )

    if guard_result.decision == GuardDecision.WARN_MODAL_REQUIRED:
        # Needs user confirmation
        try:
            webhook_log.processed = False
            webhook_log.response_status = 202
            webhook_log.response_body = json.dumps({"status": "awaiting_confirmation"})
            webhook_log.processing_time_ms = processing_time_ms
            db.commit()
        except:
            pass

        return ExecuteResponse(
            success=False,
            signal_id=signal_entity.id.value,
            status="awaiting_confirmation",
            webhook_id=webhook_id,
            account_id=account.id,
            broker=account.broker.value if hasattr(account.broker, 'value') else str(account.broker),
            guard_decision="warn",
            guard_reason=guard_result.annotations.get("history_tag", "momentum_warning"),
            modal_data=guard_result.modal_data,
            processing_time_ms=processing_time_ms
        )

    if guard_result.decision == GuardDecision.PAUSE_NEW_ENTRIES:
        # Paused - don't execute new entries
        if action != SignalAction.CLOSE:
            try:
                webhook_log.processed = False
                webhook_log.response_status = 200
                webhook_log.processing_time_ms = processing_time_ms
                db.commit()
            except:
                pass

            return ExecuteResponse(
                success=False,
                signal_id=signal_entity.id.value,
                status="paused",
                webhook_id=webhook_id,
                account_id=account.id,
                broker=account.broker.value if hasattr(account.broker, 'value') else str(account.broker),
                guard_decision="pause",
                guard_reason=guard_result.annotations.get("history_tag", "paused_new_entries"),
                modal_data=guard_result.modal_data,
                processing_time_ms=processing_time_ms
            )

    # === EXECUTE ===
    # Guard passed - execute the signal
    try:
        # Build command for use case - pass same UUID as signal_entity for FK consistency
        command = ProcessSignalRequest(
            source=SignalSource.TRADINGVIEW,
            symbol=symbol,
            action=action,
            volume=Decimal(str(quantity)),
            price=None,
            stop_loss=Decimal(str(sl_price)) if sl_price else None,
            take_profit=Decimal(str(tp_price)) if tp_price else None,
            target_account_ids=[str(account.id)],
            comment=raw_payload.get("comment"),
            strategy_id=raw_payload.get("strategy_id"),
            strategy_name=None,
            raw_payload=raw_payload,
            signal_id=signal_entity.id.value,  # Use same UUID for FK consistency
        )

        # Execute via container's use case
        container = get_container(request)
        use_case = container.process_signal_use_case()
        use_case_result = await use_case.execute(command)

        execution_success = use_case_result.status.value not in ["failed", "rejected"]

        # Log execution result
        log_event(
            "execution_result",
            webhook_id=webhook_id,
            signal_id=use_case_result.signal_id,
            account_id=account.id,
            success=execution_success,
            status=use_case_result.status.value,
            executions=use_case_result.executions,
            errors=use_case_result.errors
        )

        # Persist execution log
        try:
            # Convert broker to the models.BrokerType enum (for ExecutionLog)
            broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker).lower()
            models_broker = ModelsBrokerType(broker_str)

            exec_log = ExecutionLog(
                signal_id=signal_entity.id.value,  # Use original UUID for FK to signals.signal_id
                account_id=account.id,
                broker=models_broker,
                action=action_str.upper(),
                symbol=symbol,
                volume=quantity,
                price=None,
                status="success" if execution_success else "failed",
                broker_response={"executions": use_case_result.executions} if execution_success else None,
                error_message="; ".join(use_case_result.errors) if use_case_result.errors else None,
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
            db.add(exec_log)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to persist execution log: {e}")
            db.rollback()

        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Update webhook log
        try:
            webhook_log.processed = execution_success
            webhook_log.response_status = 200
            webhook_log.processing_time_ms = processing_time_ms
            db.commit()
        except:
            pass

        return ExecuteResponse(
            success=execution_success,
            signal_id=use_case_result.signal_id or signal_entity.id.value,
            status="executed" if execution_success else "failed",
            webhook_id=webhook_id,
            account_id=account.id,
            broker=account.broker.value if hasattr(account.broker, 'value') else str(account.broker),
            errors=use_case_result.errors,
            guard_decision="execute",
            processing_time_ms=processing_time_ms
        )

    except Exception as e:
        logger.exception(f"Execution error: {e}")

        log_event(
            "execution_failed",
            webhook_id=webhook_id,
            signal_id=signal_entity.id.value,
            account_id=account.id,
            error=str(e)
        )

        # Persist failed execution log
        try:
            db.rollback()  # Clear any pending transaction
            broker_str = account.broker.value if hasattr(account.broker, 'value') else str(account.broker).lower()
            models_broker = ModelsBrokerType(broker_str)

            exec_log = ExecutionLog(
                signal_id=signal_entity.id.value,
                account_id=account.id,
                broker=models_broker,
                action=action_str.upper(),
                symbol=symbol,
                volume=quantity,
                status="failed",
                error_message=str(e),
                execution_time_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
            db.add(exec_log)
            db.commit()
        except Exception as log_err:
            logger.error(f"Failed to persist error log: {log_err}")
            db.rollback()

        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return ExecuteResponse(
            success=False,
            signal_id=signal_entity.id.value,
            status="failed",
            webhook_id=webhook_id,
            account_id=account.id,
            broker=account.broker.value if hasattr(account.broker, 'value') else str(account.broker),
            errors=[str(e)],
            processing_time_ms=processing_time_ms
        )
