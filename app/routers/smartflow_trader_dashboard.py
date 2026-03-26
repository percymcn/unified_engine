"""
SmartFlow Trader Dashboard API Router
=====================================

Endpoints:
- GET /api/v1/smartflow/trader/status
- GET /api/v1/smartflow/trader/trades
- GET /api/v1/smartflow/trader/performance
- GET /api/v1/smartflow/trader/signals
- POST /api/v1/smartflow/trader/toggle
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import User
from app.models.smartflow_models import SmartFlowConfig, SmartFlowSignalLog, SmartFlowTrade
from app.routers.auth import get_current_user
from app.services.smartflow_trader import get_smartflow_trader
from app.services.trade_journal import TradeJournal

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class SmartFlowTraderPosition(BaseModel):
    trade_id: Optional[int]
    symbol: str
    direction: str
    quantity: float
    entry_price: Optional[float]
    entry_time: datetime
    status: str
    pnl: Optional[float]
    strategy: Optional[str]
    notes: Optional[str]


class GuardrailStatus(BaseModel):
    halted: bool
    halt_reason: str
    daily_pnl: float
    total_realized_pnl: float
    open_positions: int
    max_open_positions: int
    max_daily_loss: float
    max_position_size: float
    max_drawdown_pct: float
    current_drawdown_pct: float
    starting_equity: float


class SmartFlowTraderStatusResponse(BaseModel):
    running: bool
    paused: bool
    paper_mode: bool
    todays_pnl: float
    positions: List[SmartFlowTraderPosition]
    guardrails: GuardrailStatus


class SmartFlowTradeResponse(BaseModel):
    id: int
    user_id: Optional[int]
    symbol: str
    direction: str
    entry_price: Optional[float]
    exit_price: Optional[float]
    quantity: float
    entry_time: datetime
    exit_time: Optional[datetime]
    pnl: Optional[float]
    strategy: Optional[str]
    status: str
    notes: Optional[str]

    class Config:
        from_attributes = True


class SmartFlowTradesPage(BaseModel):
    trades: List[SmartFlowTradeResponse]
    total: int
    skip: int
    limit: int


class SmartFlowPerformanceResponse(BaseModel):
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    total_trades: int
    trade_count_today: int


class SmartFlowSignalResponse(BaseModel):
    id: int
    ticker: str
    action: str
    score: float
    price: Optional[float]
    bullish_flows: int
    bearish_flows: int
    total_premium: float
    confidence: Optional[float]
    reason: Optional[str]
    engine_type: Optional[str]
    post_successful: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SmartFlowToggleResponse(BaseModel):
    success: bool
    paper_mode: bool


# ============================================================================
# Helpers
# ============================================================================

def _get_today_start() -> datetime:
    now = datetime.utcnow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _build_guardrail_status(trader) -> GuardrailStatus:
    manager = trader.risk_manager
    current_equity = manager.config.starting_equity + manager.total_realized_pnl
    peak = manager.peak_equity if manager.peak_equity > 0 else manager.config.starting_equity
    drawdown_pct = 0.0
    if peak > 0:
        drawdown_pct = max(0.0, ((peak - current_equity) / peak) * 100)

    return GuardrailStatus(
        halted=manager.halted,
        halt_reason=manager.halt_reason or "",
        daily_pnl=manager.daily_pnl,
        total_realized_pnl=manager.total_realized_pnl,
        open_positions=len(manager.open_positions),
        max_open_positions=manager.config.max_open_positions,
        max_daily_loss=manager.config.max_daily_loss,
        max_position_size=manager.config.max_position_size,
        max_drawdown_pct=manager.config.max_drawdown_pct,
        current_drawdown_pct=drawdown_pct,
        starting_equity=manager.config.starting_equity,
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/status", response_model=SmartFlowTraderStatusResponse)
async def get_trader_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return SmartFlow trader status with live positions and guardrails."""
    trader = get_smartflow_trader()

    start_of_day = _get_today_start()
    todays_pnl = db.query(func.coalesce(func.sum(SmartFlowTrade.pnl), 0.0)).filter(
        SmartFlowTrade.user_id == current_user.id,
        SmartFlowTrade.exit_time.isnot(None),
        SmartFlowTrade.exit_time >= start_of_day,
        SmartFlowTrade.status.in_(["closed", "paper_closed"]),
    ).scalar() or 0.0

    positions: List[SmartFlowTraderPosition] = []
    if trader.config.user_id is None or trader.config.user_id == current_user.id:
        positions = [
            SmartFlowTraderPosition(
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                direction=trade.direction,
                quantity=trade.quantity,
                entry_price=trade.entry_price,
                entry_time=trade.entry_time,
                status=trade.status,
                pnl=trade.pnl,
                strategy=trade.strategy,
                notes=trade.notes,
            )
            for trade in trader.open_trades.values()
        ]

    return SmartFlowTraderStatusResponse(
        running=bool(getattr(trader.signal_engine, "enabled", True)),
        paused=trader.risk_manager.halted,
        paper_mode=trader.config.paper_trading,
        todays_pnl=todays_pnl,
        positions=positions,
        guardrails=_build_guardrail_status(trader),
    )


@router.get("/trades", response_model=SmartFlowTradesPage)
async def get_recent_trades(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated SmartFlow trade journal entries."""
    base_query = db.query(SmartFlowTrade).filter(SmartFlowTrade.user_id == current_user.id)
    total = base_query.count()
    trades = (
        base_query.order_by(SmartFlowTrade.entry_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return SmartFlowTradesPage(trades=trades, total=total, skip=skip, limit=limit)


@router.get("/performance", response_model=SmartFlowPerformanceResponse)
async def get_performance_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return aggregated SmartFlow trade performance metrics."""
    journal = TradeJournal()
    metrics = journal.get_performance(user_id=current_user.id)

    start_of_day = _get_today_start()
    trade_count_today = db.query(func.count(SmartFlowTrade.id)).filter(
        SmartFlowTrade.user_id == current_user.id,
        SmartFlowTrade.entry_time >= start_of_day,
    ).scalar() or 0

    return SmartFlowPerformanceResponse(
        win_rate=metrics.win_rate,
        total_pnl=metrics.total_pnl,
        avg_win=metrics.average_win,
        avg_loss=metrics.average_loss,
        profit_factor=metrics.profit_factor,
        max_drawdown=metrics.max_drawdown,
        total_trades=metrics.total_trades,
        trade_count_today=trade_count_today,
    )


@router.get("/signals", response_model=List[SmartFlowSignalResponse])
async def get_recent_signals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the most recent SmartFlow signals for the user."""
    signals = (
        db.query(SmartFlowSignalLog)
        .join(SmartFlowConfig, SmartFlowSignalLog.config_id == SmartFlowConfig.id)
        .filter(SmartFlowConfig.user_id == current_user.id)
        .order_by(SmartFlowSignalLog.created_at.desc())
        .limit(20)
        .all()
    )
    return signals


@router.post("/toggle", response_model=SmartFlowToggleResponse)
async def toggle_paper_mode(
    current_user: User = Depends(get_current_user),
):
    """Toggle SmartFlow Trader between paper and live modes."""
    trader = get_smartflow_trader()
    trader.config.paper_trading = not trader.config.paper_trading
    logger.info(
        "SmartFlow Trader mode toggled by user %s (paper_mode=%s)",
        current_user.id,
        trader.config.paper_trading,
    )
    return SmartFlowToggleResponse(success=True, paper_mode=trader.config.paper_trading)
