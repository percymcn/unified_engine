from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
from decimal import Decimal
import uuid
import secrets
import json
import logging

from app.db.database import get_db
from app.models.models import WebhookLog, User, Position, Signal as SignalORM, SignalSource as ModelsSignalSource
from app.models.database_models import WebhookConfig, TradingAccount, RejectedSignal, RejectedSignalReason, BrokerType as DBBrokerType
from app.models.schemas import WebhookLog as WebhookLogSchema, WebhookLogCreate
from app.routers.auth import get_current_user
from app.dependencies import get_container
from app.application.dto.signal_dto import ProcessSignalRequest
from app.domain.enums import SignalSource, SignalAction, SignalStatus, BrokerType
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


async def execute_metaapi_trade(
    metaapi_account_id: str,
    symbol: str,
    action: str,
    volume: float,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    price: Optional[float] = None,
    trailing_stop: Optional[float] = None,
    comment: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a trade via MetaAPI for MT4/MT5 accounts.

    Args:
        metaapi_account_id: The MetaAPI account ID
        symbol: Trading symbol (e.g., "EURUSD")
        action: Trade action - supports:
            - "buy" / "sell": Market orders
            - "limit_buy" / "limit_sell": Limit orders (requires price)
            - "stop_buy" / "stop_sell": Stop orders (requires price)
            - "close": Close positions by symbol
            - "close_all": Close all positions
            - "modify": Modify existing positions (SL/TP/trailing stop)
        volume: Trade volume in lots
        stop_loss: Optional stop loss price
        take_profit: Optional take profit price
        price: Entry price for limit/stop orders
        trailing_stop: Trailing stop distance in points
        comment: Optional trade comment

    Returns:
        Dict with success status, order_id, and error if any
    """
    try:
        from app.core.config import settings
        from metaapi_cloud_sdk import MetaApi
        import asyncio

        token = settings.METAAPI_TOKEN
        if not token:
            return {"success": False, "error": "METAAPI_TOKEN not configured"}

        api = MetaApi(token=token)
        account = await api.metatrader_account_api.get_account(metaapi_account_id)

        # Ensure account is deployed and connected
        if account.state != "DEPLOYED":
            logger.info(f"Deploying MetaAPI account {metaapi_account_id}...")
            await account.deploy()

        # Wait for connection
        try:
            await asyncio.wait_for(account.wait_connected(), timeout=30)
        except asyncio.TimeoutError:
            return {"success": False, "error": "Account connection timeout"}
        except Exception as e:
            return {"success": False, "error": f"Account not connected: {e}"}

        # Get RPC connection for trading
        connection = account.get_rpc_connection()
        await connection.connect()
        await asyncio.wait_for(connection.wait_synchronized(), timeout=30)

        action_lower = action.lower()

        # Market orders: buy/sell
        if action_lower in ("buy", "sell"):
            options = {}
            if stop_loss:
                options["stopLoss"] = stop_loss
            if take_profit:
                options["takeProfit"] = take_profit

            if action_lower == "buy":
                result = await connection.create_market_buy_order(
                    symbol=symbol, volume=volume, **options
                )
            else:
                result = await connection.create_market_sell_order(
                    symbol=symbol, volume=volume, **options
                )

            await connection.close()
            if result.get("stringCode") == "TRADE_RETCODE_DONE" or result.get("orderId"):
                return {
                    "success": True,
                    "order_id": result.get("orderId") or result.get("positionId"),
                    "position_id": result.get("positionId"),
                }
            return {"success": False, "error": result.get("message") or "Trade failed"}

        # Limit orders: limit_buy/limit_sell
        elif action_lower in ("limit_buy", "limit_sell"):
            if not price:
                await connection.close()
                return {"success": False, "error": "Price required for limit orders"}

            options = {}
            if stop_loss:
                options["stopLoss"] = stop_loss
            if take_profit:
                options["takeProfit"] = take_profit

            if action_lower == "limit_buy":
                result = await connection.create_limit_buy_order(
                    symbol=symbol, volume=volume, open_price=price, **options
                )
            else:
                result = await connection.create_limit_sell_order(
                    symbol=symbol, volume=volume, open_price=price, **options
                )

            await connection.close()
            if result.get("stringCode") == "TRADE_RETCODE_DONE" or result.get("orderId"):
                return {"success": True, "order_id": result.get("orderId")}
            return {"success": False, "error": result.get("message") or "Limit order failed"}

        # Stop orders: stop_buy/stop_sell
        elif action_lower in ("stop_buy", "stop_sell"):
            if not price:
                await connection.close()
                return {"success": False, "error": "Price required for stop orders"}

            options = {}
            if stop_loss:
                options["stopLoss"] = stop_loss
            if take_profit:
                options["takeProfit"] = take_profit

            if action_lower == "stop_buy":
                result = await connection.create_stop_buy_order(
                    symbol=symbol, volume=volume, open_price=price, **options
                )
            else:
                result = await connection.create_stop_sell_order(
                    symbol=symbol, volume=volume, open_price=price, **options
                )

            await connection.close()
            if result.get("stringCode") == "TRADE_RETCODE_DONE" or result.get("orderId"):
                return {"success": True, "order_id": result.get("orderId")}
            return {"success": False, "error": result.get("message") or "Stop order failed"}

        # Close positions by symbol
        elif action_lower == "close":
            positions = await connection.get_positions()
            closed = 0
            for pos in positions:
                if pos.get("symbol", "").upper() == symbol.upper():
                    await connection.close_position(pos["id"])
                    closed += 1
            await connection.close()
            return {"success": True, "closed_positions": closed}

        # Close all positions
        elif action_lower == "close_all":
            positions = await connection.get_positions()
            closed = 0
            for pos in positions:
                await connection.close_position(pos["id"])
                closed += 1
            await connection.close()
            return {"success": True, "closed_positions": closed}

        # Modify existing positions (SL/TP/trailing stop)
        elif action_lower == "modify":
            positions = await connection.get_positions()
            modified = 0
            for pos in positions:
                if pos.get("symbol", "").upper() == symbol.upper():
                    modify_kwargs = {"position_id": pos["id"]}
                    if stop_loss:
                        modify_kwargs["stop_loss"] = stop_loss
                    if take_profit:
                        modify_kwargs["take_profit"] = take_profit
                    if trailing_stop:
                        # MetaAPI trailing stop format
                        modify_kwargs["trailing_stop_loss"] = {
                            "distance": {
                                "distance": int(trailing_stop),
                                "units": "RELATIVE_POINTS"
                            }
                        }
                    await connection.modify_position(**modify_kwargs)
                    modified += 1
            await connection.close()
            return {"success": True, "modified_positions": modified}

        else:
            await connection.close()
            return {"success": False, "error": f"Unknown action: {action}"}

    except Exception as e:
        logger.error(f"MetaAPI trade execution error: {e}")
        return {"success": False, "error": str(e)}


def _persist_pending_guard_signal(
    db: Session,
    signal_id: str,
    user_id: Optional[int],
    symbol: str,
    action: str,
    volume,
    stop_loss,
    take_profit,
    payload: Dict[str, Any],
    guard_response: Dict[str, Any],
    target_accounts: Optional[List[int]],
    strategy_info: Dict[str, Any],
) -> None:
    """Persist guard warning signals for pending confirmation"""
    if not signal_id or not user_id:
        return

    guard_data = {
        "guard_decision": guard_response.get("guard_decision", "warn"),
        "guard_reason": guard_response.get("guard_reason"),
        "reason_detail": guard_response.get("reason_detail"),
        "warning_type": guard_response.get("warning_type"),
        "guard_rule": guard_response.get("guard_rule"),
        "message": guard_response.get("message"),
        "annotations": guard_response.get("annotations"),
        "modal_data": guard_response.get("modal_data"),
    }

    try:
        existing_signal = db.query(SignalORM).filter(SignalORM.signal_id == signal_id).first()
        if existing_signal:
            return

        action_value = action.upper() if isinstance(action, str) else getattr(action, "value", str(action))
        signal_record = SignalORM(
            signal_id=signal_id,
            user_id=user_id,
            source=ModelsSignalSource.TRADINGVIEW,
            symbol=symbol,
            action=action_value,
            volume=float(volume) if volume is not None else None,
            price=None,
            stop_loss=float(stop_loss) if stop_loss is not None else None,
            take_profit=float(take_profit) if take_profit is not None else None,
            comment=payload.get("comment"),
            status="pending_confirmation",
            target_accounts=target_accounts or [],
            raw_payload=payload,
            signal_data=guard_data,
            strategy_id=strategy_info.get("strategy_id"),
            strategy_version=strategy_info.get("strategy_version"),
            strategy_name=strategy_info.get("strategy_name"),
        )
        db.add(signal_record)
        db.commit()
    except Exception as exc:
        logger.warning(f"Failed to persist pending guard signal {signal_id}: {exc}")


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
            guard_reason = guard_result.annotations.get("history_tag", "momentum_warning")
            return {
                "success": False,
                "webhook_id": webhook_id,
                "status": "pending_confirmation",
                "modal_required": True,
                "modal_data": guard_result.modal_data,
                "annotations": guard_result.annotations,
                "guard_decision": "warn",
                "guard_reason": guard_reason,
                "reason_detail": guard_result.annotations.get("reason_detail"),
                "warning_type": guard_result.annotations.get("warning_type"),
                "guard_rule": guard_result.annotations.get("guard_rule"),
                "message": guard_result.annotations.get("message"),
                "processing_time_ms": processing_time_ms,
                "signal_id": signal_entity.id.value,
            }

        # Guard passed - return None to continue execution
        logger.debug(f"Signal passed guard layer checks: {guard_result.annotations}")
        return None

    except Exception as guard_error:
        # Fail open - log but don't block execution
        logger.warning(f"Guard layer evaluation failed, continuing execution (fail open): {guard_error}")
        return None


@router.post("/generate-key")
async def generate_primary_webhook_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate or regenerate the primary webhook key for the current user.

    If no active webhook config exists, create a default config and return its key.
    """
    config = db.query(WebhookConfig).filter(
        WebhookConfig.user_id == current_user.id,
        WebhookConfig.is_active == True
    ).order_by(WebhookConfig.updated_at.desc()).first()

    created = False
    if not config:
        config = WebhookConfig(
            user_id=current_user.id,
            name="Primary Webhook",
            webhook_key=secrets.token_urlsafe(32),
            source="tradingview",
            routing_strategy="default_only",
            default_account_id=None,
            specific_account_ids=[],
            routing_rules=[],
            symbol_filter=None,
            action_filter=None,
            is_active=True,
        )
        db.add(config)
        created = True
    else:
        config.webhook_key = secrets.token_urlsafe(32)

    db.commit()
    db.refresh(config)

    # Ensure primary webhook key maps to an active account for execute endpoint
    primary_account = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).order_by(TradingAccount.updated_at.desc()).first()

    if primary_account:
        if config.default_account_id is None:
            config.default_account_id = primary_account.id
        primary_account.webhook_key = config.webhook_key
        db.commit()

    return {
        "webhook_key": config.webhook_key,
        "config_id": config.id,
        "created": created,
    }


@router.get("/primary-key")
async def get_primary_webhook_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get the primary webhook key for the current user.

    Returns the most recently updated active webhook config key, or None if no config exists.
    This does NOT regenerate the key - use POST /generate-key to create/regenerate.
    """
    config = db.query(WebhookConfig).filter(
        WebhookConfig.user_id == current_user.id,
        WebhookConfig.is_active == True
    ).order_by(WebhookConfig.updated_at.desc()).first()

    if not config:
        return {"key": None, "message": "No webhook key configured. Use Settings to generate one."}

    return {
        "key": config.webhook_key,
        "config_id": config.id,
        "name": config.name,
    }


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
            # Handle both string and object formats for strategy
            if isinstance(strategy_obj, dict):
                strategy_info = {
                    "strategy_id": strategy_obj.get("id", payload.get("strategy_id", "unknown")),
                    "strategy_version": strategy_obj.get("version", payload.get("strategy_version", "1.0.0")),
                    "strategy_name": strategy_obj.get("name", payload.get("strategy_name", "Unknown Strategy"))
                }
            else:
                # strategy is a string (simple strategy name)
                strategy_info = {
                    "strategy_id": str(strategy_obj),
                    "strategy_version": payload.get("strategy_version", "1.0.0"),
                    "strategy_name": str(strategy_obj)
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
            if guard_response.get("status") == "pending_confirmation":
                signal_id = guard_response.get("signal_id") or str(uuid.uuid4())
                guard_response["signal_id"] = signal_id
                _persist_pending_guard_signal(
                    db=db,
                    signal_id=signal_id,
                    user_id=user_id,
                    symbol=symbol,
                    action=action_str,
                    volume=command.volume,
                    stop_loss=command.stop_loss,
                    take_profit=command.take_profit,
                    payload=payload,
                    guard_response=guard_response,
                    target_accounts=account_ids,
                    strategy_info=strategy_info,
                )
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
        # Log error - update existing log if it exists, otherwise try to create
        try:
            if 'db_webhook' in locals() and db_webhook is not None:
                # Update existing log
                db_webhook.processed = False
                db_webhook.error_message = str(e)
                db.commit()
            else:
                # Create new log with a fresh webhook_id to avoid duplicates
                error_webhook_id = str(uuid.uuid4())
                db_webhook = WebhookLog(
                    webhook_id=error_webhook_id,
                    source="tradingview",
                    source_ip=request.client.host if request.client else "unknown",
                    user_agent=request.headers.get("user-agent"),
                    payload=json.dumps(payload) if 'payload' in locals() else "{}",
                    processed=False,
                    error_message=str(e)
                )
                db.add(db_webhook)
                db.commit()
        except Exception:
            db.rollback()  # Best effort logging, don't fail on logging errors

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
            source=SignalSource.CUSTOM,
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
            source=SignalSource.CUSTOM,
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
        # Log error - update existing log if it exists, otherwise try to create
        try:
            if 'db_webhook' in locals() and db_webhook is not None:
                # Update existing log
                db_webhook.processed = False
                db_webhook.error_message = str(e)
                db.commit()
            else:
                # Create new log with a fresh webhook_id to avoid duplicates
                error_webhook_id = str(uuid.uuid4())
                db_webhook = WebhookLog(
                    webhook_id=error_webhook_id,
                    source="trailhacker",
                    source_ip=request.client.host if request.client else "unknown",
                    user_agent=request.headers.get("user-agent"),
                    payload=json.dumps(payload) if 'payload' in locals() else "{}",
                    processed=False,
                    error_message=str(e)
                )
                db.add(db_webhook)
                db.commit()
        except Exception:
            db.rollback()  # Best effort logging, don't fail on logging errors

        return {"success": False, "error": str(e)}

@router.get("/logs")
async def get_webhook_logs(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get webhook logs with enriched data for the current user."""
    from app.models.models import ExecutionLog

    # Get user's webhook keys to filter logs
    user_accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).all()
    user_webhook_keys = [a.webhook_key for a in user_accounts if a.webhook_key]

    # Also get profile webhook key
    user_webhook_config = db.query(WebhookConfig).filter(
        WebhookConfig.user_id == current_user.id
    ).first()
    if user_webhook_config and user_webhook_config.webhook_key:
        user_webhook_keys.append(user_webhook_config.webhook_key)

    # Query logs
    logs = db.query(WebhookLog).order_by(WebhookLog.created_at.desc()).offset(skip).limit(limit).all()

    # Enrich logs with parsed data and execution info
    enriched_logs = []
    for log in logs:
        # Parse payload to extract useful info
        try:
            payload_data = json.loads(log.payload) if log.payload else {}
        except (json.JSONDecodeError, TypeError):
            payload_data = {}

        # Check if this log belongs to user's webhook key
        log_webhook_key = payload_data.get("webhook_key", "")
        is_user_log = log_webhook_key in user_webhook_keys if user_webhook_keys else False

        # Filter to user's logs only (unless admin)
        if not is_user_log and not getattr(current_user, 'is_admin', False):
            continue

        # Get execution logs if signal_id available in response
        executions = []
        response_data = {}
        if log.response_body:
            try:
                response_data = json.loads(log.response_body)
                signal_id = response_data.get("signal_id")
                if signal_id:
                    exec_logs = db.query(ExecutionLog).filter(
                        ExecutionLog.signal_id == signal_id
                    ).all()
                    for el in exec_logs:
                        executions.append({
                            "account_id": el.account_id,
                            "broker": el.broker.value if hasattr(el.broker, 'value') else str(el.broker),
                            "status": el.status,
                            "error": el.error_message,
                        })

                # If no ExecutionLog records but errors in response, parse those
                if not executions and response_data.get("errors"):
                    for err in response_data["errors"]:
                        # Parse error strings like "Account 57: Instrument not found: XAUUSD"
                        if ": " in str(err):
                            parts = str(err).split(": ", 1)
                            account_part = parts[0]
                            error_msg = parts[1] if len(parts) > 1 else str(err)
                            account_id = account_part.replace("Account ", "") if "Account " in account_part else None
                            executions.append({
                                "account_id": account_id,
                                "broker": "unknown",
                                "status": "failed",
                                "error": error_msg,
                            })
                        else:
                            executions.append({
                                "account_id": None,
                                "broker": "unknown",
                                "status": "failed",
                                "error": str(err),
                            })
            except (json.JSONDecodeError, TypeError):
                pass

        # Extract rejection reason from response data
        rejection_reason = None
        result_status = response_data.get("status", "") if response_data else ""

        if result_status == "pending_confirmation":
            rejection_reason = "Awaiting manual confirmation (auto-confirm disabled)"
        elif result_status in ("failed", "partial", "error"):
            # Get errors from response for failed/partial results
            errors = response_data.get("errors", []) if response_data else []
            if errors:
                first_error = errors[0]
                # Clean up error message
                if ": " in str(first_error):
                    rejection_reason = str(first_error).split(": ", 1)[-1]
                else:
                    rejection_reason = str(first_error)
            elif response_data.get("error"):
                rejection_reason = str(response_data["error"])[:200]

        # Check guard decisions
        if not rejection_reason and response_data and response_data.get("guard_decision"):
            guard_decision = response_data.get("guard_decision")
            guard_reason = response_data.get("guard_reason", "")
            if guard_decision == "skip":
                rejection_reason = f"Signal Guard: {guard_reason}" if guard_reason else "Rejected by Signal Guard"
            elif guard_decision == "pause_new_entries":
                rejection_reason = "Paused: Risk limit exceeded"
            elif guard_decision == "warn_modal_required":
                rejection_reason = "Warning: Confirmation required (market flip detected)"

        # Check for specific error patterns in execution logs
        if not rejection_reason and executions:
            for exec_item in executions:
                if exec_item.get("error"):
                    error = exec_item["error"]
                    if "Invalid order size" in error:
                        rejection_reason = "Invalid order size (quantity too small for broker)"
                    elif "Not enough margin" in error:
                        rejection_reason = "Insufficient margin in broker account"
                    elif "Market is closed" in error:
                        rejection_reason = "Market closed (outside trading hours)"
                    elif "Instrument not found" in error or "symbol not found" in error.lower():
                        rejection_reason = "Symbol not found (check symbol mapping)"
                    elif "exposure_limit" in error:
                        rejection_reason = "Daily exposure limit reached"
                    elif "stale" in error.lower():
                        rejection_reason = "Signal too old (staleness guard)"
                    elif "MetaAPI connection failed" in error:
                        rejection_reason = "Broker connection failed (check credentials)"
                    elif "Could not create executor" in error:
                        rejection_reason = "Missing broker credentials"
                    elif "Max daily trades" in error:
                        rejection_reason = error[:150]
                    elif "Trade cooldown" in error:
                        rejection_reason = error[:150]
                    elif "Max open positions" in error:
                        rejection_reason = error[:150]
                    elif "Max positions for" in error:
                        rejection_reason = error[:150]
                    elif error:
                        rejection_reason = error[:200]
                    break

        # Fallback: use webhook log error_message if no reason found yet
        if not rejection_reason and log.error_message:
            rejection_reason = log.error_message[:200]

        # Last resort: if processed=False and still no reason, indicate unknown
        if not rejection_reason and not log.processed and log.response_status:
            if log.response_status >= 400:
                rejection_reason = f"HTTP {log.response_status} error from broker/execution"
            elif log.response_status == 0 or log.response_status is None:
                rejection_reason = "Execution failed (no response received)"

        enriched_logs.append({
            "id": log.id,
            "webhook_id": log.webhook_id,
            "source": log.source,
            "source_ip": log.source_ip,
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "processed": log.processed,
            "processing_time_ms": log.processing_time_ms,
            "response_status": log.response_status,
            "error_message": log.error_message,
            # Extracted from payload (check all aliases: quantity, contracts, volume)
            "action": payload_data.get("action"),
            "symbol": payload_data.get("symbol"),
            "quantity": payload_data.get("quantity") or payload_data.get("contracts") or payload_data.get("volume") or 0.01,
            # Execution details
            "total_accounts": response_data.get("total_accounts", 1) if response_data else 1,
            "successful_accounts": response_data.get("successful", 1 if log.processed else 0) if response_data else (1 if log.processed else 0),
            "failed_accounts": response_data.get("failed", 0 if log.processed else 1) if response_data else (0 if log.processed else 1),
            "executions": executions,
            # NEW: Human-readable rejection reason
            "rejection_reason": rejection_reason,
            "result_status": result_status,
        })

    return enriched_logs

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
            "custom": SignalSource.CUSTOM,
        }
        source = source_map.get(webhook_config.source.lower(), SignalSource.TRADINGVIEW)

        # Map action string to enum
        action_str = signal_data.get("action", "buy").lower()
        action_map = {
            "buy": SignalAction.BUY,
            "sell": SignalAction.SELL,
            "close": SignalAction.CLOSE,
            "close_all": SignalAction.CLOSE,
            "limit_buy": SignalAction.BUY,
            "limit_sell": SignalAction.SELL,
            "stop_buy": SignalAction.BUY,
            "stop_sell": SignalAction.SELL,
            "modify": SignalAction.MODIFY,
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

        # Execute signal on accounts - handle MetaAPI (MT4/MT5) accounts directly
        execution_results = []
        non_metaapi_account_ids = []

        for account_id in target_account_ids:
            account = accounts_by_id.get(account_id)
            if not account:
                continue

            # Check if this is an MT5/MT4 account with MetaAPI
            if account.broker in (DBBrokerType.MT5, DBBrokerType.MT4):
                metaapi_account_id = (account.extra_metadata or {}).get("metaapi_account_id")
                if metaapi_account_id:
                    # Execute directly via MetaAPI
                    try:
                        exec_result = await execute_metaapi_trade(
                            metaapi_account_id=metaapi_account_id,
                            symbol=signal_data.get("symbol", "UNKNOWN"),
                            action=action_str,
                            volume=float(signal_data.get("quantity", 0.01) or 0.01),
                            stop_loss=float(payload.get("stop_loss") or payload.get("sl") or payload.get("stop") or 0) if payload.get("stop_loss") or payload.get("sl") or payload.get("stop") else None,
                            take_profit=float(payload.get("take_profit") or payload.get("tp") or payload.get("target") or 0) if payload.get("take_profit") or payload.get("tp") or payload.get("target") else None,
                            price=float(payload.get("price") or 0) if payload.get("price") else None,
                            trailing_stop=float(payload.get("trailing_stop") or payload.get("trailing") or 0) if payload.get("trailing_stop") or payload.get("trailing") else None,
                            comment=payload.get("comment"),
                        )
                        execution_results.append({
                            "account_id": account_id,
                            "broker": account.broker.value,
                            "success": exec_result.get("success", False),
                            "order_id": exec_result.get("order_id"),
                            "error": exec_result.get("error"),
                        })
                    except Exception as e:
                        logger.error(f"MetaAPI execution failed for account {account_id}: {e}")
                        execution_results.append({
                            "account_id": account_id,
                            "broker": account.broker.value,
                            "success": False,
                            "error": str(e),
                        })
                    continue

            # Non-MetaAPI accounts go through regular use case
            non_metaapi_account_ids.append(account_id)

        # Execute regular use case for non-MetaAPI accounts
        if non_metaapi_account_ids:
            command_for_non_metaapi = ProcessSignalRequest(
                source=source,
                symbol=signal_data.get("symbol", "UNKNOWN"),
                action=action,
                volume=Decimal(str(signal_data.get("quantity", 1) or 1)),
                price=Decimal(str(payload["price"])) if payload.get("price") else None,
                stop_loss=Decimal(str(payload.get("stop_loss") or payload.get("stop", 0))) if payload.get("stop_loss") or payload.get("stop") else None,
                take_profit=Decimal(str(payload.get("take_profit") or payload.get("target", 0))) if payload.get("take_profit") or payload.get("target") else None,
                target_account_ids=[str(aid) for aid in non_metaapi_account_ids],
                comment=payload.get("comment"),
                strategy_id=payload.get("strategy_id"),
                strategy_name=payload.get("strategy_name"),
                raw_payload=payload,
            )
            use_case_result = await use_case.execute(command_for_non_metaapi)
            # Merge results
            for detail in use_case_result.execution_details or []:
                execution_results.append(detail)

        # Build combined result
        successes = [r for r in execution_results if r.get("success")]
        errors = [r.get("error") for r in execution_results if r.get("error")]

        # Create a mock use_case_result for compatibility
        class MockResult:
            def __init__(self, signal_id, status, executions, errors, execution_details):
                self.signal_id = signal_id
                self.status = status
                self.executions = executions
                self.errors = errors
                self.execution_details = execution_details

        use_case_result = MockResult(
            signal_id=str(uuid.uuid4()),
            status=SignalStatus.PROCESSED if successes else SignalStatus.FAILED,
            executions=len(successes),
            errors=errors,
            execution_details=execution_results,
        )

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
        # Log error - update existing log if it exists, otherwise try to create
        try:
            if 'db_webhook' in locals() and db_webhook is not None:
                # Update existing log
                db_webhook.processed = False
                db_webhook.error_message = str(e)
                db.commit()
            else:
                # Create new log with a fresh webhook_id to avoid duplicates
                error_webhook_id = str(uuid.uuid4())
                db_webhook = WebhookLog(
                    webhook_id=error_webhook_id,
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
            db.rollback()  # Best effort logging, don't fail on logging errors

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
