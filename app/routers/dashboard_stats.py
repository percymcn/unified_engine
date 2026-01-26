from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date

from app.db.database import get_db
from app.models.models import Signal as SignalORM, Trade, Account, Position
from app.routers.auth import get_current_user
from app.models.schemas import User

router = APIRouter(prefix="/api/dashboard/stats", tags=["dashboard"])

@router.get("/")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by signal status: pending, executed, failed, skipped")
):
    """
    Get dashboard statistics aggregating signals, trades, accounts, and positions.
    
    This endpoint provides real-time stats for the frontend dashboard.
    """
    try:
        user_id = current_user.id if current_user else None
        
        # Base query filters
        signals_query = db.query(SignalORM)
        trades_query = db.query(Trade)
        accounts_query = db.query(Account)
        positions_query = db.query(Position)
        
        # Filter by user if authenticated
        if user_id:
            signals_query = signals_query.filter(SignalORM.user_id == user_id)
            trades_query = trades_query.filter(Trade.user_id == user_id)
            accounts_query = accounts_query.filter(Account.user_id == user_id)
            positions_query = positions_query.filter(Position.account.has(Account.id == Account.user_id))
        
        # Filter by status if provided
        if status:
            signals_query = signals_query.filter(SignalORM.status == status)
        
        # Get signals stats
        total_signals = signals_query.count()
        pending_signals = signals_query.filter(SignalORM.status == "pending").count()
        executed_signals = signals_query.filter(SignalORM.status == "executed").count()
        failed_signals = signals_query.filter(SignalORM.status == "failed").count()
        skipped_signals = signals_query.filter(SignalORM.status == "skipped").count()
        
        # Get trades stats
        total_trades = trades_query.count()
        
        # Today's trades
        today = date.today()
        today_trades = trades_query.filter(
            Trade.created_at >= today
        ).count()
        
        # Get accounts stats
        total_accounts = accounts_query.count()
        active_accounts = accounts_query.filter(Account.is_active == True).count()
        connected_accounts = accounts_query.filter(Account.is_connected == True).count()
        
        # Get positions stats
        total_positions = positions_query.count()
        open_positions = positions_query.filter(Position.status == "open").count()
        
        # Calculate total balance across accounts
        total_balance = db.query(Account).filter(
            Account.user_id == user_id
        ).with_entities(
            db.query(Account).filter(
                Account.user_id == user_id
            ).subquery().model.total_balance if user_id else 0
        ).scalar_subquery()
        ).scalar() or 0
        
        return {
            # Signal statistics
            "signals": {
                "total": total_signals,
                "pending": pending_signals,
                "executed": executed_signals,
                "failed": failed_signals,
                "skipped": skipped_signals,
            },
            
            # Trade statistics
            "trades": {
                "total": total_trades,
                "today": today_trades,
            },
            
            # Account statistics
            "accounts": {
                "total": total_accounts,
                "active": active_accounts,
                "connected": connected_accounts,
            },
            
            # Position statistics
            "positions": {
                "total": total_positions,
                "open": open_positions,
            },
            
            # Financial statistics
            "financial": {
                "total_balance": float(total_balance),
            },
            
            # Metadata
            "last_updated": datetime.utcnow().isoformat(),
            "filters_applied": {
                "status": status,
                "limit": limit,
            }
        }
        
    except Exception as e:
        # Log the error but don't expose details
        print(f"Dashboard stats error: {e}")
        # Return empty stats on error to prevent frontend breaking
        return {
            "signals": {"total": 0, "pending": 0, "executed": 0, "failed": 0, "skipped": 0},
            "trades": {"total": 0, "today": 0},
            "accounts": {"total": 0, "active": 0, "connected": 0},
            "positions": {"total": 0, "open": 0},
            "financial": {"total_balance": 0.0},
            "last_updated": datetime.utcnow().isoformat(),
            "filters_applied": {"status": status, "limit": limit},
        }