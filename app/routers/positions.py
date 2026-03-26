from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime
import logging

from app.db.database import get_db
from app.models.models import Position, User
from app.models.database_models import TradingAccount
from app.models.schemas import Position as PositionSchema, PositionCreate
from app.routers.auth import get_current_user
from app.services.position_sync_service import PositionSyncService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[PositionSchema])
async def get_positions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all positions for current user"""
    positions = db.query(Position).join(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        Position.is_active == True
    ).offset(skip).limit(limit).all()
    return positions

@router.post("/", response_model=PositionSchema)
async def create_position(
    position: PositionCreate,
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new position"""
    # Verify account ownership
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    db_position = Position(
        **position.dict(),
        account_id=account_id
    )
    db.add(db_position)
    db.commit()
    db.refresh(db_position)
    return db_position

@router.get("/{position_id}", response_model=PositionSchema)
async def get_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific position"""
    position = db.query(Position).join(TradingAccount).filter(
        Position.id == position_id,
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    return position

@router.post("/{position_id}/close")
async def close_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Close position"""
    position = db.query(Position).join(TradingAccount).filter(
        Position.id == position_id,
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Position not found"
        )
    
    position.is_active = False
    position.close_time = datetime.utcnow()
    db.commit()
    
    return {"message": "Position closed successfully"}

@router.get("/account/{account_id}", response_model=List[PositionSchema])
async def get_account_positions(
    account_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get positions for specific account"""
    # Verify account ownership
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    positions = db.query(Position).filter(
        Position.account_id == account_id,
        Position.is_active == True
    ).offset(skip).limit(limit).all()
    return positions


@router.post("/account/{account_id}/sync", response_model=Dict[str, Any])
async def sync_account_positions(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sync positions with broker - reconcile database with actual broker positions.

    This endpoint:
    - Fetches current positions from broker
    - Marks any database positions as closed if not found at broker
    - Returns reconciliation report

    Use this to fix max_positions issues caused by positions closed via TP/SL/manual.
    """
    from app.routers.webhook_execute import _create_account_executor

    # Verify account ownership
    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == current_user.id
    ).first()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )

    try:
        # Create executor for this account
        executor, needs_cleanup = await _create_account_executor(account, db)
        if not executor:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create executor for account"
            )

        # Initialize if needed
        is_conn_attr = getattr(executor, 'is_connected', None)
        is_connected = is_conn_attr() if callable(is_conn_attr) else bool(is_conn_attr)
        if not is_connected:
            await executor.initialize()

        # Run reconciliation
        sync_service = PositionSyncService(db)
        report = await sync_service.reconcile_all_positions(account_id, executor)

        # Cleanup executor
        if needs_cleanup and hasattr(executor, 'disconnect'):
            try:
                await executor.disconnect()
            except:
                pass

        logger.info(f"Position sync for account {account_id}: {report}")
        return report

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Position sync failed for account {account_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Position sync failed: {str(e)}"
        )


@router.post("/cleanup-stale", response_model=Dict[str, Any])
async def cleanup_stale_positions(
    max_age_hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark old 'open' positions as closed if they haven't been updated.

    Use sparingly - this marks positions as closed based on age, not broker confirmation.
    """
    sync_service = PositionSyncService(db)
    count = await sync_service.cleanup_stale_positions(max_age_hours)

    return {
        "message": f"Marked {count} stale positions as closed",
        "stale_closed": count,
        "max_age_hours": max_age_hours
    }
