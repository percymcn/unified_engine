"""
Webhook Signal Router
Handles TradingView, TrailHacker, and custom webhook signals
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.services.signal_processor import signal_processor
from app.models.pydantic_schemas import WebhookRequest, WebhookResponse
from app.db.database import get_db
from app.core.config import settings
from app.routers.auth import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

class WebhookSignalRouter:
    """Unified webhook signal router"""
    
    def __init__(self):
        self.supported_sources = ["tradingview", "trailhacker", "custom"]
        self.webhook_configs = settings.get_webhook_config()
    
    async def process_webhook_request(
        self,
        request: Request,
        source: str,
        background_tasks: BackgroundTasks,
        db: Session
    ) -> JSONResponse:
        """Process incoming webhook request"""
        try:
            # Get request details
            headers = dict(request.headers)
            payload = await request.json()
            ip_address = request.client.host
            user_agent = headers.get("user-agent", "")
            
            # Create webhook request object
            webhook_request = WebhookRequest(
                source=source,
                payload=payload,
                headers=headers,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Add to background processing
            background_tasks.add_task(
                self._process_webhook_background,
                webhook_request
            )
            
            return JSONResponse(
                status_code=202,
                content={
                    "status": "accepted",
                    "message": "Webhook received for processing",
                    "source": source,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing webhook from {source}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _process_webhook_background(self, webhook_request: WebhookRequest):
        """Process webhook in background"""
        try:
            # Process webhook through signal processor
            result = await signal_processor.process_webhook(webhook_request)
            
            # Log result
            logger.info(f"Webhook processed: {result}")
            
        except Exception as e:
            logger.error(f"Error in background webhook processing: {e}")
    
    def validate_webhook_source(self, source: str) -> bool:
        """Validate webhook source"""
        return source.lower() in self.supported_sources
    
    def validate_webhook_payload(self, source: str, payload: Dict[str, Any]) -> bool:
        """Validate webhook payload based on source"""
        try:
            if source == "tradingview":
                # TradingView webhook validation
                required_fields = ["ticker", "action"]
                return all(field in payload for field in required_fields)
            
            elif source == "trailhacker":
                # TrailHacker webhook validation
                required_fields = ["symbol", "signal"]
                return all(field in payload for field in required_fields)
            
            elif source == "custom":
                # Custom webhook - more flexible
                return "symbol" in payload or "ticker" in payload
            
            return False
            
        except Exception as e:
            logger.error(f"Error validating webhook payload: {e}")
            return False

# Global webhook router instance
webhook_router = WebhookSignalRouter()

@router.post("/tradingview/{webhook_key}")
async def tradingview_webhook(
    webhook_key: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle TradingView webhook signals"""
    try:
        # Validate webhook key (in production, this would be more sophisticated)
        if not webhook_key or len(webhook_key) < 10:
            raise HTTPException(status_code=401, detail="Invalid webhook key")
        
        # Parse and validate payload
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Validate TradingView specific format
        if not webhook_router.validate_webhook_payload("tradingview", payload):
            raise HTTPException(status_code=400, detail="Invalid TradingView webhook format")
        
        # Process webhook
        return await webhook_router.process_webhook_request(
            request, "tradingview", background_tasks, db
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TradingView webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/trailhacker/{webhook_key}")
async def trailhacker_webhook(
    webhook_key: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle TrailHacker webhook signals"""
    try:
        # Validate webhook key
        if not webhook_key or len(webhook_key) < 10:
            raise HTTPException(status_code=401, detail="Invalid webhook key")
        
        # Parse and validate payload
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Validate TrailHacker specific format
        if not webhook_router.validate_webhook_payload("trailhacker", payload):
            raise HTTPException(status_code=400, detail="Invalid TrailHacker webhook format")
        
        # Process webhook
        return await webhook_router.process_webhook_request(
            request, "trailhacker", background_tasks, db
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TrailHacker webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/custom/{source}/{webhook_key}")
async def custom_webhook(
    source: str,
    webhook_key: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Handle custom webhook signals"""
    try:
        # Validate source
        if not webhook_router.validate_webhook_source(source):
            raise HTTPException(status_code=400, detail="Unsupported webhook source")
        
        # Validate webhook key
        if not webhook_key or len(webhook_key) < 10:
            raise HTTPException(status_code=401, detail="Invalid webhook key")
        
        # Parse and validate payload
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
        # Validate custom webhook format
        if not webhook_router.validate_webhook_payload("custom", payload):
            raise HTTPException(status_code=400, detail="Invalid custom webhook format")
        
        # Process webhook
        return await webhook_router.process_webhook_request(
            request, source, background_tasks, db
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Custom webhook error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/history")
async def get_webhook_history(
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    """Get webhook processing history"""
    try:
        history = await signal_processor.get_webhook_history(limit)
        
        return JSONResponse(
            status_code=200,
            content={
                "webhooks": history,
                "count": len(history),
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting webhook history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/status")
async def get_webhook_status(api_key: str = Depends(verify_api_key)):
    """Get webhook processing status"""
    try:
        # Get broker connection status
        broker_status = {}
        for broker_name, broker in signal_processor.brokers.items():
            broker_status[broker_name] = {
                "connected": broker.is_connected,
                "last_check": datetime.now().isoformat()
            }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "active",
                "supported_sources": webhook_router.supported_sources,
                "broker_connections": broker_status,
                "webhook_config": webhook_router.webhook_configs,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting webhook status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/test")
async def test_webhook(
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """Test webhook processing"""
    try:
        # Parse test payload
        payload = await request.json()
        
        # Create test webhook request
        webhook_request = WebhookRequest(
            source="test",
            payload=payload,
            headers=dict(request.headers),
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", "")
        )
        
        # Process webhook synchronously for testing
        result = await signal_processor.process_webhook(webhook_request)
        
        return JSONResponse(
            status_code=200,
            content={
                "test_result": result,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error testing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/config")
async def get_webhook_config(api_key: str = Depends(verify_api_key)):
    """Get webhook configuration"""
    try:
        return JSONResponse(
            status_code=200,
            content={
                "config": webhook_router.webhook_configs,
                "supported_sources": webhook_router.supported_sources,
                "endpoints": {
                    "tradingview": f"/webhooks/tradingview/{{webhook_key}}",
                    "trailhacker": f"/webhooks/trailhacker/{{webhook_key}}",
                    "custom": f"/webhooks/custom/{{source}}/{{webhook_key}}"
                },
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting webhook config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")