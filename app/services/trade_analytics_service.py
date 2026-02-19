"""
Trade Analytics Service

Provides comprehensive trade journaling, performance analytics, and risk metrics.
This is the brain of the trading intelligence system.
"""
import logging
import uuid
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc
import pytz

from app.models.database_models import (
    TradeJournal,
    StrategyPerformance,
    TimeBasedStats,
    CircuitBreakerSettings,
    CircuitBreakerEvent,
    DynamicSizingSettings,
    EquityCurveState,
    TradingAccount,
    DailyPnL,
)
from app.models.models import ExecutionLog

logger = logging.getLogger(__name__)


class TradeAnalyticsService:
    """
    Core analytics service for trade journaling and performance tracking.
    """

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # TRADE JOURNAL OPERATIONS
    # =========================================================================

    def create_journal_entry(
        self,
        user_id: int,
        account_id: int,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        entry_time: datetime,
        execution_log_id: Optional[int] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        strategy_name: Optional[str] = None,
        broker_trade_id: Optional[str] = None,
        webhook_payload: Optional[dict] = None,
        atr_at_entry: Optional[float] = None,
    ) -> TradeJournal:
        """Create a new trade journal entry when a position is opened."""

        # Calculate timing metadata
        entry_hour = entry_time.hour
        entry_day_of_week = entry_time.weekday()  # 0=Monday
        entry_session = self._get_trading_session(entry_time)

        # Calculate risk metrics if SL is provided
        risk_amount = None
        reward_amount = None
        risk_reward_ratio = None

        if stop_loss and entry_price:
            if side.lower() == 'buy':
                risk_amount = abs(entry_price - stop_loss) * quantity
                if take_profit:
                    reward_amount = abs(take_profit - entry_price) * quantity
            else:
                risk_amount = abs(stop_loss - entry_price) * quantity
                if take_profit:
                    reward_amount = abs(entry_price - take_profit) * quantity

            if risk_amount and risk_amount > 0 and reward_amount:
                risk_reward_ratio = reward_amount / risk_amount

        entry = TradeJournal(
            user_id=user_id,
            account_id=account_id,
            trade_uuid=str(uuid.uuid4()),
            broker_trade_id=broker_trade_id,
            symbol=symbol,
            side=side.lower(),
            quantity=quantity,
            quantity_closed=0.0,
            entry_price=entry_price,
            entry_time=entry_time,
            entry_execution_id=execution_log_id,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_amount=risk_amount,
            reward_amount=reward_amount,
            risk_reward_ratio=risk_reward_ratio,
            strategy_name=strategy_name,
            entry_hour=entry_hour,
            entry_day_of_week=entry_day_of_week,
            entry_session=entry_session,
            atr_at_entry=atr_at_entry,
            status='open',
            webhook_payload=webhook_payload,
        )

        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)

        logger.info(f"Created trade journal entry {entry.trade_uuid} for {symbol} {side}")
        return entry

    def close_journal_entry(
        self,
        trade_uuid: str = None,
        broker_trade_id: str = None,
        account_id: int = None,
        symbol: str = None,
        exit_price: float = None,
        exit_time: datetime = None,
        gross_pnl: float = None,
        commission: float = 0.0,
        swap: float = 0.0,
        exit_reason: str = 'signal',
        execution_log_id: Optional[int] = None,
    ) -> Optional[TradeJournal]:
        """Close an existing trade journal entry."""

        # Find the open trade
        query = self.db.query(TradeJournal).filter(TradeJournal.status == 'open')

        if trade_uuid:
            query = query.filter(TradeJournal.trade_uuid == trade_uuid)
        elif broker_trade_id and account_id:
            query = query.filter(
                TradeJournal.broker_trade_id == broker_trade_id,
                TradeJournal.account_id == account_id
            )
        elif account_id and symbol:
            # Find most recent open trade for this account/symbol
            query = query.filter(
                TradeJournal.account_id == account_id,
                TradeJournal.symbol == symbol
            ).order_by(desc(TradeJournal.entry_time))
        else:
            logger.warning("Insufficient criteria to find trade journal entry")
            return None

        entry = query.first()

        if not entry:
            logger.warning(f"No open trade found for closing: uuid={trade_uuid}, broker_id={broker_trade_id}")
            return None

        # Update entry with exit details
        exit_time = exit_time or datetime.now(pytz.UTC)
        entry.exit_price = exit_price
        entry.exit_time = exit_time
        entry.exit_execution_id = execution_log_id
        entry.exit_reason = exit_reason
        entry.quantity_closed = entry.quantity

        # Calculate P&L
        entry.gross_pnl = gross_pnl
        entry.commission = commission
        entry.swap = swap
        entry.net_pnl = (gross_pnl or 0) - commission - swap

        # Calculate P&L in pips/points if we have prices
        if exit_price and entry.entry_price:
            if entry.side == 'buy':
                entry.pnl_pips = exit_price - entry.entry_price
            else:
                entry.pnl_pips = entry.entry_price - exit_price

        # Calculate holding time
        if entry.entry_time:
            holding_delta = exit_time - entry.entry_time
            entry.holding_time_seconds = int(holding_delta.total_seconds())

        # Determine win/loss
        entry.is_winner = entry.net_pnl > 0 if entry.net_pnl is not None else None

        # Update status
        entry.status = 'closed'
        entry.closed_at = exit_time

        self.db.commit()
        self.db.refresh(entry)

        logger.info(f"Closed trade journal entry {entry.trade_uuid}: PnL=${entry.net_pnl:.2f}")

        # Update analytics
        self._update_strategy_performance(entry)
        self._update_time_based_stats(entry)
        self._update_equity_curve(entry)

        return entry

    def find_open_trade(
        self,
        account_id: int,
        symbol: str,
        side: Optional[str] = None
    ) -> Optional[TradeJournal]:
        """Find an open trade for the given account and symbol."""
        query = self.db.query(TradeJournal).filter(
            TradeJournal.account_id == account_id,
            TradeJournal.symbol == symbol,
            TradeJournal.status == 'open'
        )
        if side:
            query = query.filter(TradeJournal.side == side.lower())
        return query.order_by(desc(TradeJournal.entry_time)).first()

    # =========================================================================
    # PERFORMANCE ANALYTICS
    # =========================================================================

    def calculate_performance_metrics(
        self,
        user_id: int,
        strategy_name: Optional[str] = None,
        account_id: Optional[int] = None,
        period_type: str = 'all_time',
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""

        # Build query for closed trades
        query = self.db.query(TradeJournal).filter(
            TradeJournal.user_id == user_id,
            TradeJournal.status == 'closed',
            TradeJournal.net_pnl.isnot(None)
        )

        if strategy_name:
            query = query.filter(TradeJournal.strategy_name == strategy_name)
        if account_id:
            query = query.filter(TradeJournal.account_id == account_id)
        if start_date:
            query = query.filter(TradeJournal.closed_at >= start_date)
        if end_date:
            query = query.filter(TradeJournal.closed_at <= end_date)

        trades = query.order_by(TradeJournal.closed_at).all()

        if not trades:
            # Fall back to execution_logs for basic stats
            return self._get_execution_log_metrics(user_id, account_id)

        # Basic counts
        total_trades = len(trades)
        winners = [t for t in trades if t.net_pnl > 0]
        losers = [t for t in trades if t.net_pnl < 0]
        breakeven = [t for t in trades if t.net_pnl == 0]

        winning_trades = len(winners)
        losing_trades = len(losers)
        breakeven_trades = len(breakeven)

        # Win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        # P&L calculations
        gross_profit = sum(t.net_pnl for t in winners)
        gross_loss = abs(sum(t.net_pnl for t in losers))
        net_profit = sum(t.net_pnl for t in trades)
        total_commission = sum(t.commission or 0 for t in trades)

        # Average win/loss
        avg_win = gross_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = gross_loss / losing_trades if losing_trades > 0 else 0

        # Largest win/loss
        largest_win = max((t.net_pnl for t in winners), default=0)
        largest_loss = abs(min((t.net_pnl for t in losers), default=0))

        # Profit factor
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Expectancy
        loss_rate = 100 - win_rate
        expectancy = (win_rate / 100 * avg_win) - (loss_rate / 100 * avg_loss)

        # Consecutive wins/losses
        max_consecutive_wins, max_consecutive_losses, current_streak = self._calculate_streaks(trades)

        # Drawdown calculation
        max_drawdown, max_drawdown_pct = self._calculate_drawdown(trades)

        # Time analysis
        avg_holding_time = sum(t.holding_time_seconds or 0 for t in trades) / total_trades
        best_hour = self._find_best_hour(trades)
        best_day = self._find_best_day(trades)
        best_session = self._find_best_session(trades)

        # Sharpe ratio (simplified - using daily returns)
        sharpe_ratio = self._calculate_sharpe_ratio(trades)

        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'breakeven_trades': breakeven_trades,
            'win_rate': round(win_rate, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'net_profit': round(net_profit, 2),
            'total_commission': round(total_commission, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'largest_win': round(largest_win, 2),
            'largest_loss': round(largest_loss, 2),
            'profit_factor': round(profit_factor, 2) if profit_factor != float('inf') else None,
            'expectancy': round(expectancy, 2),
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'current_streak': current_streak,
            'max_drawdown': round(max_drawdown, 2),
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'avg_holding_time_seconds': int(avg_holding_time),
            'best_hour': best_hour,
            'best_day': best_day,
            'best_session': best_session,
            'sharpe_ratio': round(sharpe_ratio, 2) if sharpe_ratio else None,
        }

    def _get_execution_log_metrics(
        self,
        user_id: int,
        account_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get metrics from execution_logs when trade_journal is empty."""
        from app.models.models import ExecutionLog

        # Get accounts for this user
        user_accounts = self.db.query(TradingAccount.id).filter(
            TradingAccount.user_id == user_id
        ).all()
        account_ids = [a.id for a in user_accounts]

        if not account_ids:
            return self._empty_metrics()

        # Query execution logs
        query = self.db.query(ExecutionLog).filter(
            ExecutionLog.account_id.in_(account_ids),
            ExecutionLog.status == 'success'
        )

        if account_id:
            query = query.filter(ExecutionLog.account_id == account_id)

        logs = query.all()

        if not logs:
            return self._empty_metrics()

        # Count entries and exits
        entries = [l for l in logs if l.action.lower() in ('buy', 'sell')]
        exits = [l for l in logs if 'close' in l.action.lower()]

        # Calculate P&L from close actions that have P&L data
        closes_with_pnl = [l for l in exits if l.pnl is not None]
        winning_trades = len([l for l in closes_with_pnl if l.pnl > 0])
        losing_trades = len([l for l in closes_with_pnl if l.pnl < 0])
        breakeven_trades = len([l for l in closes_with_pnl if l.pnl == 0])

        gross_profit = sum(l.pnl for l in closes_with_pnl if l.pnl > 0)
        gross_loss = abs(sum(l.pnl for l in closes_with_pnl if l.pnl < 0))
        net_profit = gross_profit - gross_loss

        # Calculate win rate if we have closed trades with P&L
        win_rate = None
        if closes_with_pnl:
            total_closed = winning_trades + losing_trades + breakeven_trades
            if total_closed > 0:
                win_rate = (winning_trades / total_closed) * 100

        # Profit factor
        profit_factor = None
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss

        # Expectancy
        expectancy = 0
        if closes_with_pnl:
            expectancy = net_profit / len(closes_with_pnl)

        # Largest win/loss
        wins = [l.pnl for l in closes_with_pnl if l.pnl > 0]
        losses = [l.pnl for l in closes_with_pnl if l.pnl < 0]
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0  # Will be negative

        # Time analysis based on closes with P&L
        hourly_stats = {}  # {hour: {'pnl': [], 'wins': 0, 'losses': 0}}
        daily_stats = {}   # {day: {'pnl': [], 'wins': 0, 'losses': 0}}
        session_stats = {  # Session-based stats
            'asian': {'pnl': 0, 'wins': 0, 'losses': 0, 'count': 0},
            'london': {'pnl': 0, 'wins': 0, 'losses': 0, 'count': 0},
            'overlap': {'pnl': 0, 'wins': 0, 'losses': 0, 'count': 0},
            'new_york': {'pnl': 0, 'wins': 0, 'losses': 0, 'count': 0},
        }

        for log in closes_with_pnl:
            if log.created_at:
                hour = log.created_at.hour
                day = log.created_at.weekday()
                pnl = log.pnl or 0
                is_win = pnl > 0
                is_loss = pnl < 0

                # Hourly stats
                if hour not in hourly_stats:
                    hourly_stats[hour] = {'pnl': [], 'wins': 0, 'losses': 0}
                hourly_stats[hour]['pnl'].append(pnl)
                if is_win:
                    hourly_stats[hour]['wins'] += 1
                elif is_loss:
                    hourly_stats[hour]['losses'] += 1

                # Daily stats
                if day not in daily_stats:
                    daily_stats[day] = {'pnl': [], 'wins': 0, 'losses': 0}
                daily_stats[day]['pnl'].append(pnl)
                if is_win:
                    daily_stats[day]['wins'] += 1
                elif is_loss:
                    daily_stats[day]['losses'] += 1

                # Session stats (UTC hours)
                if 0 <= hour < 8:
                    session = 'asian'
                elif 8 <= hour < 13:
                    session = 'london'
                elif 13 <= hour < 17:
                    session = 'overlap'
                else:
                    session = 'new_york'

                session_stats[session]['pnl'] += pnl
                session_stats[session]['count'] += 1
                if is_win:
                    session_stats[session]['wins'] += 1
                elif is_loss:
                    session_stats[session]['losses'] += 1

        # Find best hour/day by P&L
        best_hour = None
        best_day = None
        best_session = None

        if hourly_stats:
            best_hour = max(hourly_stats.keys(), key=lambda h: sum(hourly_stats[h]['pnl']))
        if daily_stats:
            best_day = max(daily_stats.keys(), key=lambda d: sum(daily_stats[d]['pnl']))
        if session_stats:
            sessions_with_trades = {k: v for k, v in session_stats.items() if v['count'] > 0}
            if sessions_with_trades:
                best_session = max(sessions_with_trades.keys(), key=lambda s: session_stats[s]['pnl'])

        # Calculate streaks from close actions with P&L
        current_streak = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_win_streak = 0
        current_loss_streak = 0

        sorted_closes = sorted(closes_with_pnl, key=lambda x: x.created_at or datetime.min)
        for log in sorted_closes:
            if log.pnl > 0:
                current_win_streak += 1
                current_loss_streak = 0
                max_consecutive_wins = max(max_consecutive_wins, current_win_streak)
            elif log.pnl < 0:
                current_loss_streak += 1
                current_win_streak = 0
                max_consecutive_losses = max(max_consecutive_losses, current_loss_streak)

        # Current streak
        if sorted_closes:
            last_trade = sorted_closes[-1]
            if last_trade.pnl > 0:
                current_streak = current_win_streak
            elif last_trade.pnl < 0:
                current_streak = -current_loss_streak

        pnl_note = None
        if not closes_with_pnl:
            pnl_note = 'P&L tracking active. Metrics will populate as new trades close.'

        # Build hourly breakdown for UI (use string keys for JSON serialization)
        hourly_breakdown = {}
        for hour in range(24):
            hour_key = str(hour)
            if hour in hourly_stats:
                stats = hourly_stats[hour]
                total = stats['wins'] + stats['losses']
                hourly_breakdown[hour_key] = {
                    'win_rate': (stats['wins'] / total * 100) if total > 0 else 0,
                    'pnl': sum(stats['pnl']),
                    'trades': total
                }
            else:
                hourly_breakdown[hour_key] = {'win_rate': 0, 'pnl': 0, 'trades': 0}

        # Build daily breakdown for UI (0=Monday, 6=Sunday)
        daily_breakdown = {}
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in range(7):
            if day in daily_stats:
                stats = daily_stats[day]
                total = stats['wins'] + stats['losses']
                daily_breakdown[day_names[day]] = {
                    'win_rate': (stats['wins'] / total * 100) if total > 0 else 0,
                    'pnl': sum(stats['pnl']),
                    'trades': total
                }
            else:
                daily_breakdown[day_names[day]] = {'win_rate': 0, 'pnl': 0, 'trades': 0}

        # Build session breakdown for UI
        session_breakdown = {}
        for session_name, stats in session_stats.items():
            total = stats['wins'] + stats['losses']
            session_breakdown[session_name] = {
                'win_rate': (stats['wins'] / total * 100) if total > 0 else 0,
                'pnl': stats['pnl'],
                'trades': stats['count']
            }

        return {
            'total_trades': len(entries),
            'total_entries': len(entries),
            'total_exits': len(exits),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'breakeven_trades': breakeven_trades,
            'win_rate': win_rate,
            'gross_profit': gross_profit,
            'gross_loss': gross_loss,
            'net_profit': net_profit,
            'total_commission': 0,
            'avg_win': gross_profit / winning_trades if winning_trades > 0 else 0,
            'avg_loss': gross_loss / losing_trades if losing_trades > 0 else 0,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'profit_factor': profit_factor,
            'expectancy': expectancy,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'current_streak': current_streak,
            'max_drawdown': 0,
            'max_drawdown_pct': 0,
            'avg_holding_time_seconds': 0,
            'best_hour': best_hour,
            'best_day': best_day,
            'best_session': best_session,
            'sharpe_ratio': None,
            'hourly_stats': hourly_breakdown,
            'daily_stats': daily_breakdown,
            'session_stats': session_breakdown,
            'data_source': 'execution_logs',
            'pnl_tracking_note': pnl_note
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'breakeven_trades': 0,
            'win_rate': 0,
            'gross_profit': 0,
            'gross_loss': 0,
            'net_profit': 0,
            'total_commission': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0,
            'profit_factor': None,
            'expectancy': 0,
            'max_consecutive_wins': 0,
            'max_consecutive_losses': 0,
            'current_streak': 0,
            'max_drawdown': 0,
            'max_drawdown_pct': 0,
            'avg_holding_time_seconds': 0,
            'best_hour': None,
            'best_day': None,
            'best_session': None,
            'sharpe_ratio': None,
        }

    def _calculate_streaks(self, trades: List[TradeJournal]) -> Tuple[int, int, int]:
        """Calculate max consecutive wins, losses, and current streak."""
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0

        for trade in trades:
            if trade.net_pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif trade.net_pnl < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
            else:
                current_wins = 0
                current_losses = 0

        current_streak = current_wins if current_wins > 0 else -current_losses
        return max_wins, max_losses, current_streak

    def _calculate_drawdown(self, trades: List[TradeJournal]) -> Tuple[float, float]:
        """Calculate maximum drawdown."""
        if not trades:
            return 0, 0

        equity = 0
        peak = 0
        max_dd = 0
        max_dd_pct = 0

        for trade in trades:
            equity += trade.net_pnl or 0
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = (dd / peak * 100) if peak > 0 else 0

        return max_dd, max_dd_pct

    def _calculate_sharpe_ratio(self, trades: List[TradeJournal], risk_free_rate: float = 0.02) -> Optional[float]:
        """Calculate simplified Sharpe ratio."""
        if len(trades) < 2:
            return None

        returns = [t.net_pnl for t in trades if t.net_pnl is not None]
        if not returns:
            return None

        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return None

        # Annualized (assuming 252 trading days)
        sharpe = (avg_return * 252 - risk_free_rate) / (std_dev * (252 ** 0.5))
        return sharpe

    def _find_best_hour(self, trades: List[TradeJournal]) -> Optional[int]:
        """Find the most profitable trading hour."""
        hourly_pnl = {}
        for trade in trades:
            if trade.entry_hour is not None:
                hourly_pnl.setdefault(trade.entry_hour, []).append(trade.net_pnl or 0)

        if not hourly_pnl:
            return None

        best_hour = max(hourly_pnl.keys(), key=lambda h: sum(hourly_pnl[h]))
        return best_hour

    def _find_best_day(self, trades: List[TradeJournal]) -> Optional[int]:
        """Find the most profitable trading day."""
        daily_pnl = {}
        for trade in trades:
            if trade.entry_day_of_week is not None:
                daily_pnl.setdefault(trade.entry_day_of_week, []).append(trade.net_pnl or 0)

        if not daily_pnl:
            return None

        best_day = max(daily_pnl.keys(), key=lambda d: sum(daily_pnl[d]))
        return best_day

    def _find_best_session(self, trades: List[TradeJournal]) -> Optional[str]:
        """Find the most profitable trading session."""
        session_pnl = {}
        for trade in trades:
            if trade.entry_session:
                session_pnl.setdefault(trade.entry_session, []).append(trade.net_pnl or 0)

        if not session_pnl:
            return None

        best_session = max(session_pnl.keys(), key=lambda s: sum(session_pnl[s]))
        return best_session

    def _get_trading_session(self, dt: datetime) -> str:
        """Determine trading session based on time (UTC)."""
        hour = dt.hour

        # Simplified session times (UTC)
        if 0 <= hour < 8:
            return 'asian'
        elif 8 <= hour < 13:
            return 'london'
        elif 13 <= hour < 17:
            return 'overlap'  # London/NY overlap
        else:
            return 'new_york'

    # =========================================================================
    # STRATEGY PERFORMANCE UPDATES
    # =========================================================================

    def _update_strategy_performance(self, trade: TradeJournal):
        """Update strategy performance after trade close."""
        if not trade.strategy_name:
            return

        # Get or create strategy performance record
        perf = self.db.query(StrategyPerformance).filter(
            StrategyPerformance.user_id == trade.user_id,
            StrategyPerformance.strategy_name == trade.strategy_name,
            StrategyPerformance.period_type == 'all_time'
        ).first()

        if not perf:
            perf = StrategyPerformance(
                user_id=trade.user_id,
                strategy_name=trade.strategy_name,
                period_type='all_time'
            )
            self.db.add(perf)

        # Recalculate metrics
        metrics = self.calculate_performance_metrics(
            user_id=trade.user_id,
            strategy_name=trade.strategy_name
        )

        # Update record
        perf.total_trades = metrics['total_trades']
        perf.winning_trades = metrics['winning_trades']
        perf.losing_trades = metrics['losing_trades']
        perf.breakeven_trades = metrics['breakeven_trades']
        perf.win_rate = metrics['win_rate']
        perf.avg_win = metrics['avg_win']
        perf.avg_loss = metrics['avg_loss']
        perf.largest_win = metrics['largest_win']
        perf.largest_loss = metrics['largest_loss']
        perf.gross_profit = metrics['gross_profit']
        perf.gross_loss = metrics['gross_loss']
        perf.net_profit = metrics['net_profit']
        perf.total_commission = metrics['total_commission']
        perf.profit_factor = metrics['profit_factor']
        perf.expectancy = metrics['expectancy']
        perf.max_consecutive_wins = metrics['max_consecutive_wins']
        perf.max_consecutive_losses = metrics['max_consecutive_losses']
        perf.current_streak = metrics['current_streak']
        perf.max_drawdown = metrics['max_drawdown']
        perf.max_drawdown_pct = metrics['max_drawdown_pct']
        perf.avg_holding_time_seconds = metrics['avg_holding_time_seconds']
        perf.best_hour = metrics['best_hour']
        perf.best_day = metrics['best_day']
        perf.best_session = metrics['best_session']
        perf.sharpe_ratio = metrics['sharpe_ratio']

        self.db.commit()

    def _update_time_based_stats(self, trade: TradeJournal):
        """Update time-based statistics after trade close."""
        # Update hourly stats
        if trade.entry_hour is not None:
            self._update_stat(trade, 'hourly', trade.entry_hour)

        # Update daily stats
        if trade.entry_day_of_week is not None:
            self._update_stat(trade, 'daily', trade.entry_day_of_week)

        # Update session stats
        if trade.entry_session:
            session_map = {'asian': 0, 'london': 1, 'overlap': 2, 'new_york': 3}
            self._update_stat(trade, 'session', session_map.get(trade.entry_session, 0))

    def _update_stat(self, trade: TradeJournal, stat_type: str, stat_value: int):
        """Update a specific time-based stat."""
        stat = self.db.query(TimeBasedStats).filter(
            TimeBasedStats.user_id == trade.user_id,
            TimeBasedStats.stat_type == stat_type,
            TimeBasedStats.stat_value == stat_value
        ).first()

        if not stat:
            stat = TimeBasedStats(
                user_id=trade.user_id,
                stat_type=stat_type,
                stat_value=stat_value
            )
            self.db.add(stat)

        stat.total_trades = (stat.total_trades or 0) + 1
        if trade.net_pnl and trade.net_pnl > 0:
            stat.winning_trades = (stat.winning_trades or 0) + 1
        elif trade.net_pnl and trade.net_pnl < 0:
            stat.losing_trades = (stat.losing_trades or 0) + 1

        stat.net_pnl = (stat.net_pnl or 0) + (trade.net_pnl or 0)
        stat.win_rate = (stat.winning_trades / stat.total_trades * 100) if stat.total_trades > 0 else 0
        stat.avg_pnl = stat.net_pnl / stat.total_trades if stat.total_trades > 0 else 0

        # Mark as not recommended if win rate is poor
        stat.is_recommended = stat.win_rate >= 45 and stat.avg_pnl >= 0

        self.db.commit()

    # =========================================================================
    # EQUITY CURVE TRADING
    # =========================================================================

    def _update_equity_curve(self, trade: TradeJournal):
        """Update equity curve state after trade close."""
        # Get or create equity curve state
        state = self.db.query(EquityCurveState).filter(
            EquityCurveState.user_id == trade.user_id,
            EquityCurveState.account_id == None,  # User-level
            EquityCurveState.strategy_name == None
        ).first()

        if not state:
            state = EquityCurveState(
                user_id=trade.user_id,
                pnl_history=[]
            )
            self.db.add(state)

        # Update state
        state.cumulative_pnl = (state.cumulative_pnl or 0) + (trade.net_pnl or 0)
        state.trade_count = (state.trade_count or 0) + 1

        # Update P&L history (keep last 50)
        history = state.pnl_history or []
        history.append(trade.net_pnl or 0)
        if len(history) > 50:
            history = history[-50:]
        state.pnl_history = history

        # Calculate moving average (20-trade MA)
        ma_periods = 20
        if len(history) >= ma_periods:
            recent = history[-ma_periods:]
            cumulative = sum(recent)
            state.equity_ma = cumulative

            # Check if above/below MA
            was_above = state.is_above_ma
            state.is_above_ma = state.cumulative_pnl >= state.equity_ma

            # Track crossovers
            if was_above and not state.is_above_ma:
                state.crosses_below_at = datetime.now(pytz.UTC)
            elif not was_above and state.is_above_ma:
                state.crosses_above_at = datetime.now(pytz.UTC)

        self.db.commit()

    def get_equity_curve_status(self, user_id: int) -> Dict[str, Any]:
        """Get current equity curve trading status."""
        state = self.db.query(EquityCurveState).filter(
            EquityCurveState.user_id == user_id,
            EquityCurveState.account_id == None,
            EquityCurveState.strategy_name == None
        ).first()

        if not state:
            return {
                'is_trading_allowed': True,
                'is_above_ma': True,
                'cumulative_pnl': 0,
                'equity_ma': 0,
                'trade_count': 0
            }

        return {
            'is_trading_allowed': state.is_trading_allowed,
            'is_above_ma': state.is_above_ma,
            'cumulative_pnl': state.cumulative_pnl,
            'equity_ma': state.equity_ma,
            'trade_count': state.trade_count,
            'crosses_below_at': state.crosses_below_at.isoformat() if state.crosses_below_at else None,
            'crosses_above_at': state.crosses_above_at.isoformat() if state.crosses_above_at else None
        }

    # =========================================================================
    # CIRCUIT BREAKER CHECKS
    # =========================================================================

    def check_circuit_breakers(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Check if any circuit breakers should prevent trading.
        Returns (should_allow_trade, reason_if_blocked)
        """
        # Get user's circuit breaker settings
        settings = self.db.query(CircuitBreakerSettings).filter(
            CircuitBreakerSettings.user_id == user_id
        ).first()

        if not settings:
            return True, None

        # Check for active circuit breaker events
        active_event = self.db.query(CircuitBreakerEvent).filter(
            CircuitBreakerEvent.user_id == user_id,
            CircuitBreakerEvent.is_active == True
        ).first()

        if active_event:
            # Check if it should auto-resume
            if active_event.expires_at and datetime.now(pytz.UTC) >= active_event.expires_at:
                active_event.is_active = False
                active_event.resumed_at = datetime.now(pytz.UTC)
                active_event.resume_reason = 'auto'
                self.db.commit()
            else:
                return False, f"Circuit breaker active: {active_event.trigger_type}"

        # Check daily loss limit
        if settings.daily_loss_limit_enabled:
            daily_pnl = self._get_daily_pnl(user_id)
            limit = settings.daily_loss_limit_amount or (settings.daily_loss_limit_pct / 100 * 10000)  # Simplified

            if daily_pnl < -limit:
                self._trigger_circuit_breaker(user_id, 'daily_loss', abs(daily_pnl), limit, settings)
                return False, f"Daily loss limit exceeded: ${abs(daily_pnl):.2f}"

        # Check consecutive losses
        if settings.consecutive_loss_enabled:
            streak = self._get_current_loss_streak(user_id)
            if streak >= settings.max_consecutive_losses:
                self._trigger_circuit_breaker(user_id, 'consecutive_loss', streak, settings.max_consecutive_losses, settings)
                return False, f"Consecutive losses exceeded: {streak}"

        # Check win rate degradation
        if settings.win_rate_enabled:
            recent_win_rate = self._get_recent_win_rate(user_id, settings.win_rate_lookback_trades)
            if recent_win_rate < settings.min_win_rate:
                self._trigger_circuit_breaker(user_id, 'win_rate', recent_win_rate, settings.min_win_rate, settings)
                return False, f"Win rate too low: {recent_win_rate:.1f}%"

        return True, None

    def _get_daily_pnl(self, user_id: int) -> float:
        """Get today's P&L for user."""
        today = date.today()
        result = self.db.query(func.sum(TradeJournal.net_pnl)).filter(
            TradeJournal.user_id == user_id,
            TradeJournal.status == 'closed',
            func.date(TradeJournal.closed_at) == today
        ).scalar()
        return result or 0.0

    def _get_current_loss_streak(self, user_id: int) -> int:
        """Get current consecutive loss streak."""
        trades = self.db.query(TradeJournal).filter(
            TradeJournal.user_id == user_id,
            TradeJournal.status == 'closed'
        ).order_by(desc(TradeJournal.closed_at)).limit(20).all()

        streak = 0
        for trade in trades:
            if trade.net_pnl and trade.net_pnl < 0:
                streak += 1
            else:
                break
        return streak

    def _get_recent_win_rate(self, user_id: int, lookback: int) -> float:
        """Get win rate for recent trades."""
        trades = self.db.query(TradeJournal).filter(
            TradeJournal.user_id == user_id,
            TradeJournal.status == 'closed'
        ).order_by(desc(TradeJournal.closed_at)).limit(lookback).all()

        if not trades:
            return 100.0  # No trades = no degradation

        winners = sum(1 for t in trades if t.net_pnl and t.net_pnl > 0)
        return (winners / len(trades)) * 100

    def _trigger_circuit_breaker(
        self,
        user_id: int,
        trigger_type: str,
        trigger_value: float,
        limit_value: float,
        settings: CircuitBreakerSettings
    ):
        """Create a circuit breaker event."""
        expires_at = None
        if settings.auto_resume_enabled:
            expires_at = datetime.now(pytz.UTC) + timedelta(hours=settings.auto_resume_after_hours)

        event = CircuitBreakerEvent(
            user_id=user_id,
            trigger_type=trigger_type,
            trigger_value=trigger_value,
            limit_value=limit_value,
            is_active=True,
            expires_at=expires_at
        )
        self.db.add(event)
        self.db.commit()

        logger.warning(f"Circuit breaker triggered for user {user_id}: {trigger_type}")

    # =========================================================================
    # DYNAMIC POSITION SIZING
    # =========================================================================

    def get_position_size_multiplier(self, user_id: int, base_size: float) -> float:
        """
        Calculate position size multiplier based on performance.
        Returns a multiplier to apply to the base position size.
        """
        settings = self.db.query(DynamicSizingSettings).filter(
            DynamicSizingSettings.user_id == user_id
        ).first()

        if not settings or not settings.enabled:
            return 1.0

        multiplier = 1.0

        # Get current streak
        streak = self._get_current_streak(user_id)

        # Adjust based on win streak
        if settings.increase_on_win_streak and streak >= settings.win_streak_threshold:
            multiplier *= (1 + settings.win_streak_increase_pct / 100)

        # Adjust based on loss streak
        if settings.decrease_on_loss_streak and streak <= -settings.loss_streak_threshold:
            multiplier *= (1 - settings.loss_streak_decrease_pct / 100)

        # Equity curve adjustment
        if settings.equity_curve_enabled:
            eq_status = self.get_equity_curve_status(user_id)
            if not eq_status['is_above_ma']:
                if settings.pause_below_ma:
                    return 0  # Don't trade at all
                else:
                    multiplier *= (1 - settings.reduce_below_ma_pct / 100)

        # Apply limits
        multiplier = max(settings.min_size_multiplier, min(multiplier, settings.max_size_multiplier))

        return multiplier

    def _get_current_streak(self, user_id: int) -> int:
        """Get current win/loss streak (positive = wins, negative = losses)."""
        trades = self.db.query(TradeJournal).filter(
            TradeJournal.user_id == user_id,
            TradeJournal.status == 'closed'
        ).order_by(desc(TradeJournal.closed_at)).limit(20).all()

        if not trades:
            return 0

        wins = 0
        losses = 0

        for trade in trades:
            if trade.net_pnl and trade.net_pnl > 0:
                if losses > 0:
                    break
                wins += 1
            elif trade.net_pnl and trade.net_pnl < 0:
                if wins > 0:
                    break
                losses += 1
            else:
                break

        return wins if wins > 0 else -losses

    # =========================================================================
    # REPORTING
    # =========================================================================

    def get_trade_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        strategy: Optional[str] = None,
        symbol: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Get trade history with filters."""
        query = self.db.query(TradeJournal).filter(
            TradeJournal.user_id == user_id
        )

        if status:
            query = query.filter(TradeJournal.status == status)
        if strategy:
            query = query.filter(TradeJournal.strategy_name == strategy)
        if symbol:
            query = query.filter(TradeJournal.symbol == symbol)
        if start_date:
            query = query.filter(TradeJournal.entry_time >= start_date)
        if end_date:
            query = query.filter(TradeJournal.entry_time <= end_date)

        trades = query.order_by(desc(TradeJournal.entry_time)).offset(offset).limit(limit).all()

        return [self._trade_to_dict(t) for t in trades]

    def _trade_to_dict(self, trade: TradeJournal) -> Dict[str, Any]:
        """Convert trade journal entry to dictionary."""
        return {
            'id': trade.id,
            'trade_uuid': trade.trade_uuid,
            'account_id': trade.account_id,
            'symbol': trade.symbol,
            'side': trade.side,
            'quantity': trade.quantity,
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'entry_time': trade.entry_time.isoformat() if trade.entry_time else None,
            'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
            'stop_loss': trade.stop_loss,
            'take_profit': trade.take_profit,
            'gross_pnl': trade.gross_pnl,
            'net_pnl': trade.net_pnl,
            'commission': trade.commission,
            'is_winner': trade.is_winner,
            'status': trade.status,
            'strategy_name': trade.strategy_name,
            'holding_time_seconds': trade.holding_time_seconds,
            'entry_session': trade.entry_session,
            'exit_reason': trade.exit_reason,
            'risk_reward_ratio': trade.risk_reward_ratio,
        }
