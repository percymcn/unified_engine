"""
Strategy Management Router
Handles strategy registry, enable/disable, and statistics
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import func, and_
from pydantic import BaseModel

from app.db.database import get_db
from app.models.models import Strategy, AccountStrategy, Account, Signal, User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/strategies", tags=["strategies"])


class StrategyCreateBody(BaseModel):
    strategy_id: str
    strategy_name: str
    strategy_source: str = "manual"
    strategy_version: str = "1.0.0"
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    is_active: bool = True


def _serialize_strategy(strategy: Strategy) -> Dict[str, Any]:
    return {
        "id": strategy.id,
        "strategy_id": strategy.strategy_id,
        "strategy_name": strategy.strategy_name,
        "strategy_version": strategy.strategy_version,
        "strategy_source": strategy.strategy_source,
        "strategy_type": strategy.strategy_source,
        "description": strategy.description,
        "is_active": strategy.is_active,
        "status": "active" if strategy.is_active else "inactive",
        "sharpe_ratio": None,
        "win_rate": None,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
    }

@router.get("/top")
async def get_top_strategies(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get top performing strategies"""
    # Get strategies with signal counts and success rates
    strategies = db.query(
        Strategy,
        func.count(Signal.id).label('signal_count'),
        func.sum(func.cast(Signal.status == 'processed', func.Integer)).label('success_count')
    ).join(
        Signal, Signal.strategy_id == Strategy.strategy_id
    ).filter(
        Signal.user_id == current_user.id
    ).group_by(
        Strategy.id
    ).order_by(
        func.count(Signal.id).desc()
    ).limit(limit).all()
    
    return [
        {
            "strategy_id": s.Strategy.strategy_id,
            "strategy_name": s.Strategy.strategy_name,
            "strategy_version": s.Strategy.strategy_version,
            "strategy_source": s.Strategy.strategy_source,
            "signal_count": s.signal_count or 0,
            "success_count": s.success_count or 0,
            "success_rate": (s.success_count or 0) / (s.signal_count or 1) * 100
        }
        for s in strategies
    ]

@router.get("/")
async def list_strategies(
    source: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all strategies"""
    query = db.query(Strategy)
    
    if source:
        query = query.filter(Strategy.strategy_source == source)
    
    strategies = query.all()
    serialized = [_serialize_strategy(s) for s in strategies]
    return {"strategies": serialized, "total": len(serialized)}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_strategy(
    body: StrategyCreateBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a strategy record. Does not start live trading."""
    existing = db.query(Strategy).filter(Strategy.strategy_id == body.strategy_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Strategy already exists",
        )

    strategy = Strategy(
        strategy_id=body.strategy_id,
        strategy_name=body.strategy_name,
        strategy_version=body.strategy_version,
        strategy_source=body.strategy_source,
        description=body.description,
        is_active=body.is_active,
        parameters=body.parameters,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return _serialize_strategy(strategy)

@router.get("/{strategy_id}/stats")
async def get_strategy_stats(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get statistics for a specific strategy"""
    strategy = db.query(Strategy).filter(
        Strategy.strategy_id == strategy_id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Get signal statistics
    signals = db.query(Signal).filter(
        Signal.strategy_id == strategy_id,
        Signal.user_id == current_user.id
    ).all()
    
    total_signals = len(signals)
    processed_signals = len([s for s in signals if s.status == 'processed'])
    failed_signals = len([s for s in signals if s.status == 'failed'])
    
    return {
        "strategy_id": strategy.strategy_id,
        "strategy_name": strategy.strategy_name,
        "strategy_version": strategy.strategy_version,
        "total_signals": total_signals,
        "processed_signals": processed_signals,
        "failed_signals": failed_signals,
        "success_rate": (processed_signals / total_signals * 100) if total_signals > 0 else 0
    }

@router.post("/{strategy_id}/enable")
async def enable_strategy(
    strategy_id: str,
    account_id: int,
    parameters: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Enable a strategy for an account"""
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
    
    # Get or create strategy
    strategy = db.query(Strategy).filter(
        Strategy.strategy_id == strategy_id
    ).first()
    
    if not strategy:
        # Auto-create strategy if it doesn't exist
        strategy = Strategy(
            strategy_id=strategy_id,
            strategy_name=strategy_id,
            strategy_version="1.0.0",
            strategy_source="inhouse"
        )
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
    
    # Enable strategy for account
    account_strategy = db.query(AccountStrategy).filter(
        AccountStrategy.account_id == account_id,
        AccountStrategy.strategy_id == strategy.id
    ).first()
    
    if account_strategy:
        account_strategy.is_enabled = True
        if parameters:
            account_strategy.parameters = parameters
    else:
        account_strategy = AccountStrategy(
            account_id=account_id,
            strategy_id=strategy.id,
            is_enabled=True,
            parameters=parameters or {}
        )
        db.add(account_strategy)
    
    db.commit()
    
    return {
        "message": f"Strategy {strategy_id} enabled for account {account_id}",
        "strategy_id": strategy_id,
        "account_id": account_id,
        "enabled": True
    }

@router.post("/{strategy_id}/disable")
async def disable_strategy(
    strategy_id: str,
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable a strategy for an account"""
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
    
    # Get strategy
    strategy = db.query(Strategy).filter(
        Strategy.strategy_id == strategy_id
    ).first()
    
    if not strategy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Strategy not found"
        )
    
    # Disable strategy for account
    account_strategy = db.query(AccountStrategy).filter(
        AccountStrategy.account_id == account_id,
        AccountStrategy.strategy_id == strategy.id
    ).first()
    
    if account_strategy:
        account_strategy.is_enabled = False
        db.commit()
    
    return {
        "message": f"Strategy {strategy_id} disabled for account {account_id}",
        "strategy_id": strategy_id,
        "account_id": account_id,
        "enabled": False
    }
