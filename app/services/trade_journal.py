"""
SmartFlow Trade Journal
=======================

Logs SmartFlow trades and computes performance statistics.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.smartflow_models import SmartFlowTrade

logger = logging.getLogger(__name__)


@dataclass
class TradePerformance:
    """Aggregated performance metrics for SmartFlow trades."""
    total_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0


class TradeJournal:
    """Trade journal for SmartFlow executions."""

    def __init__(self, session_factory=SessionLocal):
        self._session_factory = session_factory

    def log_entry(
        self,
        user_id: Optional[int],
        symbol: str,
        direction: str,
        quantity: float,
        entry_price: Optional[float],
        strategy: Optional[str] = None,
        status: str = "open",
        notes: Optional[str] = None,
        entry_time: Optional[datetime] = None,
    ) -> Optional[int]:
        """Log a new trade entry and return the trade ID."""
        entry_time = entry_time or datetime.utcnow()
        db: Optional[Session] = None
        try:
            db = self._session_factory()
            trade = SmartFlowTrade(
                user_id=user_id,
                symbol=symbol,
                direction=direction,
                quantity=quantity,
                entry_price=entry_price,
                entry_time=entry_time,
                strategy=strategy,
                status=status,
                notes=notes,
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)
            return trade.id
        except Exception as exc:
            logger.error(f"Failed to log trade entry: {exc}")
            if db:
                db.rollback()
            return None
        finally:
            if db:
                db.close()

    def close_trade(
        self,
        trade_id: int,
        exit_price: Optional[float],
        exit_time: Optional[datetime] = None,
        pnl: Optional[float] = None,
        status: str = "closed",
        notes: Optional[str] = None,
    ) -> bool:
        """Close a trade and update P&L."""
        exit_time = exit_time or datetime.utcnow()
        db: Optional[Session] = None
        try:
            db = self._session_factory()
            trade = db.query(SmartFlowTrade).filter(SmartFlowTrade.id == trade_id).first()
            if not trade:
                return False

            if pnl is None and trade.entry_price is not None and exit_price is not None:
                if trade.direction == "buy":
                    pnl = (exit_price - trade.entry_price) * trade.quantity
                elif trade.direction == "sell":
                    pnl = (trade.entry_price - exit_price) * trade.quantity

            trade.exit_price = exit_price
            trade.exit_time = exit_time
            trade.pnl = pnl
            trade.status = status
            if notes:
                trade.notes = notes

            db.commit()
            return True
        except Exception as exc:
            logger.error(f"Failed to close trade {trade_id}: {exc}")
            if db:
                db.rollback()
            return False
        finally:
            if db:
                db.close()

    def fetch_trades(self, user_id: Optional[int] = None) -> List[SmartFlowTrade]:
        """Fetch SmartFlow trades for a user (or all trades)."""
        db = self._session_factory()
        try:
            query = db.query(SmartFlowTrade)
            if user_id is not None:
                query = query.filter(SmartFlowTrade.user_id == user_id)
            return query.order_by(SmartFlowTrade.entry_time.asc()).all()
        finally:
            db.close()

    def get_performance(self, user_id: Optional[int] = None) -> TradePerformance:
        """Compute performance metrics from closed trades."""
        trades = self.fetch_trades(user_id=user_id)
        closed_statuses = {"closed", "paper_closed"}
        closed = [
            trade for trade in trades
            if trade.status in closed_statuses and trade.pnl is not None
        ]

        if not closed:
            return TradePerformance()

        total_pnl = sum(trade.pnl for trade in closed)
        wins = [trade.pnl for trade in closed if trade.pnl > 0]
        losses = [trade.pnl for trade in closed if trade.pnl < 0]

        win_rate = (len(wins) / len(closed)) * 100 if closed else 0.0
        average_win = sum(wins) / len(wins) if wins else 0.0
        average_loss = abs(sum(losses) / len(losses)) if losses else 0.0
        profit_factor = (sum(wins) / abs(sum(losses))) if losses else 0.0

        equity_curve = []
        running_total = 0.0
        for trade in closed:
            running_total += trade.pnl
            equity_curve.append(running_total)

        peak = 0.0
        max_drawdown = 0.0
        for value in equity_curve:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        return TradePerformance(
            total_trades=len(closed),
            win_rate=win_rate,
            total_pnl=total_pnl,
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
        )
