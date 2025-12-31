from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid
import json

from app.db.database import get_db
from app.models.models import Signal, User, WebhookLog
from app.models.schemas import Signal as SignalSchema, SignalCreate, WebhookLog as WebhookLogSchema
from app.routers.auth import get_current_user
from app.services.signal_processor import SignalProcessor

router = APIRouter()

@router.get("/", response_model=List[SignalSchema])
async def get_signals(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all signals for current user"""
    signals = db.query(Signal).filter(
        Signal.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return signals

@router.post("/", response_model=SignalSchema)
async def create_signal(
    signal: SignalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new manual signal"""
    db_signal = Signal(
        signal_id=str(uuid.uuid4()),
        user_id=current_user.id,
        **signal.dict(),
        status="pending"
    )
    db.add(db_signal)
    db.commit()
    db.refresh(db_signal)
    return db_signal

@router.get("/{signal_id}", response_model=SignalSchema)
async def get_signal(
    signal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific signal"""
    signal = db.query(Signal).filter(
        Signal.signal_id == signal_id,
        Signal.user_id == current_user.id
    ).first()
    
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found"
        )
    
    return signal

@router.post("/{signal_id}/cancel")
async def cancel_signal(
    signal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel signal"""
    signal = db.query(Signal).filter(
        Signal.signal_id == signal_id,
        Signal.user_id == current_user.id
    ).first()
    
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found"
        )
    
    signal.status = "cancelled"
    db.commit()
    return {"message": "Signal cancelled"}

@router.get("/history")
async def get_signal_history(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get signal history"""
    from app.services.signal_processor import SignalProcessor
    processor = SignalProcessor()
    return await processor.get_signal_history(limit, current_user.id, db)

@router.get("/active")
async def get_active_signals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active signals"""
    from app.services.signal_processor import SignalProcessor
    processor = SignalProcessor()
    return await processor.get_active_signals(db)

@router.post("/execute")
async def execute_signal(
    signal_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute signal immediately"""
    from app.services.signal_processor import SignalProcessor
    processor = SignalProcessor()
    
    # Add user ID to signal data
    signal_data["user_id"] = current_user.id
    
    result = await processor.process_signal(signal_data, db)
    return result