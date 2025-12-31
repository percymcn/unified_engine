from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
import uuid
import json

from app.db.database import get_db
from app.models.models import WebhookLog, User
from app.models.schemas import WebhookLog as WebhookLogSchema, WebhookLogCreate
from app.routers.auth import get_current_user

router = APIRouter()

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
        
        # Process signal through signal processor
        from app.services.signal_processor import SignalProcessor
        processor = SignalProcessor()
        
        signal_data = {
            "source": "tradingview",
            "payload": payload,
            "strategy_info": strategy_info
        }
        
        result = await processor.process_signal(signal_data, db)
        
        # Update webhook log
        db_webhook.processed = result.get("success", False)
        db_webhook.response_status = 200
        db_webhook.response_body = json.dumps(result)
        db_webhook.processing_time_ms = result.get("processing_time_ms", 0)
        db.commit()
        
        return result
        
    except Exception as e:
        # Log error
        db_webhook = WebhookLog(
            webhook_id=webhook_id,
            source="tradingview",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(payload),
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
        
        # Process signal through signal processor
        from app.services.signal_processor import SignalProcessor
        processor = SignalProcessor()
        
        signal_data = {
            "source": "trailhacker",
            "payload": payload
        }
        
        result = await processor.process_signal(signal_data, db)
        
        # Update webhook log
        db_webhook.processed = result.get("success", False)
        db_webhook.response_status = 200
        db_webhook.response_body = json.dumps(result)
        db_webhook.processing_time_ms = result.get("processing_time_ms", 0)
        db.commit()
        
        return result
        
    except Exception as e:
        # Log error
        db_webhook = WebhookLog(
            webhook_id=webhook_id,
            source="trailhacker",
            source_ip=request.client.host if request.client else "unknown",
            user_agent=request.headers.get("user-agent"),
            payload=json.dumps(payload),
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