from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from app.db.database import get_db
from app.models.models import Signal as SignalORM, User, Account, Position, Trade
from app.routers.auth import get_current_user
from app.infrastructure.container import get_container
from app.domain.enums import SignalStatus, BrokerType
from app.models.schemas import Signal as SignalSchema
from app.models.database_models import WebhookConfig
from app.application.dto.signal_dto import ProcessSignalRequest
from app.domain.services.signal_service import SignalService
from app.utils.webhook_validation import safe_parse_webhook_payload, validate_webhook_payload_structure
from app.routers.webhooks import generate_webhook_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])

@router.get("/")
async def get_signals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    status: Optional[str] = Query(None, description="Filter by signal status: pending, executed, failed, skipped"),
    offset: int = 0
):
    """
    Get signals with optional status filtering.
    
    This endpoint now supports the status query parameter for filtering signals.
    """
    try:
        # Get user-specific signals if authenticated
        query = db.query(SignalORM)
        if current_user:
            query = query.filter(SignalORM.user_id == current_user.id)
        
        # Filter by status if provided
        if status:
            query = query.filter(SignalORM.status == status)
        
        signals = query.order_by(SignalORM.created_at.desc()).offset(offset).limit(limit).all()
        
        return [
            {
                "id": signal.id,
                "symbol": signal.symbol,
                "action": signal.action,
                "quantity": signal.quantity,
                "price": signal.price,
                "status": signal.status,
                "created_at": signal.created_at.isoformat(),
                "updated_at": signal.updated_at.isoformat() if signal.updated_at else None,
                "executions": signal.execution_details or [],
                "errors": signal.errors or [],
            }
            for signal in signals
        ]
        
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get signals"
        )