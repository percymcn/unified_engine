"""
Strategy Execution Router
Endpoints to trigger strategy execution
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Optional, Any

from app.db.database import get_db
from app.models.models import Account, User
from app.routers.auth import get_current_user
from app.services.strategy_runner import strategy_runner

router = APIRouter(prefix="/strategy-execution", tags=["strategy-execution"])

@router.post("/run")
async def run_strategy(
    strategy_id: str,
    account_id: int,
    parameters: Optional[Dict[str, Any]] = None,
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run a strategy for an account"""
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Run strategy
    result = await strategy_runner.run_strategy(strategy_id, account_id, parameters)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Strategy execution failed")
        )
    
    return result

@router.post("/start-periodic")
async def start_periodic_strategy(
    strategy_id: str,
    account_id: int,
    interval_seconds: int = 60,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Start periodic execution of a strategy"""
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    await strategy_runner.start_periodic_execution(strategy_id, account_id, interval_seconds)
    
    return {
        "message": f"Started periodic execution of {strategy_id} for account {account_id}",
        "interval_seconds": interval_seconds
    }

@router.post("/stop-periodic")
async def stop_periodic_strategy(
    strategy_id: str,
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop periodic execution of a strategy"""
    # Verify account ownership
    account = db.query(Account).filter(
        Account.id == account_id,
        Account.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    await strategy_runner.stop_periodic_execution(strategy_id, account_id)
    
    return {
        "message": f"Stopped periodic execution of {strategy_id} for account {account_id}"
    }
