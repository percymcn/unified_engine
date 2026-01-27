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
import asyncio

from app.db.database import get_db
from app.routers.auth import get_current_user
from app.models.models import User, ExecutionLog, Position
from app.models.database_models import (
    TradingAccount,
    AccountEquityHistory,
    BrokerType,
)
from app.services.signal_processor import _create_account_executor

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
    id: str  # String to preserve large TradeLocker position IDs
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
    Get all open positions across user's accounts from live broker connections.
    Returns active positions with real-time P&L information.
    """
    # Get user's active accounts
    user_accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    if not user_accounts:
        return PositionsResponse(positions=[], total_pnl=0, total_positions=0)

    async def fetch_positions_for_account(account: TradingAccount):
        """Fetch live positions for a single account."""
        positions = []
        try:
            executor, needs_cleanup = await _create_account_executor(account, db)
            if executor:
                try:
                    raw_positions = await executor.get_positions()
                    for pos in raw_positions:
                        side = "Long"
                        pos_side = getattr(pos, 'side', None) or pos.get('side', '') if isinstance(pos, dict) else getattr(pos, 'side', 'buy')
                        if pos_side:
                            side_str = pos_side.lower() if isinstance(pos_side, str) else str(pos_side).lower()
                            if 'sell' in side_str or 'short' in side_str:
                                side = "Short"

                        # Handle both object and dict formats
                        if isinstance(pos, dict):
                            pnl = float(pos.get('unrealized_pnl', 0) or pos.get('unrealizedPnl', 0) or 0)
                            positions.append(PositionItem(
                                id=str(pos.get('id', 0)),  # String to preserve large IDs
                                symbol=pos.get('symbol', ''),
                                side=side,
                                volume=float(pos.get('size', 0) or pos.get('qty', 0) or 0),
                                unrealized_pnl=pnl,
                                account=PositionAccountInfo(
                                    broker=account.broker.value if account.broker else "unknown",
                                    account_name=account.account_name
                                )
                            ))
                        else:
                            pnl = float(getattr(pos, 'unrealized_pnl', 0) or 0)
                            positions.append(PositionItem(
                                id=str(getattr(pos, 'id', 0)),  # String to preserve large IDs
                                symbol=getattr(pos, 'symbol', ''),
                                side=side,
                                volume=float(getattr(pos, 'size', 0) or 0),
                                unrealized_pnl=pnl,
                                account=PositionAccountInfo(
                                    broker=account.broker.value if account.broker else "unknown",
                                    account_name=account.account_name
                                )
                            ))
                finally:
                    if needs_cleanup and executor:
                        try:
                            await executor.disconnect()
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Failed to fetch positions for account {account.id}: {e}")
        return positions

    # Fetch positions from all accounts concurrently
    tasks = [fetch_positions_for_account(account) for account in user_accounts]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    items = []
    total_pnl = 0

    for result in results:
        if isinstance(result, list):
            for pos in result:
                items.append(pos)
                total_pnl += pos.unrealized_pnl

    return PositionsResponse(
        positions=items,
        total_pnl=round(total_pnl, 2),
        total_positions=len(items)
    )


# --------------------
# Live Account Summary Models
# --------------------

class AccountSummaryItem(BaseModel):
    account_id: int
    account_name: Optional[str] = None
    broker: str
    balance: float
    equity: float
    margin_used: float = 0
    margin_available: float = 0
    unrealized_pnl: float = 0
    positions_count: int = 0


class AccountsSummaryResponse(BaseModel):
    accounts: List[AccountSummaryItem]
    total_balance: float
    total_equity: float
    total_unrealized_pnl: float


@router.get("/accounts/live", response_model=AccountsSummaryResponse)
async def get_live_accounts_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get live account summary with real-time balance and equity from brokers.
    Fetches directly from connected broker accounts.
    """
    # Get user's active accounts
    user_accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()

    if not user_accounts:
        return AccountsSummaryResponse(
            accounts=[],
            total_balance=0,
            total_equity=0,
            total_unrealized_pnl=0
        )

    async def fetch_account_summary(account: TradingAccount) -> Optional[AccountSummaryItem]:
        """Fetch live summary for a single account."""
        try:
            executor, needs_cleanup = await _create_account_executor(account, db)
            if executor:
                try:
                    # Get broker account ID (required for most executors)
                    broker_account_id = account.default_broker_account_id or account.account_number or str(account.id)

                    # Get account info - pass account_id if required
                    try:
                        account_info = await executor.get_account_info(broker_account_id)
                    except TypeError:
                        # Fallback for executors that don't require account_id
                        account_info = await executor.get_account_info()

                    positions = await executor.get_positions()

                    balance = 0
                    equity = 0
                    margin_used = 0
                    margin_available = 0
                    unrealized_pnl = 0

                    if isinstance(account_info, dict):
                        balance = float(account_info.get('balance', 0) or 0)
                        equity = float(account_info.get('equity', 0) or account_info.get('accountEquity', 0) or 0)
                        margin_used = float(account_info.get('margin_used', 0) or account_info.get('usedMargin', 0) or 0)
                        margin_available = float(account_info.get('margin_available', 0) or account_info.get('freeMargin', 0) or 0)
                        unrealized_pnl = float(account_info.get('unrealized_pnl', 0) or 0)
                    else:
                        balance = float(getattr(account_info, 'balance', 0) or 0)
                        equity = float(getattr(account_info, 'equity', 0) or getattr(account_info, 'accountEquity', 0) or 0)
                        margin_used = float(getattr(account_info, 'margin_used', 0) or getattr(account_info, 'usedMargin', 0) or 0)
                        margin_available = float(getattr(account_info, 'margin_available', 0) or getattr(account_info, 'freeMargin', 0) or 0)
                        unrealized_pnl = float(getattr(account_info, 'unrealized_pnl', 0) or 0)

                    # Calculate unrealized PnL from positions if not in account info
                    if unrealized_pnl == 0 and positions:
                        for pos in positions:
                            if isinstance(pos, dict):
                                unrealized_pnl += float(pos.get('unrealized_pnl', 0) or pos.get('unrealizedPnl', 0) or 0)
                            else:
                                unrealized_pnl += float(getattr(pos, 'unrealized_pnl', 0) or 0)

                    return AccountSummaryItem(
                        account_id=account.id,
                        account_name=account.account_name,
                        broker=account.broker.value if account.broker else "unknown",
                        balance=balance,
                        equity=equity,
                        margin_used=margin_used,
                        margin_available=margin_available,
                        unrealized_pnl=unrealized_pnl,
                        positions_count=len(positions) if positions else 0
                    )
                finally:
                    if needs_cleanup and executor:
                        try:
                            await executor.disconnect()
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Failed to fetch summary for account {account.id}: {e}")
            # Return cached data from DB as fallback
            return AccountSummaryItem(
                account_id=account.id,
                account_name=account.account_name,
                broker=account.broker.value if account.broker else "unknown",
                balance=float(account.balance or 0),
                equity=float(account.equity or 0),
                margin_used=0,
                margin_available=0,
                unrealized_pnl=0,
                positions_count=0
            )
        return None

    # Fetch summaries from all accounts concurrently
    tasks = [fetch_account_summary(account) for account in user_accounts]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    accounts = []
    total_balance = 0
    total_equity = 0
    total_unrealized_pnl = 0

    for result in results:
        if isinstance(result, AccountSummaryItem):
            accounts.append(result)
            total_balance += result.balance
            total_equity += result.equity
            total_unrealized_pnl += result.unrealized_pnl

    return AccountsSummaryResponse(
        accounts=accounts,
        total_balance=round(total_balance, 2),
        total_equity=round(total_equity, 2),
        total_unrealized_pnl=round(total_unrealized_pnl, 2)
    )
