from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, date

from app.db.database import get_db
from app.models.models import Signal as SignalORM, Trade, Position, ExecutionLog
from app.models.database_models import TradingAccount
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
        accounts_query = db.query(TradingAccount)
        executions_query = db.query(ExecutionLog)

        # Filter by user if authenticated
        if user_id:
            signals_query = signals_query.filter(SignalORM.user_id == user_id)
            accounts_query = accounts_query.filter(TradingAccount.user_id == user_id)
            # Get account IDs for execution log filtering
            account_ids = [a.id for a in accounts_query.all()]
            executions_query = executions_query.filter(ExecutionLog.account_id.in_(account_ids)) if account_ids else executions_query.filter(False)

        # Filter by status if provided
        if status:
            signals_query = signals_query.filter(SignalORM.status == status)

        # Get signals stats
        total_signals = signals_query.count()
        pending_signals = db.query(SignalORM).filter(SignalORM.user_id == user_id, SignalORM.status == "pending").count() if user_id else 0
        executed_signals = db.query(SignalORM).filter(SignalORM.user_id == user_id, SignalORM.status == "executed").count() if user_id else 0
        failed_signals = db.query(SignalORM).filter(SignalORM.user_id == user_id, SignalORM.status == "failed").count() if user_id else 0
        skipped_signals = db.query(SignalORM).filter(SignalORM.user_id == user_id, SignalORM.status == "skipped").count() if user_id else 0

        # Get execution stats (today's trades)
        today = date.today()
        today_trades = executions_query.filter(
            ExecutionLog.created_at >= today
        ).count() if user_id else 0

        # Get accounts stats
        total_accounts = accounts_query.count()
        active_accounts = accounts_query.filter(TradingAccount.is_active == True).count()
        connected_accounts = active_accounts  # For TradingAccount, active = connected

        # Get positions count from accounts (sum from synced data)
        total_positions = accounts_query.with_entities(func.sum(TradingAccount.positions_count)).scalar() or 0
        open_positions = total_positions  # Synced positions are open positions

        # Calculate total balance across accounts
        total_balance_result = db.query(func.sum(TradingAccount.balance)).filter(
            TradingAccount.user_id == user_id
        ).scalar() if user_id else 0
        total_balance = float(total_balance_result or 0)
        
        # Total executions (all time)
        total_executions = executions_query.count() if user_id else 0

        # Return in both flat format (for dashboard widgets) and nested (for detail views)
        return {
            # Flat format for dashboard widgets
            "activeSignals": pending_signals,  # "Active" means pending/waiting to be processed
            "connectedBrokers": connected_accounts,
            "todaysTrades": today_trades,
            "totalBalance": float(total_balance),

            # Nested format for detailed stats (backward compat)
            "signals": {
                "total": total_signals,
                "pending": pending_signals,
                "executed": executed_signals,
                "failed": failed_signals,
                "skipped": skipped_signals,
            },
            "trades": {
                "total": total_executions,
                "today": today_trades,
            },
            "accounts": {
                "total": total_accounts,
                "active": active_accounts,
                "connected": connected_accounts,
            },
            "positions": {
                "total": int(total_positions),
                "open": int(open_positions),
            },
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