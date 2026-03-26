"""
SmartFlow Forward Testing Engine
================================

Paper trades the 2%/2% Pyramid strategy in real-time.
Logs all signals and tracks performance without real money.

Usage:
    from app.services.forward_test import ForwardTester

    tester = ForwardTester()
    await tester.start(['MNQ', 'MES', 'US30'])
"""

import asyncio
import logging
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import deque
from enum import Enum

# Database imports for persistence
try:
    from app.db.database import SessionLocal
    from app.models.models import ExecutionLog
    from app.models.smartflow_models import SmartFlowSignalLog
    from app.models.database_models import BrokerType
    from app.models.forward_test_models import ForwardTestTrade as DBForwardTestTrade, ForwardTestSession as DBForwardTestSession
    from app.models.strategy_registry_models import StrategyForwardTestSnapshot, SmartFlowStrategy
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    SessionLocal = None
    ExecutionLog = None
    SmartFlowSignalLog = None
    BrokerType = None
    DBForwardTestTrade = None
    DBForwardTestSession = None
    StrategyForwardTestSnapshot = None
    SmartFlowStrategy = None

logger = logging.getLogger(__name__)


class TradeStatus(Enum):
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class ForwardTestConfig:
    """Forward test configuration - matches backtest winning config."""
    # Account
    initial_capital: float = 25000.0

    # Stops - 2%/2% percentage-based
    pct_stop: float = 2.0
    pct_target: float = 2.0

    # Pyramid settings - PULLBACK-BASED (optimized)
    use_pyramid: bool = True
    pyramid_longs_only: bool = False  # Both directions work with pullback
    pyramid_max_positions: int = 3  # 3 positions optimal
    pyramid_addon_trigger: float = 1.0  # Fallback if pullback disabled

    # Pullback pyramid settings (Sharpe 4.7+ vs 3.3 original)
    pyramid_use_pullback: bool = True  # Wait for pullback before adding
    pyramid_pullback_pct: float = 0.50  # 50% retracement required
    pyramid_continuation_bars: int = 2  # 2 bars of continuation to confirm

    # Signal thresholds
    min_ensemble_prob: float = 0.62  # Raised from 0.55 - require higher confidence
    min_signal_strength: float = 60.0  # Raised from 50 - require stronger signals

    # Ranging market settings (mean-reversion)
    trade_ranging: bool = True  # Enable trading in ranging markets
    ranging_pct_stop: float = 0.75  # Tightened from 1.0% - quicker cuts in ranging
    ranging_pct_target: float = 1.5  # Better R:R: 1.5% target vs 0.75% stop (2:1)

    # Risk
    max_daily_loss_pct: float = 3.0
    position_size_pct: float = 2.0

    # Database persistence for UI traceability
    persist_to_db: bool = True  # Write trades to execution_logs table
    smartflow_config_id: Optional[int] = None  # Link to SmartFlowConfig for signal logs

    # ========================================
    # NEW: Enhanced features (2026 upgrades)
    # ========================================

    # Levels confluence
    use_levels_confluence: bool = True
    levels_confluence_min: float = 65.0   # Min confluence for deterministic

    # Trailing stops
    use_trailing_stop: bool = True
    trailing_breakeven_trigger: float = 2.0  # Move to BE at 2x risk
    trailing_partial_trigger: float = 3.0    # Partial exit at 3x risk
    trailing_partial_pct: float = 50.0       # Exit 50% at partial

    # News sentiment
    use_news_sentiment: bool = True
    news_boost_max: float = 0.05

    # Regime-asymmetric logic
    use_regime_asymmetric: bool = True
    uptrend_target_pct: float = 0.8         # 0.8% target in uptrend (1:4)
    uptrend_flow_require: str = 'HIGH'       # Require HIGH/EXTREME flow

    # Feature variants for A/B testing
    # Variant 1: Current (PCT 0.2/0.6)
    # Variant 2: Levels + Trailing + Sentiment
    # Variant 3: High-flow uptrend
    feature_variant: str = 'levels+trailing'  # Active variant


@dataclass
class ForwardTestTrade:
    """Single forward test trade."""
    id: str
    ticker: str
    direction: str  # 'long' or 'short'

    # Entry
    entry_time: datetime
    entry_price: float
    entry_signal_prob: float
    entry_regime: str

    # Stops (calculated at entry)
    stop_loss: float
    take_profit: float

    # Position
    size: float = 1.0
    status: TradeStatus = TradeStatus.OPEN

    # Exit (filled when closed)
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""

    # P&L
    pnl: float = 0.0
    pnl_pct: float = 0.0

    # Pyramid tracking
    is_addon: bool = False
    parent_trade_id: Optional[str] = None

    # Database IDs (for traceability)
    db_execution_id: Optional[int] = None
    db_signal_log_id: Optional[int] = None
    db_trade_id: Optional[int] = None  # ID in forward_test_trades table

    # Decision Snapshot (explains WHY signal fired)
    adx: Optional[float] = None
    hurst: Optional[float] = None
    atr: Optional[float] = None
    atr_pct: Optional[float] = None
    rsi: Optional[float] = None
    price_change_24h: Optional[float] = None
    volume_ratio: Optional[float] = None
    compression_flag: bool = False
    breakout_flag: bool = False
    strategy_mode: str = 'TRENDING'
    stop_pct_used: float = 2.0
    target_pct_used: float = 2.0
    size_multiplier: float = 1.0
    min_prob_threshold: float = 0.55
    min_strength_threshold: float = 50.0

    # Engine/strategy identification
    engine_type: str = 'DYNAMIC'
    volatility: Optional[float] = None

    # Canonical Metadata (Full Architecture)
    selected_strategy_id: Optional[str] = None  # e.g., 'deterministic_v1', 'ai_v1_proxy'
    selected_engine: Optional[str] = None  # e.g., 'deterministic', 'ai', 'quick', 'flow'
    guard_status: Optional[str] = None  # 'allowed', 'blocked', 'warned', 'not_available'
    guard_decision: Optional[str] = None  # 'execute', 'skip', 'pause_new_entries'
    flow_score: Optional[float] = None  # Flow sentiment score
    flow_confidence: Optional[float] = None  # Flow confidence percentage
    decision_source: Optional[str] = None  # 'performance_adaptive', 'regime_adaptive', 'default'
    canonical_metadata: Optional[Dict] = None  # Full _metadata dict for audit

    # ========================================
    # NEW: Enhanced features (2026 upgrades)
    # ========================================

    # Levels confluence
    levels_confluence: float = 0.0        # 0-100 confluence score
    nearest_level: str = ''               # Name of nearest level
    level_distance_pct: float = 0.0       # Distance to nearest level

    # Trailing stop tracking
    trailing_enabled: bool = False
    trailing_breakeven_hit: bool = False
    trailing_partial_exit_done: bool = False
    trailing_current_stop: float = 0.0

    # News sentiment
    news_sentiment: float = 0.0           # -1 to +1
    news_boost: float = 0.0               # Probability boost applied

    # Microstructure
    order_imbalance: float = 0.0          # -1 to +1
    vpin_toxicity: float = 0.0            # 0-1

    # Crypto funding (if applicable)
    funding_rate: float = 0.0
    funding_bias: str = 'neutral'

    # Regime-adjusted params
    regime_adjusted_target: float = 0.0   # Target adjusted for regime
    regime_min_rr: float = 3.0           # Minimum R:R for this regime

    # Feature variant for A/B testing
    feature_variant: str = 'current'      # 'current', 'levels+trailing', 'high_flow_uptrend'


@dataclass
class PullbackState:
    """Track pullback state for a ticker/direction."""
    swing_extreme: float = 0.0  # Highest high (long) or lowest low (short)
    pullback_extreme: float = 0.0  # Lowest low in pullback (long) or highest high (short)
    last_addon_price: float = 0.0  # Price of last add-on
    in_pullback: bool = False
    continuation_count: int = 0
    prev_close: float = 0.0


@dataclass
class ForwardTestSession:
    """Forward testing session state."""
    session_id: str
    start_time: datetime
    config: ForwardTestConfig

    # Performance
    capital: float = 25000.0
    peak_capital: float = 25000.0

    # Trades
    trades: List[ForwardTestTrade] = field(default_factory=list)
    open_trades: Dict[str, ForwardTestTrade] = field(default_factory=dict)

    # Pullback tracking per ticker
    pullback_states: Dict[str, PullbackState] = field(default_factory=dict)

    # Daily tracking
    daily_pnl: float = 0.0
    daily_trades: int = 0
    daily_wins: int = 0

    # Cumulative stats
    total_trades: int = 0
    total_wins: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0

    # Status
    is_active: bool = True
    paused_reason: str = ""


class ForwardTester:
    """
    Forward testing engine for SmartFlow strategy.
    Paper trades in real-time using live price feeds.
    """

    def __init__(self, config: Optional[ForwardTestConfig] = None):
        self.config = config or ForwardTestConfig()
        self.session: Optional[ForwardTestSession] = None
        self.price_feeds: Dict[str, Any] = {}
        self._running = False
        self._log_file = "forward_test_log.json"

        # Load existing session if available
        self._load_session()

    def _load_session(self):
        """Load existing session from disk."""
        session_file = ".forward_test_session.json"
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                    # Reconstruct session (simplified)
                    logger.info(f"Loaded existing session: {data.get('session_id')}")
            except Exception as e:
                logger.warning(f"Could not load session: {e}")

    def _save_session(self):
        """Save session state to disk."""
        if not self.session:
            return

        session_file = ".forward_test_session.json"
        try:
            data = {
                'session_id': self.session.session_id,
                'start_time': self.session.start_time.isoformat(),
                'capital': self.session.capital,
                'total_trades': self.session.total_trades,
                'total_wins': self.session.total_wins,
                'total_pnl': self.session.total_pnl,
                'is_active': self.session.is_active,
            }
            with open(session_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save session: {e}")

    def start_session(self, tickers: List[str]) -> ForwardTestSession:
        """Start a new forward testing session."""
        session_id = f"FT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.session = ForwardTestSession(
            session_id=session_id,
            start_time=datetime.now(),
            config=self.config,
            capital=self.config.initial_capital,
            peak_capital=self.config.initial_capital,
        )

        logger.info(f"Started forward test session: {session_id}")
        logger.info(f"Tickers: {tickers}")
        logger.info(f"Config: 2%/2% Pyramid Longs, max {self.config.pyramid_max_positions} positions")

        self._save_session()
        return self.session

    def calculate_stops(self, entry_price: float, direction: str) -> tuple:
        """Calculate stop loss and take profit based on 2%/2% config."""
        pct_stop = self.config.pct_stop / 100.0
        pct_target = self.config.pct_target / 100.0

        if direction == 'long':
            stop_loss = entry_price * (1 - pct_stop)
            take_profit = entry_price * (1 + pct_target)
        else:
            stop_loss = entry_price * (1 + pct_stop)
            take_profit = entry_price * (1 - pct_target)

        return stop_loss, take_profit

    def calculate_ranging_stops(self, entry_price: float, direction: str) -> tuple:
        """Calculate tighter stops for ranging/mean-reversion trades (1%/1%)."""
        pct_stop = self.config.ranging_pct_stop / 100.0
        pct_target = self.config.ranging_pct_target / 100.0

        if direction == 'long':
            stop_loss = entry_price * (1 - pct_stop)
            take_profit = entry_price * (1 + pct_target)
        else:
            stop_loss = entry_price * (1 + pct_stop)
            take_profit = entry_price * (1 - pct_target)

        return stop_loss, take_profit

    def check_entry_signal(
        self,
        ticker: str,
        price: float,
        regime: str,
        ensemble_prob: float,
        signal_strength: float
    ) -> Optional[Dict]:
        """
        Check if we should enter a trade based on signals.
        Returns entry details if valid, None otherwise.
        """
        if not self.session or not self.session.is_active:
            return None

        # Check daily loss limit
        if self.session.daily_pnl <= -self.config.initial_capital * (self.config.max_daily_loss_pct / 100):
            logger.warning(f"Daily loss limit reached: ${self.session.daily_pnl:.2f}")
            return None

        # Check signal thresholds
        if ensemble_prob < self.config.min_ensemble_prob:
            return None
        if signal_strength < self.config.min_signal_strength:
            return None

        # Determine direction based on regime
        direction = None
        use_ranging_stops = False

        if regime in ['trending_up', 'breakout']:
            direction = 'long'
        elif regime in ['trending_down'] and not self.config.pyramid_longs_only:
            direction = 'short'
        elif regime == 'ranging' and self.config.trade_ranging:
            # Mean-reversion in ranging markets
            # Use signal strength to determine direction (higher = more confident)
            # In ranging, we fade extremes - buy weakness, sell strength
            if signal_strength > 55 and ensemble_prob > 0.55:
                # Strong signal in ranging = mean-reversion opportunity
                # Direction based on ensemble: >0.55 for direction, bias based on recent move
                direction = 'long'  # Default to long, will be overridden by price action
                use_ranging_stops = True

        if not direction:
            return None

        # Check if we already have max positions for this ticker
        ticker_positions = sum(1 for t in self.session.open_trades.values()
                               if t.ticker == ticker and t.status == TradeStatus.OPEN)
        if ticker_positions >= self.config.pyramid_max_positions:
            return None

        # Calculate stops (tighter for ranging)
        if use_ranging_stops:
            stop_loss, take_profit = self.calculate_ranging_stops(price, direction)
        else:
            stop_loss, take_profit = self.calculate_stops(price, direction)

        return {
            'ticker': ticker,
            'direction': direction,
            'entry_price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'ensemble_prob': ensemble_prob,
            'regime': regime,
            'signal_strength': signal_strength,
        }

    def execute_entry(self, signal: Dict) -> ForwardTestTrade:
        """Execute a paper trade entry.

        Supports dynamic stop/target via 'stop_pct' and 'target_pct' in signal.
        Also captures decision snapshot indicators from the signal.
        """
        trade_id = f"{signal['ticker']}_{datetime.now().strftime('%H%M%S%f')}"

        # Check if dynamic stops are provided
        entry_price = signal['entry_price']
        direction = signal['direction']

        # Get stop/target percentages
        stop_pct_used = signal.get('stop_pct', self.config.pct_stop)
        target_pct_used = signal.get('target_pct', self.config.pct_target)

        if 'stop_pct' in signal and 'target_pct' in signal:
            # Recalculate stops with dynamic percentages
            stop_pct = signal['stop_pct'] / 100.0
            target_pct = signal['target_pct'] / 100.0

            if direction == 'long':
                stop_loss = entry_price * (1 - stop_pct)
                take_profit = entry_price * (1 + target_pct)
            else:  # short
                stop_loss = entry_price * (1 + stop_pct)
                take_profit = entry_price * (1 - target_pct)
        else:
            stop_loss = signal['stop_loss']
            take_profit = signal['take_profit']

        # Extract canonical metadata from signal (Full Architecture)
        canonical_metadata = signal.get('_metadata', {})

        # Determine engine_type from canonical metadata first, then fallback to legacy
        engine_type = canonical_metadata.get('selected_engine') or signal.get('engine_type')
        if not engine_type:
            source = signal.get('source', '')
            if 'AI' in source:
                engine_type = 'ai_only'
            elif 'Deterministic' in source:
                engine_type = 'deterministic'
            elif 'Quick' in source:
                engine_type = 'quick'
            else:
                engine_type = 'flow'

        trade = ForwardTestTrade(
            id=trade_id,
            ticker=signal['ticker'],
            direction=direction,
            entry_time=datetime.now(),
            entry_price=entry_price,
            entry_signal_prob=signal['ensemble_prob'],
            entry_regime=signal['regime'],
            stop_loss=stop_loss,
            take_profit=take_profit,
            size=1.0,  # Simplified - 1 contract
            status=TradeStatus.OPEN,
            # Decision snapshot - populated from signal
            adx=signal.get('adx'),
            hurst=signal.get('hurst'),
            atr=signal.get('atr'),
            atr_pct=signal.get('atr_pct'),
            rsi=signal.get('rsi'),
            price_change_24h=signal.get('price_change_24h'),
            volume_ratio=signal.get('volume_ratio'),
            compression_flag=signal.get('compression_flag', False),
            breakout_flag=signal.get('breakout_flag', False),
            strategy_mode=signal.get('strategy', 'TRENDING'),
            stop_pct_used=stop_pct_used,
            target_pct_used=target_pct_used,
            size_multiplier=signal.get('size_mult', 1.0),
            min_prob_threshold=self.config.min_ensemble_prob,
            min_strength_threshold=self.config.min_signal_strength,
            engine_type=engine_type,  # Phase 0.5: Engine source tracking
            # Canonical Metadata (Full Architecture)
            selected_strategy_id=canonical_metadata.get('selected_strategy_id'),
            selected_engine=canonical_metadata.get('selected_engine'),
            guard_status=canonical_metadata.get('guard_status'),
            guard_decision=canonical_metadata.get('guard_decision'),
            flow_score=canonical_metadata.get('flow_score'),
            flow_confidence=canonical_metadata.get('flow_confidence'),
            decision_source=canonical_metadata.get('decision_source'),
            canonical_metadata=canonical_metadata if canonical_metadata else None,
        )

        # Set pyramid info if applicable
        if signal.get('is_addon'):
            trade.is_addon = True
            trade.parent_trade_id = signal.get('parent_trade_id')

        self.session.trades.append(trade)
        self.session.open_trades[trade_id] = trade
        self.session.daily_trades += 1
        self.session.total_trades += 1

        self._log_trade_entry(trade)
        self._save_session()

        return trade

    def check_exits(self, ticker: str, high: float, low: float, close: float) -> List[ForwardTestTrade]:
        """Check if any open trades should be exited."""
        closed_trades = []

        for trade_id, trade in list(self.session.open_trades.items()):
            if trade.ticker != ticker or trade.status != TradeStatus.OPEN:
                continue

            exit_price = None
            exit_reason = None

            if trade.direction == 'long':
                if low <= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = 'stop_loss'
                elif high >= trade.take_profit:
                    exit_price = trade.take_profit
                    exit_reason = 'take_profit'
            else:  # short
                if high >= trade.stop_loss:
                    exit_price = trade.stop_loss
                    exit_reason = 'stop_loss'
                elif low <= trade.take_profit:
                    exit_price = trade.take_profit
                    exit_reason = 'take_profit'

            if exit_price:
                self._close_trade(trade, exit_price, exit_reason)
                closed_trades.append(trade)

        return closed_trades

    def _close_trade(self, trade: ForwardTestTrade, exit_price: float, reason: str):
        """Close a trade and update stats."""
        trade.exit_time = datetime.now()
        trade.exit_price = exit_price
        trade.exit_reason = reason
        trade.status = TradeStatus.CLOSED

        # Calculate P&L
        if trade.direction == 'long':
            trade.pnl = (exit_price - trade.entry_price) * trade.size
        else:
            trade.pnl = (trade.entry_price - exit_price) * trade.size

        trade.pnl_pct = (trade.pnl / trade.entry_price) * 100

        # Update session stats
        self.session.total_pnl += trade.pnl
        self.session.daily_pnl += trade.pnl
        self.session.capital += trade.pnl

        if trade.pnl > 0:
            self.session.total_wins += 1
            self.session.daily_wins += 1

        # Update peak and drawdown
        if self.session.capital > self.session.peak_capital:
            self.session.peak_capital = self.session.capital

        drawdown = (self.session.peak_capital - self.session.capital) / self.session.peak_capital * 100
        if drawdown > self.session.max_drawdown:
            self.session.max_drawdown = drawdown

        # Remove from open trades
        if trade.id in self.session.open_trades:
            del self.session.open_trades[trade.id]

        self._log_trade_exit(trade)
        self._save_session()

    def check_pyramid_addon(
        self,
        ticker: str,
        high: float,
        low: float,
        close: float,
        regime: str,
        ensemble_prob: float
    ) -> Optional[Dict]:
        """
        Check if we should add to an existing position (pyramid).
        Uses pullback-based detection for better entries.
        """
        if not self.config.use_pyramid:
            return None

        # Find existing open trade for this ticker
        existing_trades = [t for t in self.session.open_trades.values()
                         if t.ticker == ticker and t.status == TradeStatus.OPEN]

        if not existing_trades:
            # Reset pullback state if no open trades
            if ticker in self.session.pullback_states:
                del self.session.pullback_states[ticker]
            return None

        # Check if we can add more positions
        if len(existing_trades) >= self.config.pyramid_max_positions:
            return None

        # Get the most recent trade
        latest_trade = max(existing_trades, key=lambda t: t.entry_time)
        direction = latest_trade.direction

        # Skip shorts if longs_only
        if self.config.pyramid_longs_only and direction == 'short':
            return None

        # Initialize pullback state if needed
        if ticker not in self.session.pullback_states:
            self.session.pullback_states[ticker] = PullbackState(
                swing_extreme=latest_trade.entry_price,
                pullback_extreme=latest_trade.entry_price,
                last_addon_price=latest_trade.entry_price,
                prev_close=close
            )

        state = self.session.pullback_states[ticker]
        should_add = False

        if self.config.pyramid_use_pullback:
            # PULLBACK-BASED ADD-ON
            if direction == 'long':
                # Update swing high
                if high > state.swing_extreme:
                    state.swing_extreme = high
                    state.in_pullback = False
                    state.continuation_count = 0

                # Check for pullback (price dropped from swing high)
                move_size = state.swing_extreme - state.last_addon_price
                pullback_size = state.swing_extreme - low

                if move_size > 0 and pullback_size / move_size >= self.config.pyramid_pullback_pct:
                    state.in_pullback = True
                    state.pullback_extreme = min(state.pullback_extreme, low)

                # Check for continuation after pullback
                if state.in_pullback and close > state.pullback_extreme:
                    if close > state.prev_close:  # Higher close
                        state.continuation_count += 1
                    else:
                        state.continuation_count = 0

                    # Add when we have enough continuation bars
                    if state.continuation_count >= self.config.pyramid_continuation_bars:
                        should_add = True
                        # Reset state for next add-on
                        state.swing_extreme = close
                        state.pullback_extreme = close
                        state.last_addon_price = close
                        state.in_pullback = False
                        state.continuation_count = 0

            else:  # short
                # Update swing low
                if low < state.swing_extreme:
                    state.swing_extreme = low
                    state.in_pullback = False
                    state.continuation_count = 0

                # Check for pullback (price rose from swing low)
                move_size = state.last_addon_price - state.swing_extreme
                pullback_size = high - state.swing_extreme

                if move_size > 0 and pullback_size / move_size >= self.config.pyramid_pullback_pct:
                    state.in_pullback = True
                    state.pullback_extreme = max(state.pullback_extreme, high)

                # Check for continuation after pullback
                if state.in_pullback and close < state.pullback_extreme:
                    if close < state.prev_close:  # Lower close
                        state.continuation_count += 1
                    else:
                        state.continuation_count = 0

                    # Add when we have enough continuation bars
                    if state.continuation_count >= self.config.pyramid_continuation_bars:
                        should_add = True
                        state.swing_extreme = close
                        state.pullback_extreme = close
                        state.last_addon_price = close
                        state.in_pullback = False
                        state.continuation_count = 0

            state.prev_close = close

        else:
            # ORIGINAL: Add when price moves 1R in our favor
            risk_amount = abs(latest_trade.entry_price - latest_trade.stop_loss)
            trigger_distance = risk_amount * self.config.pyramid_addon_trigger

            if direction == 'long':
                should_add = close >= state.last_addon_price + trigger_distance
            else:
                should_add = close <= state.last_addon_price - trigger_distance

            if should_add:
                state.last_addon_price = close

        if should_add:
            stop_loss, take_profit = self.calculate_stops(close, direction)
            return {
                'ticker': ticker,
                'direction': direction,
                'entry_price': close,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'ensemble_prob': ensemble_prob,
                'regime': regime,
                'is_addon': True,
                'parent_trade_id': latest_trade.id,
            }

        return None

    def _log_trade_entry(self, trade: ForwardTestTrade):
        """Log trade entry to file, database, and console."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'ENTRY',
            'trade_id': trade.id,
            'ticker': trade.ticker,
            'direction': trade.direction,
            'entry_price': trade.entry_price,
            'stop_loss': trade.stop_loss,
            'take_profit': trade.take_profit,
            'regime': trade.entry_regime,
            'prob': trade.entry_signal_prob,
            # Canonical Metadata (Full Architecture)
            'engine_type': trade.engine_type,
            'selected_strategy_id': trade.selected_strategy_id,
            'selected_engine': trade.selected_engine,
            'guard_status': trade.guard_status,
            'guard_decision': trade.guard_decision,
            'flow_score': trade.flow_score,
            'flow_confidence': trade.flow_confidence,
            'decision_source': trade.decision_source,
        }

        # Write to JSON file (backup)
        self._append_log(log_entry)

        # Write to database for UI traceability
        if self.config.persist_to_db and DB_AVAILABLE:
            self._persist_entry_to_db(trade)

        logger.info(f"[ENTRY] {trade.ticker} {trade.direction.upper()} @ {trade.entry_price:.2f} "
                   f"SL={trade.stop_loss:.2f} TP={trade.take_profit:.2f}")

    def _log_trade_exit(self, trade: ForwardTestTrade):
        """Log trade exit to file, database, and console."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event': 'EXIT',
            'trade_id': trade.id,
            'ticker': trade.ticker,
            'direction': trade.direction,
            'entry_price': trade.entry_price,
            'exit_price': trade.exit_price,
            'exit_reason': trade.exit_reason,
            'pnl': trade.pnl,
            'pnl_pct': trade.pnl_pct,
        }

        # Write to JSON file (backup)
        self._append_log(log_entry)

        # Update database record with exit info
        if self.config.persist_to_db and DB_AVAILABLE:
            self._persist_exit_to_db(trade)

        win_loss = "WIN" if trade.pnl > 0 else "LOSS"
        logger.info(f"[EXIT] {trade.ticker} {win_loss} P&L=${trade.pnl:.2f} ({trade.pnl_pct:.1f}%) "
                   f"Reason={trade.exit_reason}")

    def _append_log(self, entry: Dict):
        """Append entry to log file."""
        try:
            with open(self._log_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')
        except Exception as e:
            logger.error(f"Failed to write log: {e}")

    def _persist_entry_to_db(self, trade: ForwardTestTrade):
        """Persist trade entry to database with full decision snapshot."""
        if not DB_AVAILABLE or not SessionLocal or not DBForwardTestTrade:
            return

        try:
            db = SessionLocal()

            session_id = self.session.session_id if self.session else 'unknown'
            action = 'buy' if trade.direction == 'long' else 'sell'

            # Create full decision snapshot
            raw_snapshot = {
                'config': {
                    'pct_stop': self.config.pct_stop,
                    'pct_target': self.config.pct_target,
                    'ranging_pct_stop': self.config.ranging_pct_stop,
                    'ranging_pct_target': self.config.ranging_pct_target,
                    'min_ensemble_prob': self.config.min_ensemble_prob,
                    'min_signal_strength': self.config.min_signal_strength,
                    'trade_ranging': self.config.trade_ranging,
                },
                'entry': {
                    'price': trade.entry_price,
                    'stop_loss': trade.stop_loss,
                    'take_profit': trade.take_profit,
                    'regime': trade.entry_regime,
                    'prob': trade.entry_signal_prob,
                },
                'indicators': {
                    'adx': trade.adx,
                    'hurst': trade.hurst,
                    'atr': trade.atr,
                    'rsi': trade.rsi,
                    'volume_ratio': trade.volume_ratio,
                },
                'strategy': {
                    'mode': trade.strategy_mode,
                    'stop_pct': trade.stop_pct_used,
                    'target_pct': trade.target_pct_used,
                    'size_mult': trade.size_multiplier,
                },
                # Canonical Metadata (Full Architecture)
                'canonical': {
                    'selected_strategy_id': trade.selected_strategy_id,
                    'selected_engine': trade.selected_engine,
                    'guard_status': trade.guard_status,
                    'guard_decision': trade.guard_decision,
                    'flow_score': trade.flow_score,
                    'flow_confidence': trade.flow_confidence,
                    'decision_source': trade.decision_source,
                    'full_metadata': trade.canonical_metadata,
                },
            }

            # Insert into forward_test_trades table
            db_trade = DBForwardTestTrade(
                trade_id=trade.id,
                session_id=session_id,
                correlation_id=session_id,  # Group by session
                symbol=trade.ticker,
                side=action,
                direction=trade.direction,
                entry_price=trade.entry_price,
                stop_loss=trade.stop_loss,
                take_profit=trade.take_profit,
                size=trade.size,
                is_pyramid=trade.is_addon,
                parent_trade_id=trade.parent_trade_id,
                # Decision snapshot
                regime=trade.entry_regime,
                probability=trade.entry_signal_prob,
                signal_strength=trade.entry_signal_prob * 100,
                adx=trade.adx,
                hurst=trade.hurst,
                atr=trade.atr,
                atr_pct=trade.atr_pct,
                rsi=trade.rsi,
                price_change_24h=trade.price_change_24h,
                volume_ratio=trade.volume_ratio,
                compression_flag=trade.compression_flag,
                breakout_flag=trade.breakout_flag,
                strategy_mode=trade.strategy_mode,
                stop_pct_used=trade.stop_pct_used,
                target_pct_used=trade.target_pct_used,
                size_multiplier=trade.size_multiplier,
                min_prob_threshold=trade.min_prob_threshold,
                min_strength_threshold=trade.min_strength_threshold,
                threshold_passed=True,
                engine_type=trade.engine_type,  # Canonical engine identification
                raw_snapshot=raw_snapshot,
                status='open',
            )
            db.add(db_trade)
            db.commit()
            db.refresh(db_trade)

            trade.db_trade_id = db_trade.id
            logger.debug(f"Persisted entry to DB: trade_id={trade.db_trade_id}, session={session_id}")

            db.close()

        except Exception as e:
            logger.error(f"Failed to persist entry to DB: {e}")

    def _persist_exit_to_db(self, trade: ForwardTestTrade):
        """Update forward_test_trades record with exit information."""
        if not DB_AVAILABLE or not SessionLocal or not DBForwardTestTrade:
            return

        if not trade.db_trade_id:
            logger.warning(f"No DB trade ID for trade {trade.id}, cannot persist exit")
            return

        try:
            db = SessionLocal()

            # Update the forward_test_trades record
            db_trade = db.query(DBForwardTestTrade).filter(
                DBForwardTestTrade.id == trade.db_trade_id
            ).first()

            if db_trade:
                db_trade.exit_price = trade.exit_price
                db_trade.exit_time = datetime.now()
                db_trade.exit_reason = trade.exit_reason
                db_trade.pnl = trade.pnl
                db_trade.pnl_pct = trade.pnl_pct
                db_trade.status = 'closed'
                db.commit()
                logger.debug(f"Updated exit in DB: trade_id={trade.db_trade_id}, pnl={trade.pnl}")
            else:
                logger.warning(f"DB trade not found: id={trade.db_trade_id}")

            db.close()

        except Exception as e:
            logger.error(f"Failed to persist exit to DB: {e}")

    def get_status(self) -> Dict:
        """Get current session status."""
        if not self.session:
            return {'active': False, 'message': 'No session started'}

        win_rate = (self.session.total_wins / self.session.total_trades * 100) if self.session.total_trades > 0 else 0

        return {
            'active': self.session.is_active,
            'session_id': self.session.session_id,
            'start_time': self.session.start_time.isoformat(),
            'capital': self.session.capital,
            'total_pnl': self.session.total_pnl,
            'total_trades': self.session.total_trades,
            'win_rate': win_rate,
            'max_drawdown': self.session.max_drawdown,
            'open_positions': len(self.session.open_trades),
            'daily_pnl': self.session.daily_pnl,
        }

    def reset_daily_stats(self):
        """Reset daily statistics (call at market open)."""
        if self.session:
            self.session.daily_pnl = 0.0
            self.session.daily_trades = 0
            self.session.daily_wins = 0
            logger.info("Daily stats reset")

    def save_snapshot_to_registry(self, strategy_id: str = "pyramid_dynamic_v1") -> bool:
        """
        Save current forward test metrics to strategy registry.

        This allows the Strategy Registry UI to show live forward test data.

        Args:
            strategy_id: The strategy_id to associate metrics with

        Returns:
            True if saved successfully, False otherwise
        """
        if not DB_AVAILABLE or not self.session:
            logger.warning("Cannot save snapshot: DB not available or no session")
            return False

        try:
            db = SessionLocal()
            try:
                # Calculate metrics
                win_rate = 0.0
                if self.session.total_trades > 0:
                    win_rate = (self.session.total_wins / self.session.total_trades) * 100

                # Calculate profit factor
                gross_profit = sum(t.pnl for t in self.session.closed_trades if t.pnl > 0)
                gross_loss = abs(sum(t.pnl for t in self.session.closed_trades if t.pnl < 0))
                profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

                # Create snapshot
                snapshot = StrategyForwardTestSnapshot(
                    strategy_id=strategy_id,
                    session_id=self.session.session_id,
                    total_trades=self.session.total_trades,
                    winning_trades=self.session.total_wins,
                    losing_trades=self.session.total_losses,
                    win_rate=win_rate,
                    max_drawdown=self.session.max_drawdown,
                    profit_factor=profit_factor,
                    total_pnl=self.session.total_pnl,
                )
                db.add(snapshot)

                # Also update the strategy's aggregate metrics
                strategy = db.query(SmartFlowStrategy).filter(
                    SmartFlowStrategy.strategy_id == strategy_id
                ).first()

                if strategy:
                    strategy.total_trades = self.session.total_trades
                    strategy.win_rate = win_rate
                    strategy.max_drawdown = self.session.max_drawdown

                db.commit()
                logger.info(f"Saved forward test snapshot for {strategy_id}: "
                           f"trades={self.session.total_trades}, win_rate={win_rate:.1f}%")
                return True

            except Exception as e:
                db.rollback()
                logger.error(f"Failed to save forward test snapshot: {e}")
                return False
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Database error saving forward test snapshot: {e}")
            return False


# Singleton instance
_forward_tester: Optional[ForwardTester] = None


def get_forward_tester() -> ForwardTester:
    """Get or create forward tester instance."""
    global _forward_tester
    if _forward_tester is None:
        _forward_tester = ForwardTester()
    return _forward_tester
