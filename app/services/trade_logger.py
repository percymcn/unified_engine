"""
Trade Logger & Forward Testing Module
======================================

Mandatory trade journaling for forward-testing the system.
Logs every signal (accepted + rejected) with full context.
Tracks 30min and 60min outcomes for performance analysis.

Database table: trade_journal
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine
from app.services.indicators import MultiTimeframeSignal

logger = logging.getLogger(__name__)

# All timestamps in EST
EST = ZoneInfo('America/New_York')

def now_est() -> datetime:
    """Get current time in EST (without tzinfo for DB storage)"""
    return datetime.now(EST).replace(tzinfo=None)


class TradeStatus(str, Enum):
    PENDING = "pending"      # Signal generated, waiting for outcomes
    TRACKING = "tracking"    # Actively tracking price for exit
    COMPLETED = "completed"  # 60min passed, all outcomes filled
    EXPIRED = "expired"      # Trade too old, stopped tracking


class SignalJournal(Base):
    """
    Signal journal entry for forward testing.

    Records every signal (accepted AND rejected) with full context and tracks outcomes.
    Separate from trade_journal which holds broker executions.
    """
    __tablename__ = "signal_journal"

    id = Column(Integer, primary_key=True, index=True)

    # Signal identification
    ticker = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # 'buy', 'sell', 'rejected'
    signal_accepted = Column(Boolean, nullable=False, default=True)
    rejection_reason = Column(Text, nullable=True)

    # Signal quality metrics
    confidence = Column(Float, nullable=False)
    aligned_tfs = Column(Integer, nullable=False)
    overall_bias = Column(String(20), nullable=True)

    # Entry information
    entry_price = Column(Float, nullable=True)
    entry_timestamp = Column(DateTime, nullable=False, index=True)

    # Planned risk parameters
    planned_stop = Column(Float, nullable=True)
    planned_target = Column(Float, nullable=True)
    planned_rr = Column(Float, nullable=True)
    atr_at_entry = Column(Float, nullable=True)

    # Outcome tracking (filled async after time passes)
    price_30min = Column(Float, nullable=True)
    pnl_30min = Column(Float, nullable=True)
    pnl_30min_pct = Column(Float, nullable=True)

    price_60min = Column(Float, nullable=True)
    pnl_60min = Column(Float, nullable=True)
    pnl_60min_pct = Column(Float, nullable=True)

    # Risk tracking
    stop_hit = Column(Boolean, nullable=True, default=False)
    target_hit = Column(Boolean, nullable=True, default=False)
    max_favorable = Column(Float, nullable=True)  # Max favorable excursion
    max_adverse = Column(Float, nullable=True)    # Max adverse excursion

    # Status
    status = Column(String(20), nullable=False, default='pending')

    # Full context (JSON blob for detailed analysis)
    signal_context = Column(JSON, nullable=True)

    # Metadata (stored in EST)
    created_at = Column(DateTime, default=now_est, nullable=False)
    updated_at = Column(DateTime, default=now_est, onupdate=now_est)


@dataclass
class TradeStats:
    """Computed statistics from trade journal"""
    total_trades: int = 0
    accepted_trades: int = 0
    rejected_trades: int = 0

    # Win/Loss (based on 30min outcome)
    winners_30min: int = 0
    losers_30min: int = 0
    win_rate_30min: float = 0.0

    # Win/Loss (based on 60min outcome)
    winners_60min: int = 0
    losers_60min: int = 0
    win_rate_60min: float = 0.0

    # P&L metrics (30min)
    total_pnl_30min: float = 0.0
    avg_win_30min: float = 0.0
    avg_loss_30min: float = 0.0
    profit_factor_30min: float = 0.0
    expectancy_30min: float = 0.0

    # P&L metrics (60min)
    total_pnl_60min: float = 0.0
    avg_win_60min: float = 0.0
    avg_loss_60min: float = 0.0
    profit_factor_60min: float = 0.0
    expectancy_60min: float = 0.0

    # Risk metrics
    stop_hit_rate: float = 0.0
    target_hit_rate: float = 0.0
    avg_rr_achieved: float = 0.0

    # By direction
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0

    # Confidence analysis
    high_conf_win_rate: float = 0.0  # Trades with conf >= 80
    low_conf_win_rate: float = 0.0   # Trades with conf < 80

    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


class TradeLogger:
    """
    Trade journaling and forward-testing system.

    Records all signals, tracks outcomes, computes statistics.
    """

    def __init__(self):
        self._ensure_table_exists()
        logger.info("TradeLogger initialized")

    def _ensure_table_exists(self):
        """Create trade_journal table if it doesn't exist"""
        try:
            SignalJournal.__table__.create(engine, checkfirst=True)
            logger.info("trade_journal table ready")
        except Exception as e:
            logger.error(f"Failed to create trade_journal table: {e}")

    def log_signal(
        self,
        signal: MultiTimeframeSignal,
        entry_price: Optional[float] = None
    ) -> Optional[int]:
        """
        Log a signal (accepted or rejected) to the journal.

        Args:
            signal: MultiTimeframeSignal from indicator engine
            entry_price: Actual entry price (if different from signal.entry_price)

        Returns:
            Journal entry ID or None on failure
        """
        try:
            db = SessionLocal()
            try:
                # Build context JSON
                context = {
                    'tf_analyses': {},
                    'config': {
                        'min_aligned_tfs': signal.min_aligned_tfs,
                        'min_confidence': signal.min_confidence,
                        'min_rr': signal.min_rr
                    }
                }

                for tf_name in ['5m', '15m', '30m', '1h', '4h']:
                    tf_analysis = getattr(signal, f'tf_{tf_name.replace("m", "m").replace("h", "h")}', None)
                    if tf_name == '5m':
                        tf_analysis = signal.tf_5m
                    elif tf_name == '15m':
                        tf_analysis = signal.tf_15m
                    elif tf_name == '30m':
                        tf_analysis = signal.tf_30m
                    elif tf_name == '1h':
                        tf_analysis = signal.tf_1h
                    elif tf_name == '4h':
                        tf_analysis = signal.tf_4h

                    if tf_analysis:
                        context['tf_analyses'][tf_name] = {
                            'bias': tf_analysis.bias,
                            'close': tf_analysis.close,
                            'ema9': tf_analysis.ema9,
                            'ema21': tf_analysis.ema21,
                            'rsi14': tf_analysis.rsi14,
                            'macd_hist': tf_analysis.macd_histogram,
                            'atr14': tf_analysis.atr14
                        }

                entry = SignalJournal(
                    ticker=signal.ticker,
                    direction=signal.action if signal.should_trade else 'rejected',
                    signal_accepted=signal.should_trade,
                    rejection_reason=signal.rejection_reason if not signal.should_trade else None,

                    confidence=signal.confidence_score,
                    aligned_tfs=max(signal.aligned_bullish, signal.aligned_bearish),
                    overall_bias=signal.overall_bias,

                    entry_price=entry_price or signal.entry_price,
                    entry_timestamp=signal.timestamp,

                    planned_stop=signal.stop_loss,
                    planned_target=signal.take_profit,
                    planned_rr=signal.risk_reward_ratio,
                    atr_at_entry=signal.atr_for_stops,

                    status=TradeStatus.PENDING.value if signal.should_trade else TradeStatus.COMPLETED.value,
                    signal_context=context
                )

                db.add(entry)
                db.commit()
                db.refresh(entry)

                log_type = "✅ ACCEPTED" if signal.should_trade else "❌ REJECTED"
                logger.info(f"📝 {log_type}: {signal.ticker} {signal.action} "
                           f"conf={signal.confidence_score:.1f}% aligned={max(signal.aligned_bullish, signal.aligned_bearish)} "
                           f"(journal_id={entry.id})")

                return entry.id

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to log signal: {e}")
            return None

    def update_outcome(
        self,
        journal_id: int,
        current_price: float,
        minutes_elapsed: int
    ) -> bool:
        """
        Update trade outcome with current price.

        Args:
            journal_id: Trade journal entry ID
            current_price: Current market price
            minutes_elapsed: Minutes since entry

        Returns:
            True if update successful
        """
        try:
            db = SessionLocal()
            try:
                entry = db.query(SignalJournal).filter(SignalJournal.id == journal_id).first()
                if not entry:
                    return False

                if not entry.entry_price:
                    return False

                # Calculate P&L
                if entry.direction == 'buy':
                    pnl = current_price - entry.entry_price
                elif entry.direction == 'sell':
                    pnl = entry.entry_price - current_price
                else:
                    return False

                pnl_pct = (pnl / entry.entry_price) * 100 if entry.entry_price else 0

                # Update appropriate field based on time elapsed
                if minutes_elapsed >= 30 and entry.price_30min is None:
                    entry.price_30min = current_price
                    entry.pnl_30min = pnl
                    entry.pnl_30min_pct = pnl_pct
                    entry.status = TradeStatus.TRACKING.value

                if minutes_elapsed >= 60 and entry.price_60min is None:
                    entry.price_60min = current_price
                    entry.pnl_60min = pnl
                    entry.pnl_60min_pct = pnl_pct
                    entry.status = TradeStatus.COMPLETED.value

                # Check stop/target hit
                if entry.planned_stop and entry.planned_target:
                    if entry.direction == 'buy':
                        if current_price <= entry.planned_stop:
                            entry.stop_hit = True
                        if current_price >= entry.planned_target:
                            entry.target_hit = True
                    else:  # sell
                        if current_price >= entry.planned_stop:
                            entry.stop_hit = True
                        if current_price <= entry.planned_target:
                            entry.target_hit = True

                # Track max excursions
                if entry.direction == 'buy':
                    if entry.max_favorable is None or pnl > entry.max_favorable:
                        entry.max_favorable = pnl
                    if entry.max_adverse is None or pnl < entry.max_adverse:
                        entry.max_adverse = pnl
                else:
                    if entry.max_favorable is None or pnl > entry.max_favorable:
                        entry.max_favorable = pnl
                    if entry.max_adverse is None or pnl < entry.max_adverse:
                        entry.max_adverse = pnl

                db.commit()
                return True

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to update outcome for journal_id={journal_id}: {e}")
            return False

    def get_pending_trades(self, max_age_minutes: int = 120) -> List[SignalJournal]:
        """Get trades that need outcome updates."""
        try:
            db = SessionLocal()
            try:
                cutoff = now_est() - timedelta(minutes=max_age_minutes)

                pending = db.query(SignalJournal).filter(
                    SignalJournal.signal_accepted == True,
                    SignalJournal.status.in_([TradeStatus.PENDING.value, TradeStatus.TRACKING.value]),
                    SignalJournal.entry_timestamp >= cutoff
                ).all()

                return pending

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to get pending trades: {e}")
            return []

    def compute_stats(
        self,
        ticker: Optional[str] = None,
        days_back: int = 7
    ) -> TradeStats:
        """
        Compute comprehensive trading statistics.

        Args:
            ticker: Filter by ticker (None for all)
            days_back: Number of days to analyze

        Returns:
            TradeStats with all computed metrics
        """
        stats = TradeStats()

        try:
            db = SessionLocal()
            try:
                cutoff = now_est() - timedelta(days=days_back)

                query = db.query(SignalJournal).filter(
                    SignalJournal.entry_timestamp >= cutoff
                )

                if ticker:
                    query = query.filter(SignalJournal.ticker == ticker)

                trades = query.all()

                if not trades:
                    return stats

                stats.total_trades = len(trades)
                stats.period_start = cutoff
                stats.period_end = now_est()

                accepted = [t for t in trades if t.signal_accepted]
                rejected = [t for t in trades if not t.signal_accepted]

                stats.accepted_trades = len(accepted)
                stats.rejected_trades = len(rejected)

                # Filter trades with outcomes
                trades_30 = [t for t in accepted if t.pnl_30min is not None]
                trades_60 = [t for t in accepted if t.pnl_60min is not None]

                # 30-min stats
                if trades_30:
                    winners_30 = [t for t in trades_30 if t.pnl_30min > 0]
                    losers_30 = [t for t in trades_30 if t.pnl_30min <= 0]

                    stats.winners_30min = len(winners_30)
                    stats.losers_30min = len(losers_30)
                    stats.win_rate_30min = len(winners_30) / len(trades_30) * 100

                    stats.total_pnl_30min = sum(t.pnl_30min for t in trades_30)

                    if winners_30:
                        stats.avg_win_30min = sum(t.pnl_30min for t in winners_30) / len(winners_30)
                    if losers_30:
                        stats.avg_loss_30min = abs(sum(t.pnl_30min for t in losers_30) / len(losers_30))

                    gross_profit_30 = sum(t.pnl_30min for t in winners_30) if winners_30 else 0
                    gross_loss_30 = abs(sum(t.pnl_30min for t in losers_30)) if losers_30 else 0

                    if gross_loss_30 > 0:
                        stats.profit_factor_30min = gross_profit_30 / gross_loss_30

                    stats.expectancy_30min = stats.total_pnl_30min / len(trades_30)

                # 60-min stats
                if trades_60:
                    winners_60 = [t for t in trades_60 if t.pnl_60min > 0]
                    losers_60 = [t for t in trades_60 if t.pnl_60min <= 0]

                    stats.winners_60min = len(winners_60)
                    stats.losers_60min = len(losers_60)
                    stats.win_rate_60min = len(winners_60) / len(trades_60) * 100

                    stats.total_pnl_60min = sum(t.pnl_60min for t in trades_60)

                    if winners_60:
                        stats.avg_win_60min = sum(t.pnl_60min for t in winners_60) / len(winners_60)
                    if losers_60:
                        stats.avg_loss_60min = abs(sum(t.pnl_60min for t in losers_60) / len(losers_60))

                    gross_profit_60 = sum(t.pnl_60min for t in winners_60) if winners_60 else 0
                    gross_loss_60 = abs(sum(t.pnl_60min for t in losers_60)) if losers_60 else 0

                    if gross_loss_60 > 0:
                        stats.profit_factor_60min = gross_profit_60 / gross_loss_60

                    stats.expectancy_60min = stats.total_pnl_60min / len(trades_60)

                # Risk metrics
                trades_with_stops = [t for t in accepted if t.stop_hit is not None]
                if trades_with_stops:
                    stats.stop_hit_rate = len([t for t in trades_with_stops if t.stop_hit]) / len(trades_with_stops) * 100
                    stats.target_hit_rate = len([t for t in trades_with_stops if t.target_hit]) / len(trades_with_stops) * 100

                # Direction analysis
                longs = [t for t in trades_30 if t.direction == 'buy']
                shorts = [t for t in trades_30 if t.direction == 'sell']

                if longs:
                    stats.long_win_rate = len([t for t in longs if t.pnl_30min > 0]) / len(longs) * 100
                if shorts:
                    stats.short_win_rate = len([t for t in shorts if t.pnl_30min > 0]) / len(shorts) * 100

                # Confidence analysis
                high_conf = [t for t in trades_30 if t.confidence >= 80]
                low_conf = [t for t in trades_30 if t.confidence < 80]

                if high_conf:
                    stats.high_conf_win_rate = len([t for t in high_conf if t.pnl_30min > 0]) / len(high_conf) * 100
                if low_conf:
                    stats.low_conf_win_rate = len([t for t in low_conf if t.pnl_30min > 0]) / len(low_conf) * 100

                return stats

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Failed to compute stats: {e}")
            return stats

    def print_stats(self, stats: TradeStats):
        """Print formatted statistics to log."""
        logger.info("=" * 60)
        logger.info("📊 TRADE JOURNAL STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Period: {stats.period_start} to {stats.period_end}")
        logger.info(f"Total Signals: {stats.total_trades} (Accepted: {stats.accepted_trades}, Rejected: {stats.rejected_trades})")
        logger.info("-" * 40)
        logger.info("30-MINUTE OUTCOMES:")
        logger.info(f"  Win Rate: {stats.win_rate_30min:.1f}% ({stats.winners_30min}W/{stats.losers_30min}L)")
        logger.info(f"  Avg Win: {stats.avg_win_30min:.2f} | Avg Loss: {stats.avg_loss_30min:.2f}")
        logger.info(f"  Profit Factor: {stats.profit_factor_30min:.2f}")
        logger.info(f"  Expectancy: {stats.expectancy_30min:.2f}")
        logger.info(f"  Total P&L: {stats.total_pnl_30min:.2f}")
        logger.info("-" * 40)
        logger.info("60-MINUTE OUTCOMES:")
        logger.info(f"  Win Rate: {stats.win_rate_60min:.1f}% ({stats.winners_60min}W/{stats.losers_60min}L)")
        logger.info(f"  Avg Win: {stats.avg_win_60min:.2f} | Avg Loss: {stats.avg_loss_60min:.2f}")
        logger.info(f"  Profit Factor: {stats.profit_factor_60min:.2f}")
        logger.info(f"  Expectancy: {stats.expectancy_60min:.2f}")
        logger.info(f"  Total P&L: {stats.total_pnl_60min:.2f}")
        logger.info("-" * 40)
        logger.info("RISK ANALYSIS:")
        logger.info(f"  Stop Hit Rate: {stats.stop_hit_rate:.1f}%")
        logger.info(f"  Target Hit Rate: {stats.target_hit_rate:.1f}%")
        logger.info(f"  Long Win Rate: {stats.long_win_rate:.1f}%")
        logger.info(f"  Short Win Rate: {stats.short_win_rate:.1f}%")
        logger.info("-" * 40)
        logger.info("CONFIDENCE ANALYSIS:")
        logger.info(f"  High Conf (>=80%) Win Rate: {stats.high_conf_win_rate:.1f}%")
        logger.info(f"  Low Conf (<80%) Win Rate: {stats.low_conf_win_rate:.1f}%")
        logger.info("=" * 60)


# Global instance
_trade_logger: Optional[TradeLogger] = None

def get_trade_logger() -> TradeLogger:
    """Get or create global trade logger instance."""
    global _trade_logger
    if _trade_logger is None:
        _trade_logger = TradeLogger()
    return _trade_logger


class TradeJournalService:
    """
    Async wrapper for TradeLogger to support SmartFlow's async signal logging.
    Logs ALL signals (accepted + rejected) for forward testing analysis.
    """

    def __init__(self):
        self._logger = get_trade_logger()

    async def log_signal(
        self,
        ticker: str,
        action: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        confidence: float,
        aligned_tfs: int,
        bias: str,
        atr: float,
        risk_reward: float,
        rejection_reason: Optional[str] = None,
        source: str = 'deterministic'
    ) -> Optional[int]:
        """
        Log a signal (accepted or rejected) to the journal asynchronously.

        This is called for EVERY signal, not just accepted ones.
        Rejected signals help us understand filter effectiveness.
        """
        try:
            # Create a synthetic signal object for the underlying logger
            from app.services.indicators import MultiTimeframeSignal

            signal = MultiTimeframeSignal(
                ticker=ticker,
                timestamp=now_est(),
                should_trade=(action != 'none' and rejection_reason is None),
                action=action if action != 'none' else 'hold',
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=risk_reward,
                confidence_score=confidence,
                aligned_bullish=aligned_tfs if bias == 'bullish' else 0,
                aligned_bearish=aligned_tfs if bias == 'bearish' else 0,
                overall_bias=bias,
                atr_for_stops=atr,
                rejection_reason=rejection_reason
            )

            return self._logger.log_signal(signal, entry_price)

        except Exception as e:
            logger.error(f"TradeJournalService.log_signal failed: {e}")
            return None

    def compute_stats(self, ticker: Optional[str] = None, days_back: int = 7) -> TradeStats:
        """Compute trading statistics."""
        return self._logger.compute_stats(ticker, days_back)

    def print_stats(self, stats: TradeStats):
        """Print formatted statistics."""
        self._logger.print_stats(stats)


# Global TradeJournalService instance
_trade_journal_service: Optional[TradeJournalService] = None

def get_trade_journal() -> TradeJournalService:
    """Get or create global trade journal service instance."""
    global _trade_journal_service
    if _trade_journal_service is None:
        _trade_journal_service = TradeJournalService()
    return _trade_journal_service
