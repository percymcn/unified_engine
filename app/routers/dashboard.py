"""
Dashboard Router for Tradeflow
Provides endpoints for dashboard widgets: executions, equity history, positions
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel
import logging

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, ExecutionLog, Position
from app.models.database_models import (
    TradingAccount,
    AccountEquityHistory,
    BrokerType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# --------------------
# Execution Log Models
# --------------------

class ExecutionAccountInfo(BaseModel):
    broker: str
    account_id: Optional[int] = None


class ExecutionItem(BaseModel):
    id: int
    signal_id: Optional[str] = None
    account: ExecutionAccountInfo
    symbol: str
    action: str
    volume: float
    price: Optional[float] = None
    status: str
    execution_time_ms: Optional[int] = None
    created_at: str


class ExecutionsResponse(BaseModel):
    executions: List[ExecutionItem]
    total: int


# --------------------
# Equity History Models
# --------------------

class EquityDataPoint(BaseModel):
    date: str
    equity: float
    balance: float


class EquityResponse(BaseModel):
    data: List[EquityDataPoint]
    current_equity: float
    current_balance: float
    change_percent: Optional[float] = None


# --------------------
# Open Positions Models
# --------------------

class PositionAccountInfo(BaseModel):
    broker: str
    account_name: Optional[str] = None


class PositionItem(BaseModel):
    id: int
    symbol: str
    side: str  # "Long" or "Short"
    volume: float
    unrealized_pnl: float
    account: PositionAccountInfo


class PositionsResponse(BaseModel):
    positions: List[PositionItem]
    total_pnl: float
    total_positions: int


# --------------------
# Endpoints
# --------------------

@router.get("/executions", response_model=ExecutionsResponse)
async def get_recent_executions(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recent execution logs for the current user.
    Returns the most recent trade executions across all accounts.
    """
    # Get user's account IDs
    user_accounts = db.query(TradingAccount.id, TradingAccount.broker).filter(
        TradingAccount.user_id == current_user.id
    ).all()

    account_ids = [a.id for a in user_accounts]
    account_broker_map = {a.id: a.broker.value if a.broker else "unknown" for a in user_accounts}

    if not account_ids:
        return ExecutionsResponse(executions=[], total=0)

    # Query execution logs
    executions = db.query(ExecutionLog).filter(
        ExecutionLog.account_id.in_(account_ids)
    ).order_by(
        desc(ExecutionLog.created_at)
    ).limit(limit).all()

    # Transform to response format
    items = []
    for ex in executions:
        broker_name = account_broker_map.get(ex.account_id, "unknown")
        if ex.broker:
            broker_name = ex.broker.value if hasattr(ex.broker, 'value') else str(ex.broker)

        items.append(ExecutionItem(
            id=ex.id,
            signal_id=ex.signal_id,
            account=ExecutionAccountInfo(
                broker=broker_name,
                account_id=ex.account_id
            ),
            symbol=ex.symbol,
            action=ex.action,
            volume=ex.volume,
            price=ex.price,
            status=ex.status,
            execution_time_ms=ex.execution_time_ms,
            created_at=ex.created_at.isoformat() if ex.created_at else datetime.utcnow().isoformat()
        ))

    return ExecutionsResponse(executions=items, total=len(items))


@router.get("/equity", response_model=EquityResponse)
async def get_equity_history(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get equity history aggregated across all user accounts.
    Returns daily equity snapshots for charting.
    """
    # Get user's account IDs
    user_accounts = db.query(TradingAccount.id, TradingAccount.balance, TradingAccount.equity).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    account_ids = [a.id for a in user_accounts]

    # Calculate current totals
    current_equity = sum(a.equity or 0 for a in user_accounts)
    current_balance = sum(a.balance or 0 for a in user_accounts)

    if not account_ids:
        return EquityResponse(
            data=[],
            current_equity=0,
            current_balance=0,
            change_percent=None
        )

    # Query equity history - aggregate by day
    start_date = datetime.utcnow() - timedelta(days=days)

    # Get equity history records
    history = db.query(
        func.date(AccountEquityHistory.timestamp).label('date'),
        func.sum(AccountEquityHistory.equity).label('total_equity'),
        func.sum(AccountEquityHistory.balance).label('total_balance')
    ).filter(
        AccountEquityHistory.account_id.in_(account_ids),
        AccountEquityHistory.timestamp >= start_date
    ).group_by(
        func.date(AccountEquityHistory.timestamp)
    ).order_by(
        func.date(AccountEquityHistory.timestamp)
    ).all()

    data_points = [
        EquityDataPoint(
            date=str(h.date),
            equity=float(h.total_equity or 0),
            balance=float(h.total_balance or 0)
        )
        for h in history
    ]

    # Calculate change percent if we have history
    change_percent = None
    if data_points and len(data_points) > 0:
        first_equity = data_points[0].equity
        if first_equity > 0:
            change_percent = ((current_equity - first_equity) / first_equity) * 100

    return EquityResponse(
        data=data_points,
        current_equity=current_equity,
        current_balance=current_balance,
        change_percent=round(change_percent, 2) if change_percent is not None else None
    )


@router.get("/positions", response_model=PositionsResponse)
async def get_open_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all open positions across user's accounts.
    Returns active positions with P&L information.
    """
    # Get user's accounts with their info
    user_accounts = db.query(
        TradingAccount.id,
        TradingAccount.broker,
        TradingAccount.account_name
    ).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    account_ids = [a.id for a in user_accounts]
    account_info_map = {
        a.id: {
            "broker": a.broker.value if a.broker else "unknown",
            "account_name": a.account_name
        }
        for a in user_accounts
    }

    if not account_ids:
        return PositionsResponse(positions=[], total_pnl=0, total_positions=0)

    # Query open positions from the Position model (models.py)
    # Note: Position model uses is_active field
    positions = db.query(Position).filter(
        Position.account_id.in_(account_ids),
        Position.is_active == True
    ).all()

    items = []
    total_pnl = 0

    for pos in positions:
        account_info = account_info_map.get(pos.account_id, {"broker": "unknown", "account_name": None})

        # Determine side from type
        side = "Long"
        if pos.type:
            type_str = pos.type.value if hasattr(pos.type, 'value') else str(pos.type)
            if "SELL" in type_str.upper():
                side = "Short"

        pnl = pos.unrealized_pnl or 0
        total_pnl += pnl

        items.append(PositionItem(
            id=pos.id,
            symbol=pos.symbol,
            side=side,
            volume=pos.volume,
            unrealized_pnl=pnl,
            account=PositionAccountInfo(
                broker=account_info["broker"],
                account_name=account_info["account_name"]
            )
        ))

    return PositionsResponse(
        positions=items,
        total_pnl=round(total_pnl, 2),
        total_positions=len(items)
    )
