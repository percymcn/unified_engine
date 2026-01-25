"""
Per-Broker Secure Webhook Endpoint

Patch 1.2.1: Secure per-broker webhooks
- Each broker connection has its own webhook key
- Webhook requests must specify broker + user + key
- Mismatched keys are rejected (fail-closed) and logged to discard_bin
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends, Query, Header
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
import uuid
import json
import logging
import hashlib

from app.db.database import get_db
from app.models.models import WebhookLog, User
from app.models.database_models import DiscardBin, TradingAccount
from app.models.schemas import WebhookLogCreate
from app.routers.auth import get_current_user
from app.dependencies import get_container
from app.application.dto.signal_dto import ProcessSignalRequest
from app.domain.enums import SignalSource, SignalAction
from app.domain.services.routing_service import build_signal_data
from app.domain.services import (
    RiskEnforcementService,
    AccountRiskSettings,
    DailyCounterService,
)
from app.infrastructure.repositories import get_daily_counter_repository
from app.infrastructure.adapters.position_counter_adapter import PositionCounterAdapter
from app.routers.webhooks import evaluate_guard_layer

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/incoming")
async def incoming_webhook(
    request: Request,
    db: Session = Depends(get_db),
    broker: str = Query(..., description="Broker slug (tradelocker, tradovate, projectx, mt4, mt5)"),
    user: int = Query(..., description="User ID"),
    key: Optional[str] = Query(None, description="Webhook key (query param)"),
    x_tradeflow_webhook_key: Optional[str] = Header(None, alias="X-TradeFlow-Webhook-Key", description="Webhook key (header)")
):
    """
    Per-broker secure webhook endpoint.
    
    Requires:
    - broker: Broker slug (required)
    - user: User ID (required)
    - key: Webhook key (query param OR X-TradeFlow-Webhook-Key header)
    
    Validates broker + user + key match before routing signal to that broker only.
    """
    start_time = datetime.utcnow()
    webhook_id = str(uuid.uuid4())
    
    # Get webhook key from query or header
    webhook_key = key or x_tradeflow_webhook_key
    
    if not webhook_key:
        logger.warning(f"Webhook request missing key: broker={broker}, user={user}")
        # Log to discard_bin
        try:
            payload_str = json.dumps(await request.json() if request.headers.get("content-type", "").startswith("application/json") else {})
            payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
            
            discard_entry = DiscardBin(
                user_id=user,
                received_at=datetime.utcnow(),
                reason="broker_mismatch",
                age_ms=0,
                symbol="UNKNOWN",
                side="unknown",
                broker_target=broker,
                raw_payload=payload_str[:500]  # Truncate for storage
            )
            db.add(discard_entry)
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log discard: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook key required. Provide 'key' query param or 'X-TradeFlow-Webhook-Key' header."
        )
    
    try:
        # Get request payload
        if request.headers.get("content-type", "").startswith("application/json"):
            payload = await request.json()
        else:
            form_data = await request.form()
            payload = dict(form_data)
        
        # Create webhook log
        webhook_log = WebhookLogCreate(
            webhook_id=webhook_id,
            source="incoming",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(payload)
        )
        
        db_webhook = WebhookLog(**webhook_log.dict())
        db.add(db_webhook)
        db.commit()
        
        # Validate user exists
        user_obj = db.query(User).filter(User.id == user).first()
        if not user_obj:
            logger.warning(f"Invalid user_id in webhook: {user}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Find broker connection matching broker + webhook_key
        # Handle broker enum comparison properly
        from app.models.database_models import BrokerType as ORMBrokerType
        
        broker_enum = None
        try:
            broker_enum = ORMBrokerType[broker.upper()]
        except (KeyError, AttributeError):
            # Try lowercase
            try:
                broker_enum = ORMBrokerType[broker.lower()]
            except (KeyError, AttributeError):
                logger.warning(f"Invalid broker slug: {broker}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid broker: {broker}"
                )
        
        # Use TradingAccount model (table name: trading_accounts)
        broker_account = db.query(TradingAccount).filter(
            TradingAccount.user_id == user,
            TradingAccount.broker == broker_enum,
            TradingAccount.webhook_key == webhook_key,
            TradingAccount.is_active == True
        ).first()
        
        if not broker_account:
            # Broker/key mismatch - fail closed
            logger.warning(
                f"Webhook key mismatch: broker={broker}, user={user}, key={webhook_key[:8]}..."
            )
            
            # Log to discard_bin
            try:
                payload_str = json.dumps(payload)
                payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]
                
                discard_entry = DiscardBin(
                    user_id=user,
                    received_at=datetime.utcnow(),
                    reason="broker_mismatch",
                    age_ms=0,
                    symbol=payload.get("ticker") or payload.get("symbol", "UNKNOWN"),
                    side=payload.get("action") or payload.get("signal", "unknown"),
                    broker_target=broker,
                    raw_payload=payload_str[:500]
                )
                db.add(discard_entry)
                db.commit()
            except Exception as e:
                logger.error(f"Failed to log discard: {e}")
            
            db_webhook.processed = False
            db_webhook.response_status = 403
            db_webhook.response_body = json.dumps({"error": "Invalid broker or webhook key"})
            db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid broker or webhook key. Signal not executed."
            )
        
        # Valid match - route signal ONLY to this broker account
        logger.info(f"Webhook validated: broker={broker}, account_id={broker_account.id}, user={user}")
        
        # Build signal data
        signal_data = build_signal_data(payload, "tradingview")  # Default to tradingview format
        
        # Map action
        action_str = signal_data.get("action", "buy").lower()
        action_map = {
            "buy": SignalAction.BUY,
            "sell": SignalAction.SELL,
            "close": SignalAction.CLOSE,
        }
        action = action_map.get(action_str, SignalAction.BUY)
        
        # Build command targeting ONLY this broker account
        command = ProcessSignalRequest(
            source=SignalSource.TRADINGVIEW,
            symbol=signal_data.get("symbol", "UNKNOWN"),
            action=action,
            volume=Decimal(str(signal_data.get("quantity", 1) or 1)),
            price=Decimal(str(payload["price"])) if payload.get("price") else None,
            stop_loss=Decimal(str(payload.get("stop_loss") or payload.get("stop", 0))) if payload.get("stop_loss") or payload.get("stop") else None,
            take_profit=Decimal(str(payload.get("take_profit") or payload.get("target", 0))) if payload.get("take_profit") or payload.get("target") else None,
            target_account_ids=[str(broker_account.id)],  # ONLY this broker account
            comment=payload.get("comment"),
            strategy_id=payload.get("strategy_id"),
            strategy_name=payload.get("strategy_name"),
            raw_payload=payload,
        )
        
        # Get accounts for guard layer
        accounts_by_id = {broker_account.id: broker_account}
        
        # SIGNAL INTELLIGENCE GUARD LAYER - Evaluate signal before execution
        guard_response = await evaluate_guard_layer(
            db=db,
            command=command,
            source=SignalSource.TRADINGVIEW,
            action=action,
            user_id=user,
            account_ids=[broker_account.id],
            accounts_by_id=accounts_by_id,
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
        
        # Execute use case - route ONLY to this broker account
        container = get_container(request)
        use_case = container.process_signal_use_case()
        use_case_result = await use_case.execute(command)
        
        # Map domain result to API response
        result = {
            "success": use_case_result.status.value not in ["failed", "rejected"],
            "webhook_id": webhook_id,
            "signal_id": use_case_result.signal_id,
            "status": use_case_result.status.value,
            "broker": broker,
            "account_id": broker_account.id,
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing incoming webhook: {e}", exc_info=True)
        
        # Log error webhook
        db_webhook = WebhookLog(
            webhook_id=webhook_id,
            source="incoming",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(payload) if 'payload' in locals() else "{}",
            processed=False,
            error_message=str(e)
        )
        db.add(db_webhook)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing webhook"
        )
