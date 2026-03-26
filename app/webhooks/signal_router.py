"""
Webhook Signal Router
Handles TradingView, TrailHacker, and custom webhook signals

This router now integrates with WebhookConfig for multi-account routing.
If a webhook_key matches a WebhookConfig, it uses the AccountRoutingService.
Otherwise, it falls back to the legacy signal_processor flow.
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.services.signal_processor import signal_processor
from app.models.pydantic_schemas import WebhookRequest, WebhookResponse
from app.models.database_models import WebhookConfig
from app.db.database import get_db
from app.core.config import settings
from app.routers.auth import verify_api_key, get_current_user_optional
from app.models.models import User


async def get_debug_route_user(
    bearer_user: Optional[User] = Depends(get_current_user_optional),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    """Allow bearer auth for user-facing debug routes while keeping API-key fallback."""
    if bearer_user:
        return bearer_user
    if api_key:
        return await verify_api_key(api_key=api_key, db=db)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )

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
                # TradingView webhook validation - accept either ticker or symbol
                has_symbol = "ticker" in payload or "symbol" in payload
                has_action = "action" in payload
                return has_symbol and has_action
            
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
    """Handle TradingView webhook signals

    This endpoint now supports both:
    1. WebhookConfig routing (multi-account) - if key matches a WebhookConfig
    2. Legacy signal_processor routing - fallback for direct account keys
    """
    try:
        # Validate webhook key
        if not webhook_key or len(webhook_key) < 10:
            raise HTTPException(status_code=401, detail="Invalid webhook key")

        # Parse payload
        try:
            payload = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON payload")

        # Check if this webhook_key matches a WebhookConfig (multi-account routing)
        webhook_config = db.query(WebhookConfig).filter(
            WebhookConfig.webhook_key == webhook_key,
            WebhookConfig.is_active == True
        ).first()

        if webhook_config:
            # Use the new webhook_execute router for proper multi-account routing
            logger.info(f"WebhookConfig found for key {webhook_key[:12]}..., using multi-account routing")

            # Import here to avoid circular imports
            from app.routers.webhook_execute import execute_tradingview_signal

            # Inject webhook_key into payload if not present
            if "webhook_key" not in payload:
                payload["webhook_key"] = webhook_key

            # Create a new request-like object with the modified payload
            # We'll use a simple approach: store the payload and let execute_tradingview_signal read it
            request._json = payload
            request._body = json.dumps(payload).encode()

            # Call the execute endpoint directly
            return await execute_tradingview_signal(request, db)

        # Fallback to legacy signal_processor for direct account keys
        logger.info(f"No WebhookConfig for key {webhook_key[:12]}..., using legacy routing")

        # Validate TradingView specific format
        if not webhook_router.validate_webhook_payload("tradingview", payload):
            raise HTTPException(status_code=400, detail="Invalid TradingView webhook format")

        # Process webhook via legacy signal_processor
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
    current_user: User = Depends(get_debug_route_user)
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
async def get_webhook_status(current_user: User = Depends(get_debug_route_user)):
    """Get webhook processing status."""
    try:
        from sqlalchemy import func, desc
        from app.models.models import Signal
        from app.db.database import get_db
        
        # Multi-user platform: brokers connect per-request with DB credentials
        # Show execution activity instead of placeholder connection status
        broker_stats = {}
        brokers = getattr(signal_processor, "brokers", {}) or {}
        
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=24)
        
        db_gen = get_db()
        db = next(db_gen)
        try:
            # Overall platform stats (not broken down by broker to avoid schema issues)
            total_signals_24h = db.query(func.count(Signal.id)).filter(
                Signal.created_at >= cutoff
            ).scalar() or 0
            
            # Successful = "executed" (full success) + "partial" (some accounts succeeded)
            executed_24h = db.query(func.count(Signal.id)).filter(
                Signal.created_at >= cutoff,
                Signal.status == "executed"
            ).scalar() or 0
            
            partial_24h = db.query(func.count(Signal.id)).filter(
                Signal.created_at >= cutoff,
                Signal.status == "partial"
            ).scalar() or 0
            
            failed_24h = db.query(func.count(Signal.id)).filter(
                Signal.created_at >= cutoff,
                Signal.status == "failed"
            ).scalar() or 0
            
            pending_24h = db.query(func.count(Signal.id)).filter(
                Signal.created_at >= cutoff,
                Signal.status == "pending"
            ).scalar() or 0
            
            successful_24h = executed_24h + partial_24h
            
            last_signal_time = db.query(Signal.created_at).order_by(
                desc(Signal.created_at)
            ).first()
            
            for broker_name in brokers.keys():
                broker_stats[broker_name] = {
                    "mode": "per-request",
                    "class": brokers[broker_name].__class__.__name__
                }
        finally:
            db.close()
        
        # Platform-wide activity summary
        platform_activity = {
            "total_signals_24h": total_signals_24h,
            "executed_24h": executed_24h,
            "partial_24h": partial_24h,
            "failed_24h": failed_24h,
            "pending_24h": pending_24h,
            "successful_24h": successful_24h,
            "success_rate_24h": f"{(successful_24h / total_signals_24h * 100):.1f}%" if total_signals_24h > 0 else "N/A",
            "last_signal": last_signal_time[0].isoformat() if last_signal_time else None
        }

        webhook_configs = getattr(webhook_router, "webhook_configs", {}) or {}
        config_summary = {
            "type": type(webhook_configs).__name__,
            "count": len(webhook_configs) if hasattr(webhook_configs, "__len__") else None,
        }
        if isinstance(webhook_configs, dict):
            config_summary["keys"] = list(webhook_configs.keys())[:20]

        return JSONResponse(
            status_code=200,
            content={
                "status": "active",
                "platform_mode": "multi-user",
                "connection_model": "per-request with DB credentials",
                "supported_sources": list(getattr(webhook_router, "supported_sources", [])),
                "broker_executors": broker_stats,
                "platform_activity": platform_activity,
                "webhook_config_summary": config_summary,
                "timestamp": datetime.now().isoformat()
            }
        )

    except Exception as e:
        logger.exception(f"Error getting webhook status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/test")
async def test_webhook(
    request: Request,
    current_user: User = Depends(get_debug_route_user)
):
    """Test webhook processing"""
    try:
        # Parse test payload
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if payload is None:
            payload = {}
        
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
async def get_webhook_config(current_user: User = Depends(get_debug_route_user)):
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