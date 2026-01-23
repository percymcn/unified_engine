from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
import uuid
import json
import logging

from app.db.database import get_db
from app.models.models import WebhookLog, User, Position
from app.models.database_models import WebhookConfig, TradingAccount, RejectedSignal, RejectedSignalReason
from app.models.schemas import WebhookLog as WebhookLogSchema, WebhookLogCreate
from app.routers.auth import get_current_user
from app.dependencies import get_container
from app.application.dto.signal_dto import ProcessSignalRequest
from app.domain.enums import SignalSource, SignalAction
from app.domain.services.routing_service import (
    RoutingEngine,
    RoutingConfig,
    RoutingStrategy,
    build_signal_data,
)
from app.domain.services import (
    RiskEnforcementService,
    AccountRiskSettings,
    DailyCounterService,
)
from app.infrastructure.repositories import get_daily_counter_repository
from app.infrastructure.adapters.position_counter_adapter import PositionCounterAdapter

logger = logging.getLogger(__name__)

router = APIRouter()


# Helper function for guard layer evaluation (shared across all webhook endpoints)
async def evaluate_guard_layer(
    db: Session,
    command: ProcessSignalRequest,
    source: SignalSource,
    action: SignalAction,
    user_id: Optional[int] = None,
    account_ids: Optional[List[int]] = None,
    accounts_by_id: Optional[Dict[int, Any]] = None,
    start_time: Optional[datetime] = None,
    webhook_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Evaluate signal through guard layer.
    
    Returns:
        Dict with guard decision response if signal should be blocked/paused/warned
        None if signal should proceed (guard passed or failed open)
    """
    try:
        from app.services.signal_intelligence_guard import SignalIntelligenceGuard, GuardDecision
        from app.domain.entities.signal import Signal
        from app.domain.value_objects import SignalId, Symbol, Volume, Price, StopLoss, TakeProfit, AccountId

        # If user_id unknown, fail open (don't block) but still allow staleness logging
        if user_id is None:
            # Try to infer from command if possible, otherwise skip guard (fail open)
            logger.debug("Guard layer: user_id unknown, skipping guard evaluation (fail open)")
            return None

        # Convert command to domain entity for guard evaluation
        signal_entity = Signal(
            id=SignalId(str(uuid.uuid4())),
            source=source,
            symbol=Symbol(command.symbol),
            action=action,
            volume=Volume(command.volume) if command.volume else None,
            price=Price(command.price) if command.price else None,
            stop_loss=StopLoss(Price(command.stop_loss)) if command.stop_loss else None,
            take_profit=TakeProfit(Price(command.take_profit)) if command.take_profit else None,
            target_accounts=[AccountId(aid) for aid in (account_ids or [])],
            comment=command.comment,
            strategy_id=command.strategy_id,
            strategy_name=command.strategy_name,
            raw_payload=command.raw_payload,
        )

        # Get open positions summary for exposure check
        open_positions_summary = {}
        if account_ids and accounts_by_id:
            for account_id in account_ids:
                account = accounts_by_id.get(account_id)
                if account:
                    # Try to get actual positions if available
                    from app.models.models import Position
                    positions = db.query(Position).filter(
                        Position.account_id == account_id,
                        Position.status == "open"
                    ).all()
                    total_margin = sum(p.margin or 0.0 for p in positions) if positions else (account.margin or 0.0)
                    open_positions_summary[account_id] = {
                        "total_margin": total_margin,
                        "positions_count": len(positions) if positions else 0
                    }
        elif account_ids:
            # Fallback: use account margin if positions not available
            for account_id in account_ids:
                account = db.query(TradingAccount).filter(TradingAccount.id == account_id).first()
                if account:
                    open_positions_summary[account_id] = {
                        "total_margin": account.margin or 0.0,
                        "positions_count": 0
                    }

        # Evaluate guard layer
        guard = SignalIntelligenceGuard(db)
        guard_result = await guard.evaluate(
            signal=signal_entity,
            user_id=user_id,
            account_ids=account_ids or [],
            open_positions_summary=open_positions_summary
        )

        # Handle guard decisions
        processing_time_ms = int((datetime.utcnow() - (start_time or datetime.utcnow())).total_seconds() * 1000) if start_time else 0

        if guard_result.decision == GuardDecision.SKIP:
            return {
                "success": False,
                "webhook_id": webhook_id,
                "status": "skipped",
                "reason": guard_result.annotations.get("discard_reason", "unknown"),
                "message": guard_result.annotations.get("history_tag", "Signal skipped by guard layer"),
                "processing_time_ms": processing_time_ms,
            }

        elif guard_result.decision == GuardDecision.PAUSE_NEW_ENTRIES:
            return {
                "success": False,
                "webhook_id": webhook_id,
                "status": "paused",
                "reason": guard_result.annotations.get("history_tag", "New entries paused"),
                "modal_data": guard_result.modal_data,
                "processing_time_ms": processing_time_ms,
            }

        elif guard_result.decision == GuardDecision.WARN_MODAL_REQUIRED:
            return {
                "success": False,
                "webhook_id": webhook_id,
                "status": "warning_required",
                "modal_required": True,
                "modal_data": guard_result.modal_data,
                "annotations": guard_result.annotations,
                "processing_time_ms": processing_time_ms,
            }

        # Guard passed - return None to continue execution
        logger.debug(f"Signal passed guard layer checks: {guard_result.annotations}")
        return None

    except Exception as guard_error:
        # Fail open - log but don't block execution
        logger.warning(f"Guard layer evaluation failed, continuing execution (fail open): {guard_error}")
        return None

@router.post("/tradingview")
async def tradingview_webhook(request: Request, db: Session = Depends(get_db)):
    """TradingView webhook endpoint"""
    start_time = datetime.utcnow()

    try:
        # Get request data
        if request.headers.get("content-type", "").startswith("application/json"):
            payload = await request.json()
        else:
            form_data = await request.form()
            payload = dict(form_data)

        # Create webhook log
        webhook_id = str(uuid.uuid4())
        webhook_log = WebhookLogCreate(
            webhook_id=webhook_id,
            source="tradingview",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(payload)
        )

        db_webhook = WebhookLog(**webhook_log.dict())
        db.add(db_webhook)
        db.commit()

        # Extract strategy information from payload
        strategy_info = {}
        if "strategy" in payload:
            strategy_obj = payload["strategy"]
            strategy_info = {
                "strategy_id": strategy_obj.get("id", payload.get("strategy_id", "unknown")),
                "strategy_version": strategy_obj.get("version", payload.get("strategy_version", "1.0.0")),
                "strategy_name": strategy_obj.get("name", payload.get("strategy_name", "Unknown Strategy"))
            }
        elif "strategy_id" in payload:
            strategy_info = {
                "strategy_id": payload.get("strategy_id", "unknown"),
                "strategy_version": payload.get("strategy_version", "1.0.0"),
                "strategy_name": payload.get("strategy_name", "Unknown Strategy")
            }

        # Get container and use case from hexagonal architecture
        container = get_container(request)
        use_case = container.process_signal_use_case()

        # Build ProcessSignalRequest from webhook payload
        # Map TradingView payload fields to domain command
        symbol = payload.get("ticker") or payload.get("symbol", "UNKNOWN")
        action_str = payload.get("action", "buy").lower()

        # Map action string to enum
        action_map = {
            "buy": SignalAction.BUY,
            "sell": SignalAction.SELL,
            "close": SignalAction.CLOSE,
        }
        action = action_map.get(action_str, SignalAction.BUY)

        # Build command
        command = ProcessSignalRequest(
            source=SignalSource.TRADINGVIEW,
            symbol=symbol,
            action=action,
            volume=Decimal(str(payload.get("quantity", payload.get("volume", 1)))),
            price=Decimal(str(payload["price"])) if payload.get("price") else None,
            stop_loss=Decimal(str(payload["stop_loss"])) if payload.get("stop_loss") else None,
            take_profit=Decimal(str(payload["take_profit"])) if payload.get("take_profit") else None,
            target_account_ids=[],  # Routing will be handled by domain service
            comment=payload.get("comment"),
            strategy_id=strategy_info.get("strategy_id"),
            strategy_name=strategy_info.get("strategy_name"),
            raw_payload=payload,
        )

        # SIGNAL INTELLIGENCE GUARD LAYER - Evaluate signal before execution
        # Try to get user_id from payload or webhook config if available
        user_id = None
        account_ids = []
        accounts_by_id = {}
        
        # Try to infer user_id from payload or API key if available
        if "user_id" in payload:
            try:
                user_id = int(payload["user_id"])
            except:
                pass
        
        # If user_id available, get accounts for exposure check
        if user_id:
            accounts = db.query(TradingAccount).filter(
                TradingAccount.user_id == user_id,
                TradingAccount.is_active == True,
                TradingAccount.is_signal_enabled == True
            ).all()
            account_ids = [a.id for a in accounts]
            accounts_by_id = {a.id: a for a in accounts}

        guard_response = await evaluate_guard_layer(
            db=db,
            command=command,
            source=SignalSource.TRADINGVIEW,
            action=action,
            user_id=user_id,
            account_ids=account_ids if account_ids else None,
            accounts_by_id=accounts_by_id if accounts_by_id else None,
            start_time=start_time,
            webhook_id=webhook_id
        )
        
        if guard_response:
            # Guard blocked/paused/warned - return early
            db_webhook.processed = False
            db_webhook.response_status = 200
            db_webhook.response_body = json.dumps(guard_response)
            db_webhook.processing_time_ms = guard_response.get("processing_time_ms", 0)
            db.commit()
            return guard_response

        # Execute use case
        use_case_result = await use_case.execute(command)

        # Map domain result to API response
        result = {
            "success": use_case_result.status.value not in ["failed", "rejected"],
            "signal_id": use_case_result.signal_id,
            "status": use_case_result.status.value,
            "executions": use_case_result.executions,
            "errors": use_case_result.errors,
            "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
        }

        # Update webhook log
        db_webhook.processed = result["success"]
        db_webhook.response_status = 200
        db_webhook.response_body = json.dumps(result)
        db_webhook.processing_time_ms = result["processing_time_ms"]
        db.commit()

        return result

    except Exception as e:
        # Log error
        db_webhook = WebhookLog(
            webhook_id=webhook_id,
            source="tradingview",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(payload) if 'payload' in locals() else "{}",
            processed=False,
            error_message=str(e)
        )
        db.add(db_webhook)
        db.commit()

        return {"success": False, "error": str(e)}

@router.post("/trailhacker")
async def trailhacker_webhook(request: Request, db: Session = Depends(get_db)):
    """TrailHacker webhook endpoint"""
    start_time = datetime.utcnow()

    try:
        # Get request data
        if request.headers.get("content-type", "").startswith("application/json"):
            payload = await request.json()
        else:
            form_data = await request.form()
            payload = dict(form_data)

        # Create webhook log
        webhook_id = str(uuid.uuid4())
        webhook_log = WebhookLogCreate(
            webhook_id=webhook_id,
            source="trailhacker",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(payload)
        )

        db_webhook = WebhookLog(**webhook_log.dict())
        db.add(db_webhook)
        db.commit()

        # Get container and use case from hexagonal architecture
        container = get_container(request)
        use_case = container.process_signal_use_case()

        # Build ProcessSignalRequest from webhook payload
        # Map TrailHacker payload fields to domain command
        symbol = payload.get("symbol", "UNKNOWN")
        action_str = payload.get("signal", payload.get("action", "buy")).lower()

        # Map action string to enum
        action_map = {
            "buy": SignalAction.BUY,
            "sell": SignalAction.SELL,
            "close": SignalAction.CLOSE,
        }
        action = action_map.get(action_str, SignalAction.BUY)

        # Build command (TrailHacker uses "size", "entry", "stop", "target")
        command = ProcessSignalRequest(
            source=SignalSource.TRAILHACKER,
            symbol=symbol,
            action=action,
            volume=Decimal(str(payload.get("size", payload.get("volume", 1)))),
            price=Decimal(str(payload["entry"])) if payload.get("entry") else None,
            stop_loss=Decimal(str(payload["stop"])) if payload.get("stop") else None,
            take_profit=Decimal(str(payload["target"])) if payload.get("target") else None,
            target_account_ids=[],  # Routing will be handled by domain service
            comment=payload.get("comment"),
            strategy_id=payload.get("strategy_id"),
            strategy_name=payload.get("strategy_name"),
            raw_payload=payload,
        )

        # SIGNAL INTELLIGENCE GUARD LAYER - Evaluate signal before execution
        # Try to get user_id from payload if available
        user_id = None
        account_ids = []
        accounts_by_id = {}
        
        if "user_id" in payload:
            try:
                user_id = int(payload["user_id"])
            except:
                pass
        
        # If user_id available, get accounts for exposure check
        if user_id:
            accounts = db.query(TradingAccount).filter(
                TradingAccount.user_id == user_id,
                TradingAccount.is_active == True,
                TradingAccount.is_signal_enabled == True
            ).all()
            account_ids = [a.id for a in accounts]
            accounts_by_id = {a.id: a for a in accounts}

        guard_response = await evaluate_guard_layer(
            db=db,
            command=command,
            source=SignalSource.TRAILHACKER,
            action=action,
            user_id=user_id,
            account_ids=account_ids if account_ids else None,
            accounts_by_id=accounts_by_id if accounts_by_id else None,
            start_time=start_time,
            webhook_id=webhook_id
        )
        
        if guard_response:
            # Guard blocked/paused/warned - return early
            db_webhook.processed = False
            db_webhook.response_status = 200
            db_webhook.response_body = json.dumps(guard_response)
            db_webhook.processing_time_ms = guard_response.get("processing_time_ms", 0)
            db.commit()
            return guard_response

        # Execute use case
        use_case_result = await use_case.execute(command)

        # Map domain result to API response
        result = {
            "success": use_case_result.status.value not in ["failed", "rejected"],
            "signal_id": use_case_result.signal_id,
            "status": use_case_result.status.value,
            "executions": use_case_result.executions,
            "errors": use_case_result.errors,
            "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
        }

        # Update webhook log
        db_webhook.processed = result["success"]
        db_webhook.response_status = 200
        db_webhook.response_body = json.dumps(result)
        db_webhook.processing_time_ms = result["processing_time_ms"]
        db.commit()

        return result

    except Exception as e:
        # Log error
        db_webhook = WebhookLog(
            webhook_id=webhook_id,
            source="trailhacker",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(payload) if 'payload' in locals() else "{}",
            processed=False,
            error_message=str(e)
        )
        db.add(db_webhook)
        db.commit()

        return {"success": False, "error": str(e)}

@router.get("/logs")
async def get_webhook_logs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get webhook logs"""
    logs = db.query(WebhookLog).offset(skip).limit(limit).all()
    return logs

@router.get("/logs/{webhook_id}")
async def get_webhook_log(
    webhook_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific webhook log"""
    log = db.query(WebhookLog).filter(
        WebhookLog.webhook_id == webhook_id
    ).first()
    
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook log not found"
        )
    
    return log

@router.post("/test")
async def test_webhook(request: Request, db: Session = Depends(get_db)):
    """Test webhook endpoint"""
    try:
        payload = await request.json()

        # Create test webhook log
        webhook_id = str(uuid.uuid4())
        webhook_log = WebhookLogCreate(
            webhook_id=webhook_id,
            source="test",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(payload)
        )

        db_webhook = WebhookLog(**webhook_log.dict())
        db.add(db_webhook)
        db.commit()

        return {
            "success": True,
            "message": "Test webhook received",
            "webhook_id": webhook_id,
            "payload": payload
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/signal/{webhook_key}")
async def process_routed_signal(
    webhook_key: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Process a signal using webhook configuration for routing.

    This endpoint uses the webhook_key to identify the webhook configuration,
    then applies the configured routing rules to determine which accounts
    should receive the signal.

    The webhook_key is the unique identifier generated when creating a webhook config.
    Include it in your TradingView webhook URL:
    https://your-domain.com/api/webhooks/signal/{webhook_key}
    """
    start_time = datetime.utcnow()
    webhook_id = str(uuid.uuid4())

    try:
        # Get request data
        if request.headers.get("content-type", "").startswith("application/json"):
            payload = await request.json()
        else:
            form_data = await request.form()
            payload = dict(form_data)

        # Look up webhook configuration by key
        webhook_config = db.query(WebhookConfig).filter(
            WebhookConfig.webhook_key == webhook_key,
            WebhookConfig.is_active == True
        ).first()

        if not webhook_config:
            logger.warning(f"Invalid or inactive webhook key: {webhook_key}")
            return {
                "success": False,
                "error": "Invalid or inactive webhook configuration"
            }

        # Create webhook log
        webhook_log = WebhookLogCreate(
            webhook_id=webhook_id,
            source=webhook_config.source,
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(payload)
        )
        db_webhook = WebhookLog(**webhook_log.dict())
        db.add(db_webhook)
        db.commit()

        # Update webhook config stats
        webhook_config.total_signals = (webhook_config.total_signals or 0) + 1
        webhook_config.last_signal_at = datetime.utcnow()

        # Get user's active, signal-enabled accounts
        accounts = db.query(TradingAccount).filter(
            TradingAccount.user_id == webhook_config.user_id,
            TradingAccount.is_active == True,
            TradingAccount.is_signal_enabled == True
        ).all()

        available_account_ids = [a.id for a in accounts]

        if not available_account_ids:
            logger.warning(f"No signal-enabled accounts for user {webhook_config.user_id}")
            webhook_config.failed_signals = (webhook_config.failed_signals or 0) + 1
            db.commit()
            return {
                "success": False,
                "error": "No active signal-enabled accounts available"
            }

        # Build routing configuration from webhook config
        routing_config = RoutingConfig.from_webhook_config(webhook_config)

        # Create routing engine
        engine = RoutingEngine(routing_config, available_account_ids)

        # Build signal data for rule evaluation
        signal_data = build_signal_data(payload, webhook_config.source)

        # Resolve target accounts
        target_account_ids = engine.resolve_target_accounts(signal_data)

        if not target_account_ids:
            logger.warning(f"No accounts matched routing rules for signal: {signal_data}")
            webhook_config.failed_signals = (webhook_config.failed_signals or 0) + 1
            db.commit()
            return {
                "success": False,
                "error": "No accounts matched routing rules",
                "webhook_id": webhook_id,
                "signal_data": signal_data
            }

        logger.info(f"Routing signal to {len(target_account_ids)} accounts: {target_account_ids}")

        # RISK ENFORCEMENT: Check risk limits for each target account
        # Build account lookup for risk settings
        accounts_by_id = {a.id: a for a in accounts}
        symbol = signal_data.get("symbol", "UNKNOWN")
        action_str = signal_data.get("action", "buy").lower()

        # Initialize risk enforcement service
        counter_repo = get_daily_counter_repository()
        counter_service = DailyCounterService(counter_repo)
        position_counter = PositionCounterAdapter(session=db)
        risk_service = RiskEnforcementService(
            counter_service=counter_service,
            position_counter=position_counter,
        )

        # Track which accounts pass risk checks
        approved_account_ids = []
        blocked_accounts = []

        for account_id in target_account_ids:
            account = accounts_by_id.get(account_id)
            if not account:
                continue

            # Build risk settings from account
            risk_settings = AccountRiskSettings.from_account(account)

            # Evaluate risk limits
            evaluation = await risk_service.evaluate(
                account_id=account_id,
                symbol=symbol,
                action=action_str,
                settings=risk_settings,
            )

            if evaluation.passed:
                approved_account_ids.append(account_id)
            else:
                # Log rejection
                violation = evaluation.first_violation
                if violation:
                    try:
                        # Map reason string to enum
                        reason_map = {
                            "daily_limit": RejectedSignalReason.DAILY_LIMIT,
                            "concurrent_limit": RejectedSignalReason.CONCURRENT_LIMIT,
                            "symbol_limit": RejectedSignalReason.SYMBOL_LIMIT,
                            "cooldown": RejectedSignalReason.COOLDOWN,
                            "daily_loss": RejectedSignalReason.DAILY_LOSS,
                            "drawdown": RejectedSignalReason.DRAWDOWN,
                            "risk_reward": RejectedSignalReason.RISK_REWARD,
                            "disabled": RejectedSignalReason.DISABLED,
                        }
                        reason_enum = reason_map.get(violation.reason, RejectedSignalReason.DISABLED)

                        rejected = RejectedSignal(
                            user_id=webhook_config.user_id,
                            account_id=account_id,
                            symbol=symbol,
                            action=action_str,
                            quantity=float(signal_data.get("quantity", 1) or 1),
                            source=webhook_config.source,
                            reason=reason_enum,
                            reason_detail=violation.detail,
                            limit_value=violation.limit_value,
                            current_value=violation.current_value,
                            webhook_config_id=webhook_config.id,
                            original_payload=payload,
                        )
                        db.add(rejected)
                        logger.info(
                            f"Risk blocked account {account_id} for signal {symbol} {action_str}: "
                            f"{violation.detail}"
                        )
                    except Exception as e:
                        logger.error(f"Failed to log rejected signal: {e}")

                blocked_accounts.append({
                    "account_id": account_id,
                    "reason": violation.reason if violation else "unknown",
                    "detail": violation.detail if violation else "Risk check failed",
                })

        # Commit rejected signals
        if blocked_accounts:
            try:
                db.commit()
            except Exception as e:
                logger.error(f"Failed to commit rejected signals: {e}")
                db.rollback()

        # If all accounts blocked, return early with blocked info
        if not approved_account_ids:
            logger.warning(f"All accounts blocked by risk limits for signal: {signal_data}")
            webhook_config.failed_signals = (webhook_config.failed_signals or 0) + 1
            db.commit()
            return {
                "success": False,
                "blocked": True,
                "error": "All target accounts blocked by risk limits",
                "webhook_id": webhook_id,
                "blocked_accounts": blocked_accounts,
                "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
            }

        # Use approved accounts for signal execution
        target_account_ids = approved_account_ids
        logger.info(
            f"Risk check passed: {len(approved_account_ids)} accounts approved, "
            f"{len(blocked_accounts)} blocked"
        )

        # Apply symbol/action filters if configured
        if webhook_config.symbol_filter:
            symbol = signal_data.get("symbol", "").upper()
            if symbol not in [s.upper() for s in webhook_config.symbol_filter]:
                logger.info(f"Signal symbol {symbol} filtered out")
                return {
                    "success": True,
                    "filtered": True,
                    "reason": f"Symbol {symbol} not in filter list"
                }

        if webhook_config.action_filter:
            action = signal_data.get("action", "").lower()
            if action not in [a.lower() for a in webhook_config.action_filter]:
                logger.info(f"Signal action {action} filtered out")
                return {
                    "success": True,
                    "filtered": True,
                    "reason": f"Action {action} not in filter list"
                }

        # Get container and use case
        container = get_container(request)
        use_case = container.process_signal_use_case()

        # Determine source
        source_map = {
            "tradingview": SignalSource.TRADINGVIEW,
            "trailhacker": SignalSource.TRAILHACKER,
        }
        source = source_map.get(webhook_config.source.lower(), SignalSource.TRADINGVIEW)

        # Map action string to enum
        action_str = signal_data.get("action", "buy").lower()
        action_map = {
            "buy": SignalAction.BUY,
            "sell": SignalAction.SELL,
            "close": SignalAction.CLOSE,
        }
        action = action_map.get(action_str, SignalAction.BUY)

        # Build command with routed account IDs
        command = ProcessSignalRequest(
            source=source,
            symbol=signal_data.get("symbol", "UNKNOWN"),
            action=action,
            volume=Decimal(str(signal_data.get("quantity", 1) or 1)),
            price=Decimal(str(payload["price"])) if payload.get("price") else None,
            stop_loss=Decimal(str(payload.get("stop_loss") or payload.get("stop", 0))) if payload.get("stop_loss") or payload.get("stop") else None,
            take_profit=Decimal(str(payload.get("take_profit") or payload.get("target", 0))) if payload.get("take_profit") or payload.get("target") else None,
            target_account_ids=[str(aid) for aid in target_account_ids],
            comment=payload.get("comment"),
            strategy_id=payload.get("strategy_id"),
            strategy_name=payload.get("strategy_name"),
            raw_payload=payload,
        )

        # SIGNAL INTELLIGENCE GUARD LAYER - Evaluate signal before execution
        guard_response = await evaluate_guard_layer(
            db=db,
            command=command,
            source=source,
            action=action,
            user_id=webhook_config.user_id,
            account_ids=target_account_ids,
            accounts_by_id=accounts_by_id,
            start_time=start_time,
            webhook_id=webhook_id
        )
        
        if guard_response:
            # Guard blocked/paused/warned - return early
            webhook_config.failed_signals = (webhook_config.failed_signals or 0) + 1
            db_webhook.processed = False
            db_webhook.response_status = 200
            db_webhook.response_body = json.dumps(guard_response)
            db_webhook.processing_time_ms = guard_response.get("processing_time_ms", 0)
            db.commit()
            return guard_response

        # Execute use case
        use_case_result = await use_case.execute(command)

        # Update stats
        success = use_case_result.status.value not in ["failed", "rejected"]
        if success:
            webhook_config.successful_signals = (webhook_config.successful_signals or 0) + 1

            # INCREMENT DAILY COUNTERS for successfully executed trades
            # This is critical for daily trade limit enforcement
            signal_symbol = signal_data.get("symbol", "UNKNOWN")
            for account_id in target_account_ids:
                try:
                    await counter_service.increment_trades(account_id, signal_symbol)
                    logger.debug(f"Incremented trade counter for account {account_id}, symbol {signal_symbol}")
                except Exception as e:
                    logger.error(f"Failed to increment counter for account {account_id}: {e}")
        else:
            webhook_config.failed_signals = (webhook_config.failed_signals or 0) + 1

        # Map domain result to API response
        result = {
            "success": success,
            "webhook_id": webhook_id,
            "signal_id": use_case_result.signal_id,
            "status": use_case_result.status.value,
            "accounts_targeted": len(target_account_ids),
            "target_account_ids": target_account_ids,
            "executions": use_case_result.executions,
            "errors": use_case_result.errors,
            "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
        }

        # Include risk-blocked accounts info if any
        if blocked_accounts:
            result["risk_blocked_accounts"] = blocked_accounts
            result["risk_blocked_count"] = len(blocked_accounts)

        # Update webhook log
        db_webhook.processed = success
        db_webhook.response_status = 200
        db_webhook.response_body = json.dumps(result)
        db_webhook.processing_time_ms = result["processing_time_ms"]
        db.commit()

        return result

    except Exception as e:
        logger.error(f"Error processing routed signal: {e}")
        # Log error
        try:
            db_webhook = WebhookLog(
                webhook_id=webhook_id,
                source="routed",
                source_ip=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent"),
                payload=json.dumps(payload) if 'payload' in locals() else "{}",
                processed=False,
                error_message=str(e)
            )
            db.add(db_webhook)
            db.commit()
        except Exception:
            pass  # Best effort logging

        return {"success": False, "error": str(e), "webhook_id": webhook_id}


def get_available_accounts_for_user(db: Session, user_id: int) -> List[int]:
    """
    Get all active, signal-enabled account IDs for a user.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        List of account IDs that can receive signals
    """
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == user_id,
        TradingAccount.is_active == True,
        TradingAccount.is_signal_enabled == True
    ).all()
    return [a.id for a in accounts]