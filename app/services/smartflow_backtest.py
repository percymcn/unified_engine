"""
SmartFlow Elite Backtest Engine - 2026
========================================

Comprehensive backtesting with all SmartFlow modules:
- Regime Detection V2 (6 states, GJR-GARCH)
- Ensemble Scoring with calibration
- Advanced Risk (CVaR, slippage, position limits)
- Feature Importance tracking
- Walk-forward validation
- Monte Carlo simulation
- Shadow mode A/B testing

Usage:
    from app.services.smartflow_backtest import SmartFlowBacktester

    bt = SmartFlowBacktester()
    results = await bt.run_backtest('MES', days=90)
    bt.export_results('backtest_results.json')
"""

import asyncio
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import deque
import json
import os

logger = logging.getLogger(__name__)

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class BacktestTrade:
    """Single backtest trade."""
    entry_time: datetime
    exit_time: Optional[datetime] = None
    ticker: str = ""
    direction: str = "long"  # long/short
    entry_price: float = 0.0
    exit_price: float = 0.0
    size: float = 1.0

    # P&L
    gross_pnl: float = 0.0
    slippage_cost: float = 0.0
    commission: float = 0.0
    net_pnl: float = 0.0
    pnl_pct: float = 0.0

    # Context
    regime: str = ""
    ensemble_prob: float = 0.0
    signal_strength: float = 0.0
    flow_confirmed: bool = False
    flow_info: str = ""

    # Risk
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward: float = 0.0

    # Outcome
    is_winner: bool = False
    exit_reason: str = ""  # target, stop, timeout, signal

    # Engine attribution (Phase 2C)
    engine_type: str = "unified"  # unified, deterministic, quick, flow, ai

    # Runner strategy
    partial_exits: List[Dict] = field(default_factory=list)  # [{price, size, pnl}]
    runner_pnl: float = 0.0  # Additional P&L from runners
    scaled_in: bool = False  # Did we add to position


@dataclass
class BacktestMetrics:
    """Backtest performance metrics."""
    # Period
    start_date: str = ""
    end_date: str = ""
    trading_days: int = 0

    # Returns
    total_return_pct: float = 0.0
    cagr: float = 0.0

    # Risk-adjusted
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    # Drawdown
    max_drawdown_pct: float = 0.0
    avg_drawdown_pct: float = 0.0
    max_drawdown_duration_days: int = 0

    # Trade stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # P&L
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0

    # Trade metrics
    avg_trade: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    avg_holding_time_hours: float = 0.0

    # Regime breakdown
    regime_win_rates: Dict[str, float] = field(default_factory=dict)
    regime_pnl: Dict[str, float] = field(default_factory=dict)

    # Costs
    total_slippage: float = 0.0
    total_commission: float = 0.0

    # Flow confirmation metrics
    flow_confirmed_trades: int = 0
    flow_confirmed_win_rate: float = 0.0
    flow_unconfirmed_win_rate: float = 0.0
    flow_confirmed_pnl: float = 0.0
    flow_unconfirmed_pnl: float = 0.0

    # Monte Carlo
    mc_worst_case_dd: float = 0.0
    mc_median_return: float = 0.0
    mc_5th_percentile_return: float = 0.0


@dataclass
class WalkForwardResult:
    """Walk-forward validation result."""
    fold: int
    train_start: str
    train_end: str
    test_start: str
    test_end: str

    train_sharpe: float = 0.0
    test_sharpe: float = 0.0
    train_win_rate: float = 0.0
    test_win_rate: float = 0.0

    is_valid: bool = False  # Test Sharpe > 0.5 * Train Sharpe


@dataclass
class BacktestConfig:
    """Backtest configuration - TIGHTENED FOR GO-LIVE (2026)."""
    # Capital
    initial_capital: float = 25000.0
    position_size_pct: float = 2.0  # % of capital per trade (base)

    # Costs
    commission_per_trade: float = 2.50
    base_slippage_ticks: float = 2.0

    # Tick values
    tick_values: Dict[str, float] = field(default_factory=lambda: {
        'MES': 1.25, 'MNQ': 0.50, 'NQ': 5.0, 'ES': 12.50,
        'GC': 0.10, 'CL': 0.01, 'SPY': 0.01, 'QQQ': 0.01
    })

    # Risk - TIGHTENED
    max_positions: int = 3  # Max 3 concurrent (was unlimited in some configs)
    max_daily_loss_pct: float = 2.5  # TIGHTENED: 2.5% daily breaker (was 3%)
    max_position_pct: float = 3.5  # TIGHTENED: Max 3.5% per position (was 5%)

    # Regime-based position sizing (volatility adjustment)
    regime_size_mults: Dict[str, float] = field(default_factory=lambda: {
        'trending_up': 1.0,
        'trending_down': 1.0,
        'vol_expansion': 0.65,  # 65% size in vol expansion
        'vol_contraction': 0.9,
        'chaotic': 0.4,
        'mean_reverting': 0.8,
    })
    use_atr_stops: bool = True
    atr_stop_mult: float = 1.5
    atr_target_mult: float = 3.0

    # Percentage-based stops (alternative to ATR)
    use_pct_stops: bool = False
    pct_stop: float = 2.5  # Stop loss as % of entry price
    pct_target: float = 2.5  # Take profit as % of entry price

    # Signals
    min_ensemble_prob: float = 0.6
    min_signal_strength: float = 50.0

    # Flow confirmation
    use_flow_filter: bool = True
    require_flow_confirmation: bool = False  # If True, skip trades without flow
    flow_prob_boost: bool = True  # Apply flow probability boost

    # Runner strategy - partial profits and scaling
    # NOTE: Testing showed simple exits outperform runners due to BE stop slippage
    use_runners: bool = False  # Disabled by default - simple exits work better
    runner_partial_pct: float = 50.0  # Take 50% at first target
    runner_first_target_rr: float = 1.0  # First partial at 1:1 R:R
    runner_final_target_rr: float = 2.0  # Final exit at 1:2 R:R
    runner_move_stop_to_be: bool = True  # Move stop to breakeven after first partial
    runner_add_on_trend: bool = False  # Add contracts if trend continues (advanced)

    # Pyramid/Scaling strategy - stack positions in trend
    use_pyramid: bool = False
    pyramid_first_rr: float = 2.0  # First entry at 1:2 R:R
    pyramid_addon_rr: float = 1.0  # Scale-ins at 1:1 R:R
    pyramid_max_positions: int = 2  # Max positions to stack (conservative)
    pyramid_addon_trigger: float = 1.0  # Add when price moves 1R in our favor
    pyramid_longs_only: bool = True  # Only pyramid on longs (uptrends work better)

    # Pullback-based pyramid (smarter entries)
    pyramid_use_pullback: bool = False  # Wait for pullback before adding
    pyramid_pullback_pct: float = 0.5  # Pullback must retrace 50% of move (0.3-0.7)
    pyramid_continuation_bars: int = 2  # Bars of continuation to confirm trend resume

    # Ranging market settings (mean-reversion)
    trade_ranging: bool = False  # Enable trading in ranging markets
    ranging_pct_stop: float = 1.0  # Tighter stops for ranging (1%)
    ranging_pct_target: float = 1.0  # Quicker targets for ranging (1%)

    # ========================================
    # UPTREND TIGHTENING (2026 Enhancement)
    # ========================================
    uptrend_tightening: bool = False  # Enable stricter uptrend filters
    uptrend_min_prob: float = 0.66  # Override base 0.62 in trending_up
    uptrend_flow_require: str = 'HIGH'  # Require HIGH/EXTREME flow for uptrend longs
    uptrend_imbalance_min: float = 0.45  # Min order flow imbalance for uptrend

    # ========================================
    # VWAP/EMA21 TRAILING (2026 Enhancement)
    # ========================================
    trailing_vwap_ema: bool = False  # Enable VWAP/EMA21 trailing
    trailing_to_vwap: bool = True  # Trail to VWAP after 2x
    trailing_to_ema21: bool = True  # Also consider EMA21
    trailing_vwap_buffer_pct: float = 0.1  # 0.1% buffer below VWAP
    trailing_partial_at_3x: bool = True  # 50% exit at 3x risk
    trailing_partial_pct: float = 50.0  # Exit 50% at partial

    # ========================================
    # NEWS SENTIMENT (2026 Enhancement)
    # ========================================
    news_sentiment_enabled: bool = False  # Enable news sentiment boost
    news_boost_min: float = 0.08  # Min +8% probability boost
    news_boost_max: float = 0.12  # Max +12% probability boost
    news_sentiment_threshold: float = 0.5  # Min sentiment for boost
    news_flow_require: str = 'MEDIUM'  # Min flow for news boost

    # Walk-forward
    wf_train_days: int = 60
    wf_test_days: int = 20
    wf_folds: int = 5

    # Monte Carlo
    mc_simulations: int = 1000


class SmartFlowBacktester:
    """
    Comprehensive SmartFlow backtester with all 2026 modules.
    """

    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()

        # Results storage
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.metrics: Optional[BacktestMetrics] = None
        self.walk_forward_results: List[WalkForwardResult] = []

        # Module instances (lazy loaded)
        self._regime_detector = None
        self._ensemble_scorer = None
        self._risk_manager = None
        self._importance_tracker = None

        # Data cache
        self._price_data: Dict[str, pd.DataFrame] = {}

        logger.info(f"SmartFlowBacktester initialized with ${self.config.initial_capital} capital")

    # ========================================
    # MODULE LOADING
    # ========================================

    def _get_regime_detector(self):
        """Get or create regime detector V2."""
        if self._regime_detector is None:
            try:
                from app.services.regime_detector_v2 import RegimeDetectorV2
                self._regime_detector = RegimeDetectorV2(
                    lookback_period=100,
                    regime_ttl_minutes=15
                )
                logger.info("RegimeDetectorV2 loaded successfully")
            except ImportError as e:
                logger.warning(f"RegimeDetectorV2 not available: {e}")
                self._regime_detector = None
        return self._regime_detector

    def _get_ensemble_scorer(self):
        """Get or create ensemble scorer V2."""
        if self._ensemble_scorer is None:
            try:
                from app.services.ensemble_scorer_v2 import EnsembleScorerV2
                self._ensemble_scorer = EnsembleScorerV2()
                logger.info("EnsembleScorerV2 loaded successfully")
            except ImportError as e:
                logger.warning(f"EnsembleScorerV2 not available: {e}")
                self._ensemble_scorer = None
        return self._ensemble_scorer

    def _get_risk_manager(self):
        """Get or create risk manager."""
        if self._risk_manager is None:
            try:
                from app.services.advanced_risk import get_advanced_risk_manager
                self._risk_manager = get_advanced_risk_manager()
            except ImportError:
                logger.warning("AdvancedRiskManager not available")
                self._risk_manager = None
        return self._risk_manager

    # Regime configs for filtering - TRENDING ONLY
    SKIP_REGIMES = {'chaotic', 'vol_expansion', 'vol_contraction', 'mean_reverting'}  # Only trade clear trends
    REDUCE_SIZE_REGIMES = set()  # No half measures

    # Flow conviction levels and probability boosts - REQUIRE HIGH/EXTREME
    FLOW_CONVICTION_LEVELS = {
        'EXTREME': 0.15,  # +15% probability boost
        'HIGH': 0.12,     # +12% probability boost
        'MEDIUM': 0.0,    # No boost for medium (too weak)
        'LOW': 0.0,       # No boost
        'NEUTRAL': 0.0,   # No boost
    }

    # Ticker to ETF mapping for flow data
    TICKER_TO_ETF = {
        'MES': 'SPY', 'ES': 'SPY',
        'MNQ': 'QQQ', 'NQ': 'QQQ',
        'RTY': 'IWM', 'MYM': 'DIA',
        'GC': 'GLD', 'MGC': 'GLD',
    }

    # ========================================
    # FLOW CONFIRMATION
    # ========================================

    def _simulate_flow_conviction(
        self,
        df: pd.DataFrame,
        idx: int,
        direction: str
    ) -> Tuple[str, str, float]:
        """
        Simulate institutional options flow conviction for backtesting.

        Uses volume, price momentum, and volatility patterns to estimate
        what institutional flow might have looked like at this moment.

        Returns: (conviction_level, flow_direction, sentiment_score)
        - conviction_level: LOW, MEDIUM, HIGH, EXTREME
        - flow_direction: 'bullish', 'bearish', 'neutral'
        - sentiment_score: -100 to +100
        """
        row = df.iloc[idx]
        lookback = min(idx, 20)
        recent = df.iloc[max(0, idx - lookback):idx + 1]

        # Volume analysis (institutional flow correlates with volume spikes)
        volume_ratio = row['volume_ratio'] if 'volume_ratio' in row else 1.0
        volume_sma = recent['volume'].mean() if len(recent) > 0 else row['volume']
        volume_spike = row['volume'] / volume_sma if volume_sma > 0 else 1.0

        # Price momentum (strong moves attract institutional flow)
        returns_5 = (row['close'] / recent['close'].iloc[0] - 1) * 100 if len(recent) >= 5 else 0
        returns_10 = (row['close'] / df.iloc[max(0, idx-10)]['close'] - 1) * 100 if idx >= 10 else 0

        # Volatility (institutions trade more actively in volatile conditions)
        bb_width = row.get('bb_width', 0.03)
        atr_pct = row['atr'] / row['close'] * 100 if row['close'] > 0 else 0

        # RSI extremes (mean reversion flow)
        rsi = row['rsi']
        rsi_extreme = abs(rsi - 50) / 50  # 0 to 1, higher = more extreme

        # Calculate flow sentiment score (-100 to +100)
        sentiment_score = 0.0

        # Volume contribution (+/- 30 points)
        if volume_spike > 2.0:
            volume_contribution = min(30, (volume_spike - 1) * 15)
        else:
            volume_contribution = (volume_spike - 1) * 15

        # Direction based on price action
        if returns_5 > 0.5:
            sentiment_score += volume_contribution  # Bullish with volume
        elif returns_5 < -0.5:
            sentiment_score -= volume_contribution  # Bearish with volume

        # Momentum contribution (+/- 40 points)
        momentum_score = min(40, max(-40, returns_10 * 10))
        sentiment_score += momentum_score

        # RSI extremes suggest reversal flow (+/- 20 points)
        if rsi > 70:
            sentiment_score -= rsi_extreme * 20  # Bearish put flow
        elif rsi < 30:
            sentiment_score += rsi_extreme * 20  # Bullish call flow

        # MACD confirmation (+/- 10 points)
        macd_hist = row.get('macd_hist', 0)
        if macd_hist > 0:
            sentiment_score += min(10, macd_hist * 5)
        else:
            sentiment_score += max(-10, macd_hist * 5)

        # Clamp to -100 to +100
        sentiment_score = max(-100, min(100, sentiment_score))

        # Determine flow direction
        if sentiment_score > 20:
            flow_direction = 'bullish'
        elif sentiment_score < -20:
            flow_direction = 'bearish'
        else:
            flow_direction = 'neutral'

        # Determine conviction level based on sentiment strength and volume
        abs_score = abs(sentiment_score)

        if abs_score >= 70 and volume_spike >= 2.5:
            conviction = 'EXTREME'
        elif abs_score >= 50 and volume_spike >= 1.8:
            conviction = 'HIGH'
        elif abs_score >= 30 and volume_spike >= 1.3:
            conviction = 'MEDIUM'
        elif abs_score >= 15:
            conviction = 'LOW'
        else:
            conviction = 'NEUTRAL'

        return conviction, flow_direction, sentiment_score

    def _check_flow_confirmation(
        self,
        df: pd.DataFrame,
        idx: int,
        direction: str
    ) -> Tuple[bool, float, str]:
        """
        Check if flow confirms the trade direction.

        Strategy: Use flow as a FILTER - skip trades when strong flow
        goes against our direction. This avoids chasing momentum that's
        about to reverse.

        Returns: (is_confirmed, probability_boost, flow_info)
        """
        conviction, flow_direction, sentiment_score = self._simulate_flow_conviction(
            df, idx, direction
        )

        # Check if flow direction matches trade direction
        direction_matches = (
            (direction == 'long' and flow_direction == 'bullish') or
            (direction == 'short' and flow_direction == 'bearish')
        )

        # Check if flow is AGAINST our direction (danger signal)
        direction_opposes = (
            (direction == 'long' and flow_direction == 'bearish') or
            (direction == 'short' and flow_direction == 'bullish')
        )

        # Flow confirmation logic:
        # 1. If flow strongly opposes our direction -> NOT confirmed (skip this trade)
        # 2. If flow is neutral -> confirmed (okay to trade)
        # 3. If flow supports our direction -> confirmed with boost

        prob_boost = 0.0

        if direction_opposes and conviction in ['HIGH', 'EXTREME']:
            # Strong opposing flow - DON'T take this trade
            is_confirmed = False
            prob_boost = -0.20  # Negative boost signals rejection
        elif direction_opposes and conviction == 'MEDIUM':
            # Moderate opposing flow - caution
            is_confirmed = True  # Allow but no boost
            prob_boost = 0.0
        elif direction_matches and conviction in ['HIGH', 'EXTREME']:
            # Strong confirming flow - boost probability
            is_confirmed = True
            prob_boost = self.FLOW_CONVICTION_LEVELS.get(conviction, 0.0)
        elif direction_matches and conviction == 'MEDIUM':
            # Moderate confirming flow - no boost, just allow
            is_confirmed = True
            prob_boost = 0.0
        else:
            # Neutral or low conviction - okay to trade but no boost
            is_confirmed = True
            prob_boost = 0.0

        flow_info = f"{conviction}_{flow_direction}_score={sentiment_score:.0f}"

        return is_confirmed, prob_boost, flow_info

    # ========================================
    # DATA FETCHING
    # ========================================

    async def fetch_data(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = "1h"
    ) -> pd.DataFrame:
        """Fetch historical data from Polygon."""
        import httpx

        api_key = os.getenv("POLYGON_API_KEY", "")
        if not api_key:
            logger.warning("No POLYGON_API_KEY, using synthetic data")
            return self._generate_synthetic_data(ticker, start_date, end_date)

        # Map futures to ETF equivalents for data
        ticker_map = {
            'MES': 'SPY', 'ES': 'SPY', 'NQ': 'QQQ', 'MNQ': 'QQQ',
            'RTY': 'IWM', 'MYM': 'DIA', 'GC': 'GLD', 'MGC': 'GLD'
        }
        poly_ticker = ticker_map.get(ticker, ticker)

        # Polygon timeframe mapping
        tf_map = {
            '1m': ('minute', 1), '5m': ('minute', 5), '15m': ('minute', 15),
            '1h': ('hour', 1), '4h': ('hour', 4), '1d': ('day', 1)
        }
        unit, mult = tf_map.get(timeframe, ('hour', 1))

        url = (
            f"https://api.polygon.io/v2/aggs/ticker/{poly_ticker}/range/"
            f"{mult}/{unit}/{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
            f"?apiKey={api_key}&limit=50000"
        )

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=30)
                data = resp.json()

            if 'results' not in data:
                logger.warning(f"No data from Polygon for {ticker}")
                return self._generate_synthetic_data(ticker, start_date, end_date)

            df = pd.DataFrame(data['results'])
            df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
            df = df.rename(columns={
                'o': 'open', 'h': 'high', 'l': 'low',
                'c': 'close', 'v': 'volume'
            })
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            df = df.set_index('timestamp').sort_index()

            logger.info(f"Fetched {len(df)} bars for {ticker}")
            return df

        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return self._generate_synthetic_data(ticker, start_date, end_date)

    def _generate_synthetic_data(
        self,
        ticker: str,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Generate synthetic price data for testing."""
        periods = int((end_date - start_date).total_seconds() / 3600)  # Hourly

        # Base price by ticker (futures and CFDs)
        base_prices = {
            'MES': 5000, 'ES': 5000, 'SPY': 500, 'SPX500': 5000, 'US500': 5000,
            'NQ': 18000, 'MNQ': 18000, 'QQQ': 430, 'NAS100': 18000,
            'YM': 40000, 'MYM': 40000, 'DIA': 400, 'US30': 40000,
            'GC': 2000, 'GLD': 200, 'IWM': 200
        }
        base = base_prices.get(ticker, 5000)

        # Generate random walk with drift
        np.random.seed(42)
        returns = np.random.normal(0.0002, 0.005, periods)
        prices = base * np.exp(np.cumsum(returns))

        timestamps = pd.date_range(start_date, end_date, periods=periods)

        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices * (1 + np.random.normal(0, 0.001, periods)),
            'high': prices * (1 + np.abs(np.random.normal(0.002, 0.003, periods))),
            'low': prices * (1 - np.abs(np.random.normal(0.002, 0.003, periods))),
            'close': prices,
            'volume': np.random.randint(1000, 10000, periods)
        })

        df = df.set_index('timestamp').sort_index()
        return df

    # ========================================
    # SIGNAL GENERATION
    # ========================================

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators."""
        df = df.copy()

        # EMAs
        df['ema9'] = df['close'].ewm(span=9).mean()
        df['ema21'] = df['close'].ewm(span=21).mean()

        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + 2 * bb_std
        df['bb_lower'] = df['bb_middle'] - 2 * bb_std
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']

        # ATR
        tr = pd.concat([
            df['high'] - df['low'],
            (df['high'] - df['close'].shift()).abs(),
            (df['low'] - df['close'].shift()).abs()
        ], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()

        # Volume
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']

        # ADX
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr_smooth = tr.rolling(14).sum()
        plus_di = 100 * (plus_dm.rolling(14).sum() / tr_smooth)
        minus_di = 100 * (minus_dm.rolling(14).sum() / tr_smooth)
        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
        df['adx'] = dx.rolling(14).mean()

        return df.dropna()

    def _detect_regime(self, df: pd.DataFrame, idx: int) -> Tuple[str, float, dict]:
        """
        Detect market regime at given index using RegimeDetectorV2.

        Returns: (regime_name, confidence, regime_config_dict)
        """
        detector = self._get_regime_detector()
        row = df.iloc[idx]

        # Build regime config dict for adaptive parameters
        regime_config = {
            'stop_mult': 1.5,
            'target_mult': 3.0,
            'min_rr': 2.0,
            'confidence_boost': 0.0,
            'size_mult': 1.0,
            'allow_long': True,
            'allow_short': True,
        }

        # Try full detector first
        if detector is not None:
            try:
                lookback = df.iloc[max(0, idx-100):idx+1]
                result = detector.analyze(
                    ticker="MES",
                    closes=lookback['close'].values,
                    highs=lookback['high'].values,
                    lows=lookback['low'].values,
                    volumes=lookback['volume'].values
                )

                if result and hasattr(result, 'primary_regime'):
                    regime = result.primary_regime.value if hasattr(result.primary_regime, 'value') else str(result.primary_regime)
                    conf = result.classification_confidence / 100.0

                    # Apply regime config
                    if hasattr(result, 'regime_config'):
                        rc = result.regime_config
                        regime_config = {
                            'stop_mult': rc.stop_multiplier,
                            'target_mult': rc.target_multiplier,
                            'min_rr': rc.min_rr,
                            'confidence_boost': rc.confidence_boost,
                            'size_mult': rc.size_multiplier,
                            'allow_long': rc.allow_long,
                            'allow_short': rc.allow_short,
                        }

                    return regime, conf, regime_config
            except Exception as e:
                logger.debug(f"RegimeDetectorV2 error: {e}")

        # Fallback: Enhanced basic regime detection
        adx = row['adx']
        rsi = row['rsi']
        bb_width = row['bb_width']
        bb_position = row['bb_position']
        volume_ratio = row['volume_ratio']
        macd_hist = row['macd_hist']
        ema_bullish = row['close'] > row['ema9'] > row['ema21']
        ema_bearish = row['close'] < row['ema9'] < row['ema21']

        # Enhanced regime classification - BALANCED R:R
        if adx > 30:  # Strong trend
            if ema_bullish and macd_hist > 0:
                # Trending up: good R:R but achievable targets
                regime_config.update({
                    'stop_mult': 1.5,
                    'target_mult': 3.5,  # Achievable target
                    'min_rr': 2.0,
                    'confidence_boost': 10,
                    'size_mult': 1.2,
                    'allow_short': False
                })
                return 'trending_up', 0.75, regime_config
            elif ema_bearish and macd_hist < 0:
                # Trending down: tighter target for shorts
                regime_config.update({
                    'stop_mult': 1.5,
                    'target_mult': 3.0,  # Tighter for shorts (faster wins)
                    'min_rr': 1.8,
                    'confidence_boost': 5,
                    'size_mult': 1.0,
                    'allow_long': False
                })
                return 'trending_down', 0.70, regime_config
        elif adx > 25:  # Moderate trend
            if ema_bullish:
                regime_config.update({
                    'stop_mult': 1.5,
                    'target_mult': 3.0,
                    'min_rr': 1.8,
                    'confidence_boost': 5,
                    'size_mult': 1.0,
                    'allow_short': False
                })
                return 'trending_up', 0.70, regime_config
            elif ema_bearish:
                regime_config.update({
                    'stop_mult': 1.5,
                    'target_mult': 2.5,
                    'min_rr': 1.5,
                    'confidence_boost': 0,
                    'size_mult': 0.8,
                    'allow_long': False
                })
                return 'trending_down', 0.65, regime_config

        if bb_width < 0.025:  # Tight squeeze
            regime_config.update({'target_mult': 4.0, 'min_rr': 3.0, 'size_mult': 1.0})
            return 'vol_contraction', 0.65, regime_config

        if bb_width > 0.06 or (adx > 20 and volume_ratio > 2.0):  # Vol expansion
            regime_config.update({'stop_mult': 2.5, 'confidence_boost': -10, 'size_mult': 0.5})
            return 'vol_expansion', 0.6, regime_config

        if adx < 20 and 0.3 < bb_position < 0.7:  # Range-bound
            regime_config.update({'target_mult': 2.0, 'min_rr': 1.5, 'confidence_boost': -5, 'size_mult': 0.75})
            return 'mean_reverting', 0.55, regime_config

        # Unclear - chaotic
        regime_config.update({'confidence_boost': -20, 'size_mult': 0.25})
        return 'chaotic', 0.4, regime_config

    def _generate_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        regime: str,
        regime_config: dict
    ) -> Tuple[Optional[str], float, float]:
        """
        Generate trading signal with regime-aware filtering.

        Returns: (direction, probability, strength)
        """
        row = df.iloc[idx]

        # Check if regime allows trading
        skip_regimes = self.SKIP_REGIMES.copy()
        if self.config.trade_ranging and 'mean_reverting' in skip_regimes:
            skip_regimes.remove('mean_reverting')  # Allow ranging trades

        if regime in skip_regimes:
            return None, 0.5, 0.0

        # Feature vector
        ema_bullish = row['close'] > row['ema9'] > row['ema21']
        ema_bearish = row['close'] < row['ema9'] < row['ema21']
        rsi = row['rsi']
        macd_hist = row['macd_hist']
        bb_position = row['bb_position']
        volume_ratio = row['volume_ratio']
        adx = row['adx']

        # Enhanced scoring with regime adjustments
        score = 0.0
        confidence_boost = regime_config.get('confidence_boost', 0)

        # === BULLISH SIGNALS ===
        if ema_bullish:
            score += 2.5
        if macd_hist > 0:
            score += 1.5
        if 45 < rsi < 65:  # Healthy bullish RSI
            score += 1.0
        elif rsi < 35:  # Oversold bounce
            score += 1.5
        if bb_position < 0.25:  # Near lower band (reversal)
            score += 1.0

        # === BEARISH SIGNALS ===
        if ema_bearish:
            score -= 2.5
        if macd_hist < 0:
            score -= 1.5
        if 35 < rsi < 55:  # Healthy bearish RSI
            score -= 1.0
        elif rsi > 65:  # Overbought fade
            score -= 1.5
        if bb_position > 0.75:  # Near upper band (reversal)
            score -= 1.0

        # === TREND STRENGTH ===
        if adx > 25:  # Strong trend
            score *= 1.25
        elif adx < 15:  # Weak/no trend
            score *= 0.8

        # === VOLUME CONFIRMATION ===
        if volume_ratio > 1.5:
            score *= 1.15
        elif volume_ratio > 2.0:
            score *= 1.25

        # === REGIME ADJUSTMENTS ===
        if regime == 'trending_up':
            if score > 0:
                score *= 1.4  # Boost long signals
            else:
                score *= 0.5  # Suppress short signals
        elif regime == 'trending_down':
            if score < 0:
                score *= 1.4  # Boost short signals
            else:
                score *= 0.5  # Suppress long signals
        elif regime == 'mean_reverting':
            # Fade extremes
            if bb_position < 0.15:
                score += 1.5  # Buy oversold
            elif bb_position > 0.85:
                score -= 1.5  # Sell overbought
        elif regime == 'vol_contraction':
            # Breakout setup - need strong move
            if abs(score) < 3:
                score *= 0.7  # Wait for stronger signal

        # Convert to probability and direction
        prob = 1 / (1 + np.exp(-score / 4))  # Sigmoid

        # Apply regime confidence boost
        prob = min(1.0, max(0.0, prob + confidence_boost / 100))

        # Calculate strength
        strength = abs(score) * 12

        # Direction filtering based on regime
        allow_long = regime_config.get('allow_long', True)
        allow_short = regime_config.get('allow_short', True)

        # Generate signal with higher thresholds
        min_prob = self.config.min_ensemble_prob
        min_strength = self.config.min_signal_strength

        # UPTREND TIGHTENING: Override probability threshold for trending_up regime
        if self.config.uptrend_tightening and regime == 'trending_up':
            min_prob = self.config.uptrend_min_prob  # 0.66 vs 0.62 base

        if score > 2.5 and prob > min_prob and strength >= min_strength:
            if allow_long:
                return 'long', prob, strength
        elif score < -2.5 and (1 - prob) > min_prob and strength >= min_strength:
            if allow_short:
                return 'short', 1 - prob, strength

        return None, prob, strength

    # ========================================
    # DETERMINISTIC SIGNAL GENERATION (Phase 2C)
    # ========================================

    def _resample_to_timeframes(
        self,
        df: pd.DataFrame,
        current_idx: int
    ) -> Dict[str, pd.DataFrame]:
        """
        Resample historical data to multiple timeframes for MTF analysis.

        Args:
            df: Main dataframe (5m bars)
            current_idx: Current bar index

        Returns:
            Dict mapping timeframe ('5m', '15m', etc.) to resampled DataFrame
        """
        # Get historical data up to current point
        hist = df.iloc[:current_idx + 1].copy()

        if len(hist) < 100:  # Need enough history
            return {}

        bars_by_tf = {}

        # 5m is already our base timeframe
        bars_by_tf['5m'] = hist.tail(200)  # Keep last 200 bars

        # Resample to higher timeframes
        try:
            # 15m
            df_15m = hist.resample('15min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            if len(df_15m) >= 100:
                bars_by_tf['15m'] = df_15m.tail(150)

            # 30m
            df_30m = hist.resample('30min').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            if len(df_30m) >= 100:
                bars_by_tf['30m'] = df_30m.tail(100)

            # 1h
            df_1h = hist.resample('1h').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            if len(df_1h) >= 100:
                bars_by_tf['1h'] = df_1h.tail(100)

            # 4h
            df_4h = hist.resample('4h').agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            if len(df_4h) >= 50:
                bars_by_tf['4h'] = df_4h.tail(75)

        except Exception as e:
            logger.warning(f"Failed to resample timeframes: {e}")

        return bars_by_tf

    def _generate_deterministic_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        ticker: str
    ) -> Tuple[Optional[str], float, float, Optional[Dict]]:
        """
        Generate signal using Deterministic multi-timeframe indicator engine.

        Returns: (direction, probability, strength, mtf_signal_data)
        """
        try:
            # Import indicator engine
            from app.services.indicators import get_indicator_engine, IndicatorConfig

            # Create config with Deterministic parameters
            indicator_config = IndicatorConfig(
                min_aligned_timeframes=4,
                require_higher_tf_agreement=True,
                min_confidence_score=75.0,
                min_risk_reward=2.0
            )

            indicator_engine = get_indicator_engine(indicator_config)

            # Resample to multiple timeframes
            bars_by_tf = self._resample_to_timeframes(df, idx)

            if len(bars_by_tf) < 3:
                logger.debug(f"Insufficient timeframes: {len(bars_by_tf)}/5")
                return None, 0.5, 0.0, None

            # Run multi-timeframe analysis
            mtf_signal = indicator_engine.analyze_multi_timeframe(ticker, bars_by_tf)

            if not mtf_signal.should_trade:
                return None, mtf_signal.confidence_score / 100, 0.0, None

            # Convert to backtest format
            direction = 'long' if mtf_signal.action == 'buy' else 'short' if mtf_signal.action == 'sell' else None
            probability = mtf_signal.confidence_score / 100  # Convert 0-100 to 0-1
            strength = mtf_signal.confidence_score  # Use confidence as strength

            # Package MTF signal data for trade context
            mtf_data = {
                'aligned_tfs': mtf_signal.aligned_bullish if mtf_signal.overall_bias == 'bullish' else mtf_signal.aligned_bearish,
                'confidence': mtf_signal.confidence_score,
                'risk_reward': mtf_signal.risk_reward_ratio,
                'stop_loss': mtf_signal.stop_loss,
                'take_profit': mtf_signal.take_profit,
                'entry_price': mtf_signal.entry_price,
                'overall_bias': mtf_signal.overall_bias
            }

            return direction, probability, strength, mtf_data

        except ImportError as e:
            logger.warning(f"Deterministic indicators not available: {e}")
            return None, 0.5, 0.0, None
        except Exception as e:
            logger.error(f"Error generating deterministic signal: {e}")
            return None, 0.5, 0.0, None

    # ========================================
    # TRADE EXECUTION
    # ========================================

    def _calculate_position_size(
        self,
        ticker: str,
        entry_price: float,
        stop_price: float,
        capital: float
    ) -> float:
        """Calculate position size with risk management for micro futures."""
        # Point multipliers - futures and CFDs
        point_multipliers = {
            'MES': 5.0, 'ES': 50.0, 'MNQ': 2.0, 'NQ': 20.0,
            'MYM': 0.50, 'YM': 5.0, 'RTY': 5.0, 'GC': 10.0,
            'SPY': 1.0, 'QQQ': 1.0, 'DIA': 1.0,
            # CFDs - $1 per point
            'US30': 1.0, 'NAS100': 1.0, 'SPX500': 1.0, 'US500': 1.0,
        }
        multiplier = point_multipliers.get(ticker, 1.0)

        risk_per_trade = capital * (self.config.position_size_pct / 100)
        stop_distance = abs(entry_price - stop_price)

        if stop_distance == 0:
            return 1.0

        # Risk per contract = stop distance × point multiplier
        risk_per_contract = stop_distance * multiplier

        # Position size = total risk / risk per contract
        raw_size = risk_per_trade / risk_per_contract

        # Cap at reasonable size for micro futures (1-5 contracts typically)
        max_contracts = min(5, int(capital / 5000))  # ~1 contract per $5k
        raw_size = min(raw_size, max_contracts)

        return max(1.0, round(raw_size))

    def _calculate_slippage(
        self,
        ticker: str,
        entry_price: float,
        size: float,
        atr: float
    ) -> float:
        """Calculate realistic slippage for micro futures."""
        # Realistic slippage for micro futures:
        # MES: ~1-2 ticks × $1.25/tick = $1.25-2.50 per contract
        # MNQ: ~1-2 ticks × $0.50/tick = $0.50-1.00 per contract

        tick_value = self.config.tick_values.get(ticker, 1.25)

        # Base slippage: 1.5 ticks average (entry + exit)
        base_ticks = 1.5

        # Slight volatility adjustment (capped)
        vol_mult = min(1.5, 1.0 + (atr / entry_price) * 5)

        slippage_ticks = base_ticks * vol_mult
        return slippage_ticks * tick_value * size

    def _calculate_atr(
        self,
        df: pd.DataFrame,
        idx: int,
        window: int = 14
    ) -> float:
        """
        Calculate ATR (Average True Range) at a specific index.

        Args:
            df: DataFrame with OHLC data
            idx: Current bar index
            window: ATR lookback period

        Returns:
            ATR value
        """
        if idx < window:
            # Not enough data, use simple range
            return (df.iloc[idx]['high'] - df.iloc[idx]['low'])

        # Get relevant slice
        start_idx = max(0, idx - window)
        slice_df = df.iloc[start_idx:idx + 1]

        # Calculate True Range
        high = slice_df['high'].values
        low = slice_df['low'].values
        close = slice_df['close'].values

        # TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])

        true_range = np.maximum(np.maximum(tr1, tr2), tr3)

        # ATR is the average of True Range
        atr = np.mean(true_range[-window:]) if len(true_range) >= window else np.mean(true_range)

        return float(atr) if not np.isnan(atr) else (df.iloc[idx]['high'] - df.iloc[idx]['low'])

    def _execute_trade(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        direction: str,
        regime: str,
        regime_config: dict,
        prob: float,
        strength: float,
        capital: float,
        ticker: str = 'MES'
    ) -> Optional[BacktestTrade]:
        """Execute a trade with regime-adaptive R:R."""
        entry_row = df.iloc[entry_idx]
        entry_price = entry_row['close']
        atr = entry_row['atr']

        # Get regime-adaptive multipliers
        stop_mult = regime_config.get('stop_mult', self.config.atr_stop_mult)
        target_mult = regime_config.get('target_mult', self.config.atr_target_mult)
        size_mult = regime_config.get('size_mult', 1.0)

        # Calculate stops - percentage-based or ATR-based
        # Use tighter stops for ranging/mean-reverting markets
        use_ranging_stops = self.config.trade_ranging and regime == 'mean_reverting'

        if self.config.use_pct_stops:
            # Percentage-based stops
            if use_ranging_stops:
                pct_stop = self.config.ranging_pct_stop / 100.0
                pct_target = self.config.ranging_pct_target / 100.0
            else:
                pct_stop = self.config.pct_stop / 100.0
                pct_target = self.config.pct_target / 100.0
            if direction == 'long':
                stop_loss = entry_price * (1 - pct_stop)
                take_profit = entry_price * (1 + pct_target)
            else:
                stop_loss = entry_price * (1 + pct_stop)
                take_profit = entry_price * (1 - pct_target)
        else:
            # ATR-based stops with regime-adaptive R:R
            if direction == 'long':
                stop_loss = entry_price - atr * stop_mult
                take_profit = entry_price + atr * target_mult
            else:
                stop_loss = entry_price + atr * stop_mult
                take_profit = entry_price - atr * target_mult

        risk_reward = abs(take_profit - entry_price) / abs(entry_price - stop_loss)

        # Check minimum R:R requirement (skip for percentage-based stops as user sets the R:R)
        if not self.config.use_pct_stops:
            min_rr = regime_config.get('min_rr', 2.0)
            if risk_reward < min_rr:
                return None  # Skip trades that don't meet min R:R

        # Position size (with regime size multiplier)
        size = self._calculate_position_size(ticker, entry_price, stop_loss, capital)
        size = max(1, int(size * size_mult))

        # Entry slippage
        entry_slippage = self._calculate_slippage(ticker, entry_price, size, atr)

        # Create trade
        trade = BacktestTrade(
            entry_time=entry_row.name,
            ticker=ticker,
            direction=direction,
            entry_price=entry_price,
            size=size,
            regime=regime,
            ensemble_prob=prob,
            signal_strength=strength,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward,
            slippage_cost=entry_slippage,
            commission=self.config.commission_per_trade
        )

        # Simulate until exit
        max_bars = 50  # Max holding time

        for i in range(entry_idx + 1, min(entry_idx + max_bars, len(df))):
            bar = df.iloc[i]

            if direction == 'long':
                # Check stop
                if bar['low'] <= stop_loss:
                    trade.exit_price = stop_loss
                    trade.exit_reason = 'stop'
                    trade.is_winner = False
                    break
                # Check target
                elif bar['high'] >= take_profit:
                    trade.exit_price = take_profit
                    trade.exit_reason = 'target'
                    trade.is_winner = True
                    break
            else:  # short
                if bar['high'] >= stop_loss:
                    trade.exit_price = stop_loss
                    trade.exit_reason = 'stop'
                    trade.is_winner = False
                    break
                elif bar['low'] <= take_profit:
                    trade.exit_price = take_profit
                    trade.exit_reason = 'target'
                    trade.is_winner = True
                    break

            trade.exit_time = bar.name
            trade.exit_price = bar['close']

        # If no exit, close at last bar
        if trade.exit_time is None:
            trade.exit_time = df.iloc[-1].name
            trade.exit_price = df.iloc[-1]['close']
            trade.exit_reason = 'timeout'

        # Calculate P&L
        exit_slippage = self._calculate_slippage(
            ticker, trade.exit_price, size, atr
        )
        trade.slippage_cost += exit_slippage

        # Point multipliers for futures and CFDs
        point_multipliers = {
            'MES': 5.0, 'ES': 50.0, 'MNQ': 2.0, 'NQ': 20.0,
            'MYM': 0.50, 'YM': 5.0, 'RTY': 5.0, 'GC': 10.0,
            'SPY': 1.0, 'QQQ': 1.0, 'DIA': 1.0,
            'US30': 1.0, 'NAS100': 1.0, 'SPX500': 1.0, 'US500': 1.0,
        }
        multiplier = point_multipliers.get(ticker, 1.0)

        if direction == 'long':
            trade.gross_pnl = (trade.exit_price - entry_price) * size * multiplier
        else:
            trade.gross_pnl = (entry_price - trade.exit_price) * size * multiplier

        trade.net_pnl = trade.gross_pnl - trade.slippage_cost - trade.commission
        trade.pnl_pct = trade.net_pnl / capital * 100
        trade.is_winner = trade.net_pnl > 0

        return trade

    def _execute_trade_with_pyramid(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        direction: str,
        regime: str,
        regime_config: dict,
        prob: float,
        strength: float,
        capital: float,
        ticker: str = 'MES'
    ) -> Optional[BacktestTrade]:
        """
        Execute a trade with pyramid/scaling strategy:
        - First entry at 1:2 R:R
        - Add positions at 1:1 R:R as trend continues
        - NO breakeven - each position keeps its own SL
        - Take profits quickly on each position
        """
        entry_row = df.iloc[entry_idx]
        entry_price = entry_row['close']
        atr = entry_row['atr']

        # Get stop distance - percentage-based or ATR-based
        if self.config.use_pct_stops:
            pct_stop = self.config.pct_stop / 100.0
            stop_distance = entry_price * pct_stop
        else:
            stop_mult = regime_config.get('stop_mult', self.config.atr_stop_mult)
            stop_distance = atr * stop_mult

        # Point multiplier - futures and CFDs
        point_multipliers = {
            'MES': 5.0, 'ES': 50.0, 'MNQ': 2.0, 'NQ': 20.0,
            'MYM': 0.50, 'YM': 5.0, 'RTY': 5.0, 'GC': 10.0,
            'SPY': 1.0, 'QQQ': 1.0, 'DIA': 1.0,
            'US30': 1.0, 'NAS100': 1.0, 'SPX500': 1.0, 'US500': 1.0,
        }
        multiplier = point_multipliers.get(ticker, 1.0)

        # Position tracking - each position is independent
        # Format: {id: {entry, stop, target, size, active, pnl}}
        positions = {}
        position_id = 0
        total_gross_pnl = 0.0
        total_slippage = 0.0
        total_commission = 0.0
        wins = 0
        losses = 0

        # Calculate size per position
        size_mult = regime_config.get('size_mult', 1.0)
        base_size = self._calculate_position_size(ticker, entry_price,
                                                   entry_price - stop_distance if direction == 'long' else entry_price + stop_distance,
                                                   capital)
        base_size = max(1, int(base_size * size_mult))

        # First position R:R calculation
        if self.config.use_pct_stops:
            # Percentage-based: use pct_target for the target distance
            pct_target = self.config.pct_target / 100.0
            target_distance = entry_price * pct_target
        else:
            # ATR-based: use pyramid_first_rr multiplier
            target_distance = stop_distance * self.config.pyramid_first_rr

        # First position - set stops and targets
        if direction == 'long':
            p1_stop = entry_price - stop_distance
            p1_target = entry_price + target_distance
        else:
            p1_stop = entry_price + stop_distance
            p1_target = entry_price - target_distance

        positions[position_id] = {
            'entry': entry_price,
            'stop': p1_stop,
            'target': p1_target,
            'size': base_size,
            'active': True,
            'rr': self.config.pyramid_first_rr,
            'entry_bar': entry_idx,
        }
        position_id += 1
        total_slippage += self._calculate_slippage(ticker, entry_price, base_size, atr)
        total_commission += self.config.commission_per_trade

        # Track add-on triggers
        addon_trigger_distance = stop_distance * self.config.pyramid_addon_trigger
        last_addon_price = entry_price
        addon_count = 1  # First position counts

        # Pullback tracking for smarter add-ons
        swing_extreme = entry_price
        pullback_low = entry_price
        pullback_high = entry_price
        in_pullback = False
        continuation_count = 0

        # Track for trade record
        all_exits = []
        trade_exit_time = None
        trade_exit_price = entry_price

        # Simulate bar by bar
        max_bars = 80  # More bars to allow for pullback patterns

        for i in range(entry_idx + 1, min(entry_idx + max_bars, len(df))):
            bar = df.iloc[i]
            high, low, close = bar['high'], bar['low'], bar['close']
            current_atr = bar['atr']

            # Check each active position
            for pid, pos in list(positions.items()):
                if not pos['active']:
                    continue

                if direction == 'long':
                    # Check stop
                    if low <= pos['stop']:
                        pnl = (pos['stop'] - pos['entry']) * pos['size'] * multiplier
                        total_gross_pnl += pnl
                        total_slippage += self._calculate_slippage(ticker, pos['stop'], pos['size'], current_atr)
                        pos['active'] = False
                        pos['exit_price'] = pos['stop']
                        pos['pnl'] = pnl
                        losses += 1
                        all_exits.append({'price': pos['stop'], 'pnl': pnl, 'reason': 'stop', 'rr': pos['rr']})

                    # Check target - TAKE PROFIT QUICKLY
                    elif high >= pos['target']:
                        pnl = (pos['target'] - pos['entry']) * pos['size'] * multiplier
                        total_gross_pnl += pnl
                        total_slippage += self._calculate_slippage(ticker, pos['target'], pos['size'], current_atr)
                        pos['active'] = False
                        pos['exit_price'] = pos['target']
                        pos['pnl'] = pnl
                        wins += 1
                        all_exits.append({'price': pos['target'], 'pnl': pnl, 'reason': 'target', 'rr': pos['rr']})

                else:  # short
                    # Check stop
                    if high >= pos['stop']:
                        pnl = (pos['entry'] - pos['stop']) * pos['size'] * multiplier
                        total_gross_pnl += pnl
                        total_slippage += self._calculate_slippage(ticker, pos['stop'], pos['size'], current_atr)
                        pos['active'] = False
                        pos['exit_price'] = pos['stop']
                        pos['pnl'] = pnl
                        losses += 1
                        all_exits.append({'price': pos['stop'], 'pnl': pnl, 'reason': 'stop', 'rr': pos['rr']})

                    # Check target
                    elif low <= pos['target']:
                        pnl = (pos['entry'] - pos['target']) * pos['size'] * multiplier
                        total_gross_pnl += pnl
                        total_slippage += self._calculate_slippage(ticker, pos['target'], pos['size'], current_atr)
                        pos['active'] = False
                        pos['exit_price'] = pos['target']
                        pos['pnl'] = pnl
                        wins += 1
                        all_exits.append({'price': pos['target'], 'pnl': pnl, 'reason': 'target', 'rr': pos['rr']})

            # Check for add-on opportunity
            if addon_count < self.config.pyramid_max_positions:
                # Calculate stop/target distances for add-on at current price
                if self.config.use_pct_stops:
                    addon_stop_dist = close * (self.config.pct_stop / 100.0)
                    addon_target_dist = close * (self.config.pct_target / 100.0)
                else:
                    addon_stop_dist = stop_distance
                    addon_target_dist = stop_distance * self.config.pyramid_addon_rr

                should_add = False

                if self.config.pyramid_use_pullback:
                    # PULLBACK-BASED ADD-ON: Wait for pullback then trend continuation
                    if direction == 'long':
                        # Update swing high
                        if high > swing_extreme:
                            swing_extreme = high
                            in_pullback = False
                            continuation_count = 0

                        # Check for pullback (price dropped from swing high)
                        move_size = swing_extreme - last_addon_price
                        pullback_size = swing_extreme - low
                        if move_size > 0 and pullback_size / move_size >= self.config.pyramid_pullback_pct:
                            in_pullback = True
                            pullback_low = min(pullback_low, low)

                        # Check for continuation after pullback
                        if in_pullback and close > pullback_low:
                            if close > df.iloc[i-1]['close']:  # Higher close
                                continuation_count += 1
                            else:
                                continuation_count = 0

                            # Add when we have enough continuation bars
                            if continuation_count >= self.config.pyramid_continuation_bars:
                                should_add = True
                                swing_extreme = close  # Reset for next add-on
                                pullback_low = close
                                in_pullback = False
                                continuation_count = 0

                    else:  # short
                        # Update swing low
                        if low < swing_extreme:
                            swing_extreme = low
                            in_pullback = False
                            continuation_count = 0

                        # Check for pullback (price rose from swing low)
                        move_size = last_addon_price - swing_extreme
                        pullback_size = high - swing_extreme
                        if move_size > 0 and pullback_size / move_size >= self.config.pyramid_pullback_pct:
                            in_pullback = True
                            pullback_high = max(pullback_high, high)

                        # Check for continuation after pullback
                        if in_pullback and close < pullback_high:
                            if close < df.iloc[i-1]['close']:  # Lower close
                                continuation_count += 1
                            else:
                                continuation_count = 0

                            # Add when we have enough continuation bars
                            if continuation_count >= self.config.pyramid_continuation_bars:
                                should_add = True
                                swing_extreme = close
                                pullback_high = close
                                in_pullback = False
                                continuation_count = 0
                else:
                    # ORIGINAL: Add when price moves 1R in our favor
                    if direction == 'long':
                        should_add = close >= last_addon_price + addon_trigger_distance
                    else:
                        should_add = close <= last_addon_price - addon_trigger_distance

                if should_add:
                    if direction == 'long':
                        new_stop = close - addon_stop_dist
                        new_target = close + addon_target_dist
                    else:
                        new_stop = close + addon_stop_dist
                        new_target = close - addon_target_dist

                    positions[position_id] = {
                        'entry': close,
                        'stop': new_stop,
                        'target': new_target,
                        'size': base_size,
                        'active': True,
                        'rr': addon_target_dist / addon_stop_dist if addon_stop_dist > 0 else 1.0,
                        'entry_bar': i,
                    }
                    position_id += 1
                    addon_count += 1
                    last_addon_price = close
                    total_slippage += self._calculate_slippage(ticker, close, base_size, current_atr)
                    total_commission += self.config.commission_per_trade

            # Update exit tracking
            trade_exit_time = bar.name
            trade_exit_price = close

            # Check if all positions closed
            if not any(p['active'] for p in positions.values()):
                break

        # Close any remaining positions at market
        for pid, pos in positions.items():
            if pos['active']:
                if direction == 'long':
                    pnl = (trade_exit_price - pos['entry']) * pos['size'] * multiplier
                else:
                    pnl = (pos['entry'] - trade_exit_price) * pos['size'] * multiplier
                total_gross_pnl += pnl
                total_slippage += self._calculate_slippage(ticker, trade_exit_price, pos['size'], atr)
                pos['active'] = False
                pos['exit_price'] = trade_exit_price
                pos['pnl'] = pnl
                if pnl > 0:
                    wins += 1
                else:
                    losses += 1
                all_exits.append({'price': trade_exit_price, 'pnl': pnl, 'reason': 'timeout', 'rr': pos['rr']})

        # Calculate totals
        total_size = sum(p['size'] for p in positions.values())

        # Create trade record
        trade = BacktestTrade(
            entry_time=entry_row.name,
            exit_time=trade_exit_time,
            ticker=ticker,
            direction=direction,
            entry_price=entry_price,
            exit_price=trade_exit_price,
            size=total_size,
            regime=regime,
            ensemble_prob=prob,
            signal_strength=strength,
            stop_loss=positions[0]['stop'],
            take_profit=positions[0]['target'],
            risk_reward=self.config.pyramid_first_rr,
            slippage_cost=total_slippage,
            commission=total_commission,
            gross_pnl=total_gross_pnl,
            partial_exits=all_exits,
            scaled_in=(addon_count > 1),
        )

        trade.net_pnl = trade.gross_pnl - trade.slippage_cost - trade.commission
        trade.pnl_pct = trade.net_pnl / capital * 100
        trade.is_winner = trade.net_pnl > 0

        return trade

    def _execute_trade_with_runners(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        direction: str,
        regime: str,
        regime_config: dict,
        prob: float,
        strength: float,
        capital: float,
        ticker: str = 'MES'
    ) -> Optional[BacktestTrade]:
        """
        Execute a trade with runner strategy:
        - Take partial profit at 1:1 R:R
        - Move stop to breakeven
        - Let runner ride to 1:2 or 2:3 R:R
        """
        entry_row = df.iloc[entry_idx]
        entry_price = entry_row['close']
        atr = entry_row['atr']

        # Get regime-adaptive stop multiplier
        stop_mult = regime_config.get('stop_mult', self.config.atr_stop_mult)

        # Calculate stop distance
        stop_distance = atr * stop_mult

        # Calculate targets based on R:R settings
        first_target_distance = stop_distance * self.config.runner_first_target_rr
        final_target_distance = stop_distance * self.config.runner_final_target_rr

        if direction == 'long':
            stop_loss = entry_price - stop_distance
            first_target = entry_price + first_target_distance
            final_target = entry_price + final_target_distance
        else:
            stop_loss = entry_price + stop_distance
            first_target = entry_price - first_target_distance
            final_target = entry_price - final_target_distance

        # Position size
        size_mult = regime_config.get('size_mult', 1.0)
        total_size = self._calculate_position_size(ticker, entry_price, stop_loss, capital)
        total_size = max(1, int(total_size * size_mult))

        # Split into partial and runner
        partial_size = max(1, int(total_size * (self.config.runner_partial_pct / 100)))
        runner_size = total_size - partial_size
        if runner_size < 1:
            runner_size = 0
            partial_size = total_size

        # Entry slippage
        entry_slippage = self._calculate_slippage(ticker, entry_price, total_size, atr)

        # Point multiplier - futures and CFDs
        point_multipliers = {
            'MES': 5.0, 'ES': 50.0, 'MNQ': 2.0, 'NQ': 20.0,
            'MYM': 0.50, 'YM': 5.0, 'RTY': 5.0, 'GC': 10.0,
            'SPY': 1.0, 'QQQ': 1.0, 'DIA': 1.0,
            'US30': 1.0, 'NAS100': 1.0, 'SPX500': 1.0, 'US500': 1.0,
        }
        multiplier = point_multipliers.get(ticker, 1.0)

        # Create trade
        trade = BacktestTrade(
            entry_time=entry_row.name,
            ticker=ticker,
            direction=direction,
            entry_price=entry_price,
            size=total_size,
            regime=regime,
            ensemble_prob=prob,
            signal_strength=strength,
            stop_loss=stop_loss,
            take_profit=final_target,
            risk_reward=self.config.runner_final_target_rr,
            slippage_cost=entry_slippage,
            commission=self.config.commission_per_trade,
            partial_exits=[]
        )

        # Simulate with runner logic
        max_bars = 50
        partial_taken = False
        current_stop = stop_loss
        remaining_size = total_size
        total_gross_pnl = 0.0

        for i in range(entry_idx + 1, min(entry_idx + max_bars, len(df))):
            bar = df.iloc[i]
            high, low, close = bar['high'], bar['low'], bar['close']

            if direction == 'long':
                # Check stop first
                if low <= current_stop:
                    exit_price = current_stop
                    pnl = (exit_price - entry_price) * remaining_size * multiplier
                    total_gross_pnl += pnl
                    trade.exit_price = exit_price
                    trade.exit_time = bar.name
                    trade.exit_reason = 'stop' if not partial_taken else 'stop_be'
                    break

                # Check first target (partial exit)
                if not partial_taken and high >= first_target:
                    partial_pnl = (first_target - entry_price) * partial_size * multiplier
                    total_gross_pnl += partial_pnl
                    trade.partial_exits.append({
                        'price': first_target,
                        'size': partial_size,
                        'pnl': partial_pnl,
                        'rr': self.config.runner_first_target_rr
                    })
                    partial_taken = True
                    remaining_size = runner_size

                    # Move stop to breakeven
                    if self.config.runner_move_stop_to_be:
                        current_stop = entry_price + (atr * 0.1)  # Slightly above BE

                    # If no runner left, we're done
                    if remaining_size <= 0:
                        trade.exit_price = first_target
                        trade.exit_time = bar.name
                        trade.exit_reason = 'target_partial'
                        break

                # Check final target (runner exit)
                if partial_taken and high >= final_target:
                    runner_pnl = (final_target - entry_price) * remaining_size * multiplier
                    total_gross_pnl += runner_pnl
                    trade.runner_pnl = runner_pnl
                    trade.exit_price = final_target
                    trade.exit_time = bar.name
                    trade.exit_reason = 'target_full'
                    break

            else:  # short
                # Check stop first
                if high >= current_stop:
                    exit_price = current_stop
                    pnl = (entry_price - exit_price) * remaining_size * multiplier
                    total_gross_pnl += pnl
                    trade.exit_price = exit_price
                    trade.exit_time = bar.name
                    trade.exit_reason = 'stop' if not partial_taken else 'stop_be'
                    break

                # Check first target (partial exit)
                if not partial_taken and low <= first_target:
                    partial_pnl = (entry_price - first_target) * partial_size * multiplier
                    total_gross_pnl += partial_pnl
                    trade.partial_exits.append({
                        'price': first_target,
                        'size': partial_size,
                        'pnl': partial_pnl,
                        'rr': self.config.runner_first_target_rr
                    })
                    partial_taken = True
                    remaining_size = runner_size

                    # Move stop to breakeven
                    if self.config.runner_move_stop_to_be:
                        current_stop = entry_price - (atr * 0.1)

                    if remaining_size <= 0:
                        trade.exit_price = first_target
                        trade.exit_time = bar.name
                        trade.exit_reason = 'target_partial'
                        break

                # Check final target (runner exit)
                if partial_taken and low <= final_target:
                    runner_pnl = (entry_price - final_target) * remaining_size * multiplier
                    total_gross_pnl += runner_pnl
                    trade.runner_pnl = runner_pnl
                    trade.exit_price = final_target
                    trade.exit_time = bar.name
                    trade.exit_reason = 'target_full'
                    break

            # Update for timeout
            trade.exit_time = bar.name
            trade.exit_price = close

        # Handle timeout - close remaining at market
        if trade.exit_reason == "":
            trade.exit_reason = 'timeout'
            if remaining_size > 0:
                if direction == 'long':
                    timeout_pnl = (trade.exit_price - entry_price) * remaining_size * multiplier
                else:
                    timeout_pnl = (entry_price - trade.exit_price) * remaining_size * multiplier
                total_gross_pnl += timeout_pnl

        # Calculate final P&L
        exit_slippage = self._calculate_slippage(ticker, trade.exit_price, remaining_size, atr)
        trade.slippage_cost += exit_slippage
        trade.gross_pnl = total_gross_pnl
        trade.net_pnl = trade.gross_pnl - trade.slippage_cost - trade.commission
        trade.pnl_pct = trade.net_pnl / capital * 100
        trade.is_winner = trade.net_pnl > 0

        return trade

    # ========================================
    # BACKTEST EXECUTION
    # ========================================

    async def run_backtest(
        self,
        ticker: str = 'MES',
        days: int = 90,
        end_date: Optional[datetime] = None,
        cached_data: Optional[pd.DataFrame] = None
    ) -> BacktestMetrics:
        """Run full backtest."""
        logger.info(f"Starting backtest for {ticker}, {days} days")

        end = end_date or datetime.now()
        start = end - timedelta(days=days)

        # Use cached data if provided, otherwise fetch
        if cached_data is not None and len(cached_data) > 0:
            df = cached_data.copy()
            logger.info(f"Using cached data: {len(df)} bars for {ticker}")
        else:
            df = await self.fetch_data(ticker, start, end)
        if df.empty:
            logger.error("No data available")
            return BacktestMetrics()

        # Calculate indicators
        df = self._calculate_indicators(df)

        # Reset state
        self.trades = []
        self.equity_curve = []
        capital = self.config.initial_capital

        # Track positions
        in_position = False
        current_trade: Optional[BacktestTrade] = None

        # Track regime distribution
        regime_counts = {}

        # Track flow stats
        flow_stats = {'total': 0, 'confirmed': 0, 'skipped': 0}

        # Walk through bars
        for idx in range(50, len(df) - 1):  # Skip warmup period
            timestamp = df.index[idx]

            # Detect regime with config
            regime, regime_conf, regime_config = self._detect_regime(df, idx)

            # Track regime distribution
            regime_counts[regime] = regime_counts.get(regime, 0) + 1

            if not in_position:
                # Generate signal with regime awareness
                direction, prob, strength = self._generate_signal(df, idx, regime, regime_config)

                if direction and strength >= self.config.min_signal_strength:
                    flow_stats['total'] += 1

                    # Check flow confirmation
                    flow_confirmed = False
                    flow_info = ""
                    prob_boost = 0.0

                    if self.config.use_flow_filter:
                        flow_confirmed, prob_boost, flow_info = self._check_flow_confirmation(
                            df, idx, direction
                        )

                        # Skip trade if flow is strongly opposing (negative boost)
                        if prob_boost < 0:
                            flow_stats['skipped'] += 1
                            continue

                        # Skip trade if flow doesn't confirm and filter is strict
                        if self.config.require_flow_confirmation and not flow_confirmed:
                            flow_stats['skipped'] += 1
                            continue

                        # UPTREND TIGHTENING: Flow/imbalance filter for longs in trending_up
                        # NOTE: In backtesting, flow is simulated and may not match live behavior
                        # The probability threshold (0.66) is already applied in _generate_signal
                        # This additional filter is optional and can be disabled for cleaner backtesting
                        if self.config.uptrend_tightening and regime == 'trending_up' and direction == 'long':
                            # Only apply flow/imbalance filter if flow_info shows weak conviction
                            conviction = flow_info.split('_')[0] if flow_info else 'MEDIUM'
                            # Skip ONLY if conviction is LOW or NEUTRAL (very weak flow)
                            if conviction in ['LOW', 'NEUTRAL']:
                                flow_stats['skipped'] += 1
                                continue

                        # Apply probability boost
                        if flow_confirmed and self.config.flow_prob_boost and prob_boost > 0:
                            prob = min(1.0, prob + prob_boost)
                            flow_stats['confirmed'] += 1

                    # Execute trade with regime-adaptive parameters
                    # Pyramid only for longs if pyramid_longs_only is set
                    use_pyramid_for_trade = (
                        self.config.use_pyramid and
                        (not self.config.pyramid_longs_only or direction == 'long')
                    )

                    if use_pyramid_for_trade:
                        trade = self._execute_trade_with_pyramid(
                            df, idx, direction, regime, regime_config, prob, strength, capital, ticker
                        )
                    elif self.config.use_runners:
                        trade = self._execute_trade_with_runners(
                            df, idx, direction, regime, regime_config, prob, strength, capital, ticker
                        )
                    else:
                        trade = self._execute_trade(
                            df, idx, direction, regime, regime_config, prob, strength, capital, ticker
                        )

                    if trade:
                        trade.flow_confirmed = flow_confirmed
                        trade.flow_info = flow_info
                        self.trades.append(trade)
                        capital += trade.net_pnl

                        # Update equity curve
                        self.equity_curve.append((trade.exit_time, capital))

            # Update equity curve even without trades
            if len(self.equity_curve) == 0 or self.equity_curve[-1][0] != timestamp:
                self.equity_curve.append((timestamp, capital))

        # Log flow stats
        logger.info(
            f"Flow confirmation stats: {flow_stats['confirmed']}/{flow_stats['total']} confirmed, "
            f"{flow_stats['skipped']} skipped"
        )

        # Calculate metrics
        self.metrics = self._calculate_metrics()

        logger.info(
            f"Backtest complete: {self.metrics.total_trades} trades, "
            f"Sharpe={self.metrics.sharpe_ratio:.2f}, "
            f"Win Rate={self.metrics.win_rate:.1f}%"
        )

        return self.metrics

    async def run_deterministic_backtest(
        self,
        ticker: str = 'MES',
        days: int = 90,
        end_date: Optional[datetime] = None
    ) -> BacktestMetrics:
        """
        Run backtest using Deterministic multi-timeframe indicator engine.

        Phase 2C: True engine-specific execution.
        """
        logger.info(f"Starting DETERMINISTIC backtest for {ticker}, {days} days")

        end = end_date or datetime.now()
        start = end - timedelta(days=days)

        # Fetch data
        df = await self.fetch_data(ticker, start, end)
        if df.empty:
            logger.error("No data available")
            return BacktestMetrics()

        # Calculate basic indicators (still needed for regime detection)
        df = self._calculate_indicators(df)

        # Reset state
        self.trades = []
        self.equity_curve = []
        capital = self.config.initial_capital

        # Track positions
        in_position = False

        # Walk through bars
        for idx in range(200, len(df) - 1):  # Need more history for MTF resampling
            timestamp = df.index[idx]

            if not in_position:
                # Generate signal using Deterministic engine
                direction, prob, strength, mtf_data = self._generate_deterministic_signal(df, idx, ticker)

                if direction and mtf_data:
                    # Use MTF-derived stop/target levels
                    entry_price = df.iloc[idx]['close']
                    stop_loss = mtf_data['stop_loss']
                    take_profit = mtf_data['take_profit']
                    risk_reward = mtf_data['risk_reward']

                    # Calculate position size
                    size = self._calculate_position_size(ticker, entry_price, stop_loss, capital)

                    # Create trade with engine attribution
                    trade = BacktestTrade(
                        entry_time=timestamp,
                        ticker=ticker,
                        direction=direction,
                        entry_price=entry_price,
                        size=size,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        risk_reward=risk_reward,
                        ensemble_prob=prob,
                        signal_strength=strength,
                        engine_type='deterministic'  # Phase 2C attribution
                    )

                    # Simulate trade execution
                    trade = self._simulate_trade_exit(df, idx, trade)

                    if trade and trade.exit_time:
                        self.trades.append(trade)
                        capital += trade.net_pnl
                        self.equity_curve.append((trade.exit_time, capital))

            # Update equity curve even without trades
            if len(self.equity_curve) == 0 or self.equity_curve[-1][0] != timestamp:
                self.equity_curve.append((timestamp, capital))

        # Calculate metrics
        self.metrics = self._calculate_metrics()

        logger.info(
            f"Deterministic backtest complete: {self.metrics.total_trades} trades, "
            f"Sharpe={self.metrics.sharpe_ratio:.2f}, "
            f"Win Rate={self.metrics.win_rate:.1f}%"
        )

        return self.metrics

    def _simulate_trade_exit(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        trade: BacktestTrade
    ) -> Optional[BacktestTrade]:
        """
        Simulate trade execution and exit for Deterministic trades.

        Simple exit logic: hit stop or target, or timeout after 48 bars (4h).
        """
        max_hold_bars = 48  # Max 4 hours (48 * 5min bars)

        for offset in range(1, min(max_hold_bars + 1, len(df) - entry_idx)):
            idx = entry_idx + offset
            bar = df.iloc[idx]
            high = bar['high']
            low = bar['low']
            close = bar['close']

            # Check exits
            if trade.direction == 'long':
                # Check stop hit
                if low <= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                # Check target hit
                elif high >= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break
            else:  # short
                # Check stop hit
                if high >= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                # Check target hit
                elif low <= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break

        # Timeout exit
        if trade.exit_time is None:
            trade.exit_price = df.iloc[min(entry_idx + max_hold_bars, len(df) - 1)]['close']
            trade.exit_time = df.index[min(entry_idx + max_hold_bars, len(df) - 1)]
            trade.exit_reason = 'timeout'

        # Calculate P&L
        if trade.direction == 'long':
            trade.gross_pnl = (trade.exit_price - trade.entry_price) * trade.size
        else:
            trade.gross_pnl = (trade.entry_price - trade.exit_price) * trade.size

        trade.slippage_cost = self.config.base_slippage_ticks * trade.size
        trade.commission = self.config.commission_per_trade
        trade.net_pnl = trade.gross_pnl - trade.slippage_cost - trade.commission

        trade.is_winner = trade.net_pnl > 0
        trade.pnl_pct = (trade.net_pnl / self.config.initial_capital) * 100

        return trade

    # ========================================
    # QUICK SIGNAL GENERATION (Phase 2C)
    # ========================================

    def _generate_quick_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        ticker: str
    ) -> Tuple[Optional[str], float, float, Optional[Dict]]:
        """
        Generate signal using Quick 5m momentum engine.

        Quick mode:
        - 5m momentum primary
        - Optional 15m confirmation
        - Lower thresholds: 60% confidence, 1.5:1 R:R
        - Volume confirmation required
        - Faster, more frequent trades

        Returns: (direction, probability, strength, quick_signal_data)
        """
        try:
            # Import indicator engine
            from app.services.indicators import get_indicator_engine, IndicatorConfig

            # Create config with Quick parameters
            indicator_config = IndicatorConfig(
                min_aligned_timeframes=1,  # Only need 5m (+ optional 15m)
                require_higher_tf_agreement=False,  # No 1h/4h requirement
                min_confidence_score=60.0,  # Lower threshold than Deterministic
                min_risk_reward=1.5  # More aggressive than Deterministic 2:1
            )

            # Quick-specific ATR multipliers
            quick_atr_stop_mult = 1.0  # Tighter stop
            quick_atr_target_mult = 1.5  # Quick target (1.5:1 R:R)

            indicator_engine = get_indicator_engine(indicator_config)

            # For Quick, we only need 5m (and optionally 15m)
            # Get just the 5m data up to current point
            hist_5m = df.iloc[:idx + 1].tail(200).copy()

            if len(hist_5m) < 30:
                return None, 0.5, 0.0, None

            # Analyze 5m timeframe
            try:
                tf_5m = indicator_engine.calculate_indicators(hist_5m, '5m')
            except:
                # Fallback: use method name that exists
                from app.services.indicators import DeterministicIndicators
                engine = DeterministicIndicators(indicator_config)
                tf_5m = engine.calculate_indicators(hist_5m, '5m')

            if not tf_5m:
                return None, 0.5, 0.0, None

            # Extract indicators
            close = tf_5m.close
            ema9 = tf_5m.ema9
            ema21 = tf_5m.ema21
            rsi = tf_5m.rsi14
            macd_hist = tf_5m.macd_histogram
            atr = tf_5m.atr14
            volume_ratio = tf_5m.volume_ratio

            # Quick mode volume requirement
            quick_min_volume_ratio = 1.2
            if volume_ratio < quick_min_volume_ratio:
                return None, 0.5, 0.0, None

            # Quick mode criteria (simpler than Deterministic)
            bullish_ema = ema9 > ema21
            bullish_rsi = 40 < rsi < 70
            bullish_macd = macd_hist > 0
            rsi_momentum_bull = rsi > 55  # Quick RSI momentum threshold

            bearish_ema = ema9 < ema21
            bearish_rsi = 30 < rsi < 60
            bearish_macd = macd_hist < 0
            rsi_momentum_bear = rsi < 45

            # Optional 15m confirmation (for backtesting, we'll skip this for simplicity)
            # In live Quick mode, this is configurable

            # Calculate confidence score (Quick scoring system)
            bullish_score = 0
            bearish_score = 0

            # EMA crossover (40 points)
            if bullish_ema:
                bullish_score += 40
            if bearish_ema:
                bearish_score += 40

            # RSI momentum (25 points)
            if rsi_momentum_bull:
                bullish_score += 25
            if rsi_momentum_bear:
                bearish_score += 25

            # MACD direction (20 points)
            if bullish_macd:
                bullish_score += 20
            if bearish_macd:
                bearish_score += 20

            # Volume confirmation (15 points)
            if volume_ratio >= quick_min_volume_ratio:
                if bullish_ema:
                    bullish_score += 15
                if bearish_ema:
                    bearish_score += 15

            # Determine signal
            action = None
            confidence = 0

            min_quick_confidence = 60.0

            if bullish_score >= min_quick_confidence and bullish_score > bearish_score:
                action = 'buy'
                confidence = bullish_score
            elif bearish_score >= min_quick_confidence and bearish_score > bullish_score:
                action = 'sell'
                confidence = bearish_score

            if not action:
                return None, confidence / 100, 0.0, None

            # Calculate stop and target using ATR (Quick style - tighter)
            entry_price = close
            if action == 'buy':
                stop_loss = close - (atr * quick_atr_stop_mult)
                take_profit = close + (atr * quick_atr_target_mult)
            else:
                stop_loss = close + (atr * quick_atr_stop_mult)
                take_profit = close - (atr * quick_atr_target_mult)

            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            risk_reward = reward / risk if risk > 0 else 0

            # Package Quick signal data
            quick_data = {
                'confidence': confidence,
                'risk_reward': risk_reward,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'entry_price': entry_price,
                'volume_ratio': volume_ratio,
                'ema9': ema9,
                'ema21': ema21,
                'rsi': rsi
            }

            return action, confidence / 100, confidence, quick_data

        except ImportError as e:
            logger.warning(f"Quick indicators not available: {e}")
            return None, 0.5, 0.0, None
        except Exception as e:
            logger.error(f"Error generating quick signal: {e}")
            return None, 0.5, 0.0, None

    async def run_quick_backtest(
        self,
        ticker: str = 'MES',
        days: int = 90,
        end_date: Optional[datetime] = None
    ) -> BacktestMetrics:
        """
        Run backtest using Quick 5m momentum engine.

        Phase 2C: True engine-specific execution.
        Quick mode:
        - 5m momentum signals
        - Lower threshold (60% vs 75%)
        - Tighter R:R (1.5:1 vs 2:1)
        - More frequent trades
        - Shorter holding times
        """
        logger.info(f"Starting QUICK backtest for {ticker}, {days} days")

        end = end_date or datetime.now()
        start = end - timedelta(days=days)

        # Fetch data
        df = await self.fetch_data(ticker, start, end)
        if df.empty:
            logger.error("No data available")
            return BacktestMetrics()

        # Calculate basic indicators (for Quick signal generation)
        df = self._calculate_indicators(df)

        # Reset state
        self.trades = []
        self.equity_curve = []
        capital = self.config.initial_capital

        # Walk through bars (Quick needs less history)
        for idx in range(50, len(df) - 1):  # Start earlier than Deterministic (50 vs 200)
            timestamp = df.index[idx]

            # Generate signal using Quick engine
            direction, prob, strength, quick_data = self._generate_quick_signal(df, idx, ticker)

            if direction and quick_data:
                # Use Quick-derived stop/target levels
                entry_price = df.iloc[idx]['close']
                stop_loss = quick_data['stop_loss']
                take_profit = quick_data['take_profit']
                risk_reward = quick_data['risk_reward']

                # Calculate position size
                size = self._calculate_position_size(ticker, entry_price, stop_loss, capital)

                # Create trade with engine attribution
                trade = BacktestTrade(
                    entry_time=timestamp,
                    ticker=ticker,
                    direction=direction,
                    entry_price=entry_price,
                    size=size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward=risk_reward,
                    ensemble_prob=prob,
                    signal_strength=strength,
                    engine_type='quick'  # Phase 2C attribution
                )

                # Simulate trade execution (Quick mode: shorter timeout)
                trade = self._simulate_quick_trade_exit(df, idx, trade)

                if trade and trade.exit_time:
                    self.trades.append(trade)
                    capital += trade.net_pnl
                    self.equity_curve.append((trade.exit_time, capital))

            # Update equity curve
            if len(self.equity_curve) == 0 or self.equity_curve[-1][0] != timestamp:
                self.equity_curve.append((timestamp, capital))

        # Calculate metrics
        self.metrics = self._calculate_metrics()

        logger.info(
            f"Quick backtest complete: {self.metrics.total_trades} trades, "
            f"Sharpe={self.metrics.sharpe_ratio:.2f}, "
            f"Win Rate={self.metrics.win_rate:.1f}%"
        )

        return self.metrics

    def _simulate_quick_trade_exit(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        trade: BacktestTrade
    ) -> Optional[BacktestTrade]:
        """
        Simulate trade execution for Quick trades.

        Quick mode: shorter timeout (24 bars = 2 hours vs 48 bars = 4 hours for Deterministic)
        """
        max_hold_bars = 24  # Quick mode: max 2 hours (24 * 5min bars)

        for offset in range(1, min(max_hold_bars + 1, len(df) - entry_idx)):
            idx = entry_idx + offset
            bar = df.iloc[idx]
            high = bar['high']
            low = bar['low']

            # Check exits (same logic as Deterministic)
            if trade.direction == 'long':
                if low <= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                elif high >= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break
            else:  # short
                if high >= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                elif low <= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break

        # Timeout exit
        if trade.exit_time is None:
            trade.exit_price = df.iloc[min(entry_idx + max_hold_bars, len(df) - 1)]['close']
            trade.exit_time = df.index[min(entry_idx + max_hold_bars, len(df) - 1)]
            trade.exit_reason = 'timeout'

        # Calculate P&L
        if trade.direction == 'long':
            trade.gross_pnl = (trade.exit_price - trade.entry_price) * trade.size
        else:
            trade.gross_pnl = (trade.entry_price - trade.exit_price) * trade.size

        trade.slippage_cost = self.config.base_slippage_ticks * trade.size
        trade.commission = self.config.commission_per_trade
        trade.net_pnl = trade.gross_pnl - trade.slippage_cost - trade.commission

        trade.is_winner = trade.net_pnl > 0
        trade.pnl_pct = (trade.net_pnl / self.config.initial_capital) * 100

        return trade

    # ========================================
    # AI-PROXY BACKTEST (Phase 5A)
    # ========================================

    async def run_ai_proxy_backtest(
        self,
        ticker: str = 'MES',
        days: int = 90,
        end_date: Optional[datetime] = None
    ) -> BacktestMetrics:
        """
        Run backtest using AI-Proxy engine.

        Phase 5A: AI-proxy implementation (NOT true Claude analysis).

        AI-Proxy characteristics:
        - Uses multi-timeframe analysis (deterministic component)
        - Applies AI confidence threshold (70% vs deterministic's 75%)
        - Requires MTF alignment (like live AI mode does)
        - Produces fewer but higher-quality trades

        IMPORTANT: This is NOT true Claude API historical replay.
        This uses deterministic MTF indicators as a proxy for AI behavior
        while preserving AI decision framework (thresholds, alignment, voting).

        Metadata will label this as 'ai_proxy_backtest' with
        routing_status='partially_routed' to be honest about limitations.
        """
        logger.info(f"Starting AI-PROXY backtest for {ticker}, {days} days")
        logger.info("NOTE: AI-Proxy uses MTF analysis + AI thresholds (not true Claude analysis)")

        end = end_date or datetime.now()
        start = end - timedelta(days=days)

        # Fetch data
        df = await self.fetch_data(ticker, start, end)
        if df.empty:
            logger.error("No data available")
            return BacktestMetrics()

        # Calculate basic indicators
        df = self._calculate_indicators(df)

        # Reset state
        self.trades = []
        self.equity_curve = []
        capital = self.config.initial_capital

        # Walk through bars (AI-proxy needs similar history to Deterministic)
        for idx in range(200, len(df) - 1):  # Need history for MTF analysis
            timestamp = df.index[idx]

            # Generate signal using AI-Proxy engine
            direction, prob, strength, ai_data = self._generate_ai_proxy_signal(df, idx, ticker)

            if direction and ai_data:
                # Use AI-proxy-derived stop/target levels
                entry_price = df.iloc[idx]['close']
                stop_loss = ai_data['stop_loss']
                take_profit = ai_data['take_profit']
                risk_reward = ai_data['risk_reward']

                # Calculate position size
                size = self._calculate_position_size(ticker, entry_price, stop_loss, capital)

                # Create trade with engine attribution
                trade = BacktestTrade(
                    entry_time=timestamp,
                    ticker=ticker,
                    direction=direction,
                    entry_price=entry_price,
                    size=size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward=risk_reward,
                    ensemble_prob=prob,
                    signal_strength=strength,
                    engine_type='ai'  # Phase 5A attribution
                )

                # Simulate trade execution (AI-proxy: similar timeout to Deterministic)
                trade = self._simulate_ai_proxy_trade_exit(df, idx, trade)

                if trade and trade.exit_time:
                    self.trades.append(trade)
                    capital += trade.net_pnl
                    self.equity_curve.append((trade.exit_time, capital))

            # Update equity curve
            if len(self.equity_curve) == 0 or self.equity_curve[-1][0] != timestamp:
                self.equity_curve.append((timestamp, capital))

        # Calculate metrics
        self.metrics = self._calculate_metrics()

        logger.info(
            f"AI-Proxy backtest complete: {self.metrics.total_trades} trades, "
            f"Sharpe={self.metrics.sharpe_ratio:.2f}, "
            f"Win Rate={self.metrics.win_rate:.1f}%"
        )

        return self.metrics

    def _generate_ai_proxy_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        ticker: str
    ) -> Tuple[Optional[str], float, float, Optional[Dict]]:
        """
        Generate signal using AI-Proxy engine (Phase 5A).

        AI-Proxy logic:
        1. Use MTF analysis (deterministic component)
        2. Apply AI confidence threshold (70% instead of 75%)
        3. Require MTF bias alignment (like live AI does)

        Returns: (direction, probability, strength, ai_proxy_data)
        """
        try:
            # Import indicator engine
            from app.services.indicators import get_indicator_engine, IndicatorConfig

            # Create config with AI-PROXY parameters
            # Lower threshold than Deterministic (70% vs 75%) but still selective
            indicator_config = IndicatorConfig(
                min_aligned_timeframes=4,
                require_higher_tf_agreement=True,
                min_confidence_score=70.0,  # AI threshold (lower than deterministic's 75%)
                min_risk_reward=2.0
            )

            indicator_engine = get_indicator_engine(indicator_config)

            # Resample to multiple timeframes
            bars_by_tf = self._resample_to_timeframes(df, idx)

            if len(bars_by_tf) < 3:
                logger.debug(f"AI-Proxy: Insufficient timeframes: {len(bars_by_tf)}/5")
                return None, 0.5, 0.0, None

            # Run multi-timeframe analysis
            mtf_signal = indicator_engine.analyze_multi_timeframe(ticker, bars_by_tf)

            # AI-Proxy requirement: Confidence must meet AI threshold (70%)
            if mtf_signal.confidence_score < 70.0:
                logger.debug(f"AI-Proxy: Confidence {mtf_signal.confidence_score:.1f}% < 70% threshold")
                return None, mtf_signal.confidence_score / 100, 0.0, None

            # AI-Proxy requirement: MTF bias must be clear (not neutral)
            # This mimics live AI requiring MTF alignment
            if mtf_signal.overall_bias == 'neutral':
                logger.debug(f"AI-Proxy: Skipping neutral MTF bias (requires clear direction)")
                return None, mtf_signal.confidence_score / 100, 0.0, None

            if not mtf_signal.should_trade:
                return None, mtf_signal.confidence_score / 100, 0.0, None

            # Convert to backtest format
            direction = 'long' if mtf_signal.action == 'buy' else 'short' if mtf_signal.action == 'sell' else None
            probability = mtf_signal.confidence_score / 100  # Convert 0-100 to 0-1
            strength = mtf_signal.confidence_score  # Use confidence as strength

            # Package AI-proxy signal data
            ai_data = {
                'aligned_tfs': mtf_signal.aligned_bullish if mtf_signal.overall_bias == 'bullish' else mtf_signal.aligned_bearish,
                'confidence': mtf_signal.confidence_score,
                'risk_reward': mtf_signal.risk_reward_ratio,
                'stop_loss': mtf_signal.stop_loss,
                'take_profit': mtf_signal.take_profit,
                'entry_price': mtf_signal.entry_price,
                'overall_bias': mtf_signal.overall_bias,
                'ai_proxy_note': f'MTF-based proxy with AI threshold (70%)'
            }

            return direction, probability, strength, ai_data

        except ImportError as e:
            logger.warning(f"AI-Proxy indicators not available: {e}")
            return None, 0.5, 0.0, None
        except Exception as e:
            logger.error(f"Error generating AI-proxy signal: {e}")
            return None, 0.5, 0.0, None

    def _simulate_ai_proxy_trade_exit(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        trade: BacktestTrade
    ) -> Optional[BacktestTrade]:
        """
        Simulate trade execution for AI-Proxy trades.

        AI-Proxy mode: similar timeout to Deterministic (48 bars = 4 hours)
        but with stricter entry criteria (70% confidence + MTF alignment).
        """
        max_hold_bars = 48  # AI-Proxy: max 4 hours (same as Deterministic)

        for offset in range(1, min(max_hold_bars + 1, len(df) - entry_idx)):
            idx = entry_idx + offset
            bar = df.iloc[idx]
            high = bar['high']
            low = bar['low']

            # Check exits
            if trade.direction == 'long':
                if low <= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                elif high >= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break
            else:  # short
                if high >= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                elif low <= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break

        # Timeout exit
        if trade.exit_time is None:
            trade.exit_price = df.iloc[min(entry_idx + max_hold_bars, len(df) - 1)]['close']
            trade.exit_time = df.index[min(entry_idx + max_hold_bars, len(df) - 1)]
            trade.exit_reason = 'timeout'

        # Calculate P&L
        if trade.direction == 'long':
            trade.gross_pnl = (trade.exit_price - trade.entry_price) * trade.size
        else:
            trade.gross_pnl = (trade.entry_price - trade.exit_price) * trade.size

        trade.slippage_cost = self.config.base_slippage_ticks * trade.size
        trade.commission = self.config.commission_per_trade
        trade.net_pnl = trade.gross_pnl - trade.slippage_cost - trade.commission

        trade.is_winner = trade.net_pnl > 0
        trade.pnl_pct = (trade.net_pnl / self.config.initial_capital) * 100

        return trade

    async def run_flow_backtest(
        self,
        ticker: str = 'MES',
        days: int = 90,
        end_date: Optional[datetime] = None
    ) -> BacktestMetrics:
        """
        Run backtest using Flow engine with historical Polygon options flow data.

        Phase 5B: Historical flow replay using REAL Polygon options trades.

        This IS true historical flow replay - NOT a proxy!
        - Fetches real options trade data from Polygon API
        - Applies same sentiment scoring logic as live Flow mode
        - Generates signals based on flow thresholds (±3.0)
        - Fully deterministic and replayable

        Args:
            ticker: Futures ticker (MES, NQ, GC, etc.)
            days: Days of history to backtest
            end_date: Optional end date (defaults to now)

        Returns:
            BacktestMetrics with flow-attributed trades
        """
        logger.info(f"Starting FLOW HISTORICAL REPLAY backtest for {ticker}, {days} days")
        logger.info("NOTE: Using REAL Polygon options flow data (not proxy!)")

        # Reset state
        self.trades = []
        self.equity_curve = []

        # Map futures ticker to ETF (for options flow)
        ticker_map = {
            'MES': 'SPY',
            'MYM': 'SPY',
            'NQ': 'QQQ',
            'MNQ': 'QQQ',
            'GC': 'GLD',
            'MGC': 'GLD',
            'RTY': 'IWM',
            'M2K': 'IWM'
        }
        flow_ticker = ticker_map.get(ticker, 'SPY')
        logger.info(f"Flow ticker mapping: {ticker} → {flow_ticker}")

        # Fetch historical bars
        end = end_date or datetime.now()
        start = end - timedelta(days=days)
        df = await self.fetch_data(ticker, start, end)

        if df.empty:
            logger.warning(f"No historical data for {ticker}")
            return self._calculate_metrics()

        logger.info(f"Fetched {len(df)} bars from {df.index[0]} to {df.index[-1]}")

        # Initialize Polygon flow service
        try:
            from app.services.polygon_options_flow import get_polygon_options_flow
            polygon_service = await get_polygon_options_flow()
        except Exception as e:
            logger.error(f"Failed to initialize Polygon flow service: {e}")
            return self._calculate_metrics()

        # Track last signal to prevent duplicates
        last_signal_time = None
        last_signal_direction = None
        signal_cooldown = timedelta(minutes=30)

        capital = self.config.initial_capital
        self.equity_curve.append((df.index[0], capital))

        # Iterate through bars
        for idx in range(50, len(df)):  # Need history for flow analysis
            timestamp = df.index[idx]
            bar = df.iloc[idx]

            # Skip if in active trade
            if self.trades and self.trades[-1].exit_time is None:
                continue

            # Generate flow signal for this bar
            direction, prob, strength, flow_data = await self._generate_flow_signal(
                df=df,
                idx=idx,
                ticker=ticker,
                flow_ticker=flow_ticker,
                polygon_service=polygon_service
            )

            if direction and flow_data:
                # Check duplicate prevention (same as live Flow mode)
                if last_signal_time and last_signal_direction == direction:
                    if timestamp - last_signal_time < signal_cooldown:
                        logger.debug(f"Flow: Skipping duplicate {direction} signal (cooldown)")
                        continue

                entry_price = bar['close']
                stop_loss = flow_data['stop_loss']
                take_profit = flow_data['take_profit']
                risk_reward = flow_data['risk_reward']

                # Calculate position size
                size = self._calculate_position_size(ticker, entry_price, stop_loss, capital)

                # Create trade with flow attribution
                trade = BacktestTrade(
                    entry_time=timestamp,
                    ticker=ticker,
                    direction=direction,
                    entry_price=entry_price,
                    size=size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    risk_reward=risk_reward,
                    ensemble_prob=prob,
                    signal_strength=strength,
                    engine_type='flow'  # Phase 5B attribution
                )

                # Simulate trade execution (Flow: 24-hour max hold for flow signals)
                trade = self._simulate_flow_trade_exit(df, idx, trade)

                if trade and trade.exit_time:
                    self.trades.append(trade)
                    capital += trade.net_pnl
                    self.equity_curve.append((trade.exit_time, capital))

                    # Update last signal tracking
                    last_signal_time = timestamp
                    last_signal_direction = direction

            # Update equity curve
            if len(self.equity_curve) == 0 or self.equity_curve[-1][0] != timestamp:
                self.equity_curve.append((timestamp, capital))

        # Calculate metrics
        self.metrics = self._calculate_metrics()

        logger.info(
            f"Flow historical replay complete: {self.metrics.total_trades} trades, "
            f"Sharpe={self.metrics.sharpe_ratio:.2f}, "
            f"Win Rate={self.metrics.win_rate:.1f}%"
        )

        return self.metrics

    async def _generate_flow_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        ticker: str,
        flow_ticker: str,
        polygon_service: Any
    ) -> Tuple[Optional[str], float, float, Optional[Dict]]:
        """
        Generate signal using Flow engine with historical Polygon data.

        Phase 5B: Uses REAL historical options flow data from Polygon.

        Returns: (direction, probability, strength, flow_data)
        """
        try:
            bar_time = df.index[idx]

            # Fetch historical flow data for 5-minute window before this bar
            # (same window as live Flow mode)
            flow_window_minutes = 5
            start_time = bar_time - timedelta(minutes=flow_window_minutes)
            end_time = bar_time

            flows = await polygon_service.fetch_historical_options_trades(
                ticker=flow_ticker,
                start_time=start_time,
                end_time=end_time
            )

            if not flows:
                logger.debug(f"Flow: No flow data for {flow_ticker} at {bar_time}")
                return None, 0.5, 0.0, None

            # Compute sentiment score using SAME logic as live Flow mode
            # Import SmartFlow service for sentiment calculation
            from app.services.smartflow_service import SmartFlowService

            # Create temporary service instance to use sentiment logic
            flow_service = SmartFlowService()

            # Convert Polygon flows to FlowEntry format
            from app.services.smartflow_service import FlowEntry

            flow_entries = []
            for trade in flows:
                flow_entries.append(FlowEntry(
                    timestamp=trade.timestamp,
                    ticker=trade.ticker,
                    flow_type='sweep' if trade.is_sweep else 'block' if trade.is_block else 'trade',
                    side='bullish' if trade.sentiment == 'bullish' else 'bearish',
                    option_type=trade.option_type,
                    premium=trade.premium,
                    strike=trade.strike,
                    expiry=trade.expiry
                ))

            # Compute sentiment using live Flow logic
            sentiment = flow_service.compute_sentiment_score(flow_entries, flow_ticker)

            # Check signal thresholds (same as live: ±3.0)
            buy_threshold = flow_service.score_threshold_buy  # 3.0
            sell_threshold = flow_service.score_threshold_sell  # -3.0

            if sentiment.score >= buy_threshold:
                # Buy signal
                logger.info(f"Flow BUY signal: {flow_ticker} score={sentiment.score:.1f}, "
                           f"{len(flows)} flows, ${sentiment.total_premium:,.0f} premium")

                # Calculate stops using current price
                current_price = df.iloc[idx]['close']
                atr = self._calculate_atr(df, idx, window=14)
                stop_distance = atr * 2.0
                risk_reward = 2.0

                flow_data = {
                    'sentiment_score': sentiment.score,
                    'flow_count': len(flows),
                    'total_premium': sentiment.total_premium,
                    'bullish_flows': sentiment.bullish_flows,
                    'bearish_flows': sentiment.bearish_flows,
                    'stop_loss': current_price - stop_distance,
                    'take_profit': current_price + (stop_distance * risk_reward),
                    'risk_reward': risk_reward,
                    'entry_price': current_price
                }

                return 'long', min(sentiment.score / 10, 0.95), sentiment.score, flow_data

            elif sentiment.score <= sell_threshold:
                # Sell signal
                logger.info(f"Flow SELL signal: {flow_ticker} score={sentiment.score:.1f}, "
                           f"{len(flows)} flows, ${sentiment.total_premium:,.0f} premium")

                current_price = df.iloc[idx]['close']
                atr = self._calculate_atr(df, idx, window=14)
                stop_distance = atr * 2.0
                risk_reward = 2.0

                flow_data = {
                    'sentiment_score': sentiment.score,
                    'flow_count': len(flows),
                    'total_premium': sentiment.total_premium,
                    'bullish_flows': sentiment.bullish_flows,
                    'bearish_flows': sentiment.bearish_flows,
                    'stop_loss': current_price + stop_distance,
                    'take_profit': current_price - (stop_distance * risk_reward),
                    'risk_reward': risk_reward,
                    'entry_price': current_price
                }

                return 'short', min(abs(sentiment.score) / 10, 0.95), abs(sentiment.score), flow_data

            else:
                # Below threshold
                logger.debug(f"Flow: Score {sentiment.score:.1f} below threshold (±3.0)")
                return None, 0.5, 0.0, None

        except Exception as e:
            logger.error(f"Error generating flow signal: {e}")
            import traceback
            traceback.print_exc()
            return None, 0.5, 0.0, None

    def _simulate_flow_trade_exit(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        trade: BacktestTrade
    ) -> Optional[BacktestTrade]:
        """
        Simulate trade execution for Flow trades.

        Flow mode: 24-hour max hold (288 5m bars) for flow-based signals.
        """
        max_hold_bars = 288  # Flow: max 24 hours

        for offset in range(1, min(max_hold_bars + 1, len(df) - entry_idx)):
            idx = entry_idx + offset
            bar = df.iloc[idx]
            high = bar['high']
            low = bar['low']

            # Check exits
            if trade.direction == 'long':
                if low <= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                elif high >= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break
            else:  # short
                if high >= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                elif low <= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break

        # Timeout exit
        if trade.exit_time is None:
            trade.exit_price = df.iloc[min(entry_idx + max_hold_bars, len(df) - 1)]['close']
            trade.exit_time = df.index[min(entry_idx + max_hold_bars, len(df) - 1)]
            trade.exit_reason = 'timeout'

        # Calculate P&L
        if trade.direction == 'long':
            trade.gross_pnl = (trade.exit_price - trade.entry_price) * trade.size
        else:
            trade.gross_pnl = (trade.entry_price - trade.exit_price) * trade.size

        trade.slippage_cost = self.config.base_slippage_ticks * trade.size
        trade.commission = self.config.commission_per_trade
        trade.net_pnl = trade.gross_pnl - trade.slippage_cost - trade.commission

        trade.is_winner = trade.net_pnl > 0
        trade.pnl_pct = (trade.net_pnl / self.config.initial_capital) * 100

        return trade

    # ========================================
    # SPECIALIZED ENGINE BACKTESTS (Phase 5C)
    # ========================================
    # True backtest paths for 4 specialized strategy engines.
    # These use actual engine signal generation, NOT unified fallback.

    async def run_breakout_backtest(
        self,
        ticker: str = 'MES',
        days: int = 90,
        end_date: Optional[datetime] = None
    ) -> BacktestMetrics:
        """
        Run backtest using Breakout engine (compression + structural breakouts).

        Phase 5C: True specialized engine execution.

        Strategy:
        - Compression detection (ATR < 70% of 20-bar avg)
        - Structural level breakout (PDH/PDL, VWAP, pivots)
        - Volume expansion confirmation (> 1.3x avg)
        - Stop: Below breakout level + 1 ATR
        - Target: 2-3 ATR or next structural level
        """
        logger.info(f"Starting BREAKOUT backtest for {ticker}, {days} days")

        end = end_date or datetime.now()
        start = end - timedelta(days=days)

        df = await self.fetch_data(ticker, start, end)
        if df.empty:
            logger.error("No data available for breakout backtest")
            return BacktestMetrics()

        df = self._calculate_indicators(df)

        self.trades = []
        self.equity_curve = []
        capital = self.config.initial_capital

        # Import specialized engine
        try:
            from app.services.strategy_engines.breakout import BreakoutEngine
            from app.services.strategy_engines.base import SignalContext
            engine = BreakoutEngine('breakout_v1')
        except ImportError as e:
            logger.error(f"Failed to import BreakoutEngine: {e}")
            return BacktestMetrics()

        for idx in range(50, len(df) - 1):
            timestamp = df.index[idx]
            bar = df.iloc[idx]

            # Build SignalContext from current bar
            context = SignalContext(
                ticker=ticker,
                timestamp=timestamp,
                close=bar['close'],
                high=bar['high'],
                low=bar['low'],
                open=bar['open'],
                volume=bar.get('volume', 0),
                df=df.iloc[:idx+1]
            )

            # Generate signal using TRUE breakout engine
            signal = engine.generate_signal(context)

            if signal.direction in ['long', 'short'] and signal.is_valid:
                size = self._calculate_position_size(ticker, signal.entry_price, signal.stop_loss, capital)

                trade = BacktestTrade(
                    entry_time=timestamp,
                    ticker=ticker,
                    direction=signal.direction,
                    entry_price=signal.entry_price,
                    size=size,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    risk_reward=signal.risk_reward_ratio,
                    ensemble_prob=signal.confidence,
                    signal_strength=signal.confidence,
                    engine_type='breakout'  # TRUE engine attribution
                )

                trade = self._simulate_specialized_trade_exit(df, idx, trade, max_hold_bars=48)

                if trade and trade.exit_time:
                    self.trades.append(trade)
                    capital += trade.net_pnl
                    self.equity_curve.append((trade.exit_time, capital))

            if len(self.equity_curve) == 0 or self.equity_curve[-1][0] != timestamp:
                self.equity_curve.append((timestamp, capital))

        self.metrics = self._calculate_metrics()
        logger.info(f"Breakout backtest complete: {self.metrics.total_trades} trades, "
                   f"Sharpe={self.metrics.sharpe_ratio:.2f}, Win Rate={self.metrics.win_rate:.1f}%")
        return self.metrics

    async def run_trend_backtest(
        self,
        ticker: str = 'MES',
        days: int = 90,
        end_date: Optional[datetime] = None
    ) -> BacktestMetrics:
        """
        Run backtest using Trend engine (pullback entries in trends).

        Phase 5C: True specialized engine execution.

        Strategy:
        - Trend detection via EMA alignment (9 > 21 > 50)
        - Pullback entry (price touches/crosses EMAs)
        - Volume confirmation on pullback
        - Stop: Below structure/EMA + 1 ATR
        - Target: Prior high/low or measured move
        """
        logger.info(f"Starting TREND backtest for {ticker}, {days} days")

        end = end_date or datetime.now()
        start = end - timedelta(days=days)

        df = await self.fetch_data(ticker, start, end)
        if df.empty:
            logger.error("No data available for trend backtest")
            return BacktestMetrics()

        df = self._calculate_indicators(df)

        self.trades = []
        self.equity_curve = []
        capital = self.config.initial_capital

        try:
            from app.services.strategy_engines.trend import TrendEngine
            from app.services.strategy_engines.base import SignalContext
            engine = TrendEngine('trend_v1')
        except ImportError as e:
            logger.error(f"Failed to import TrendEngine: {e}")
            return BacktestMetrics()

        for idx in range(50, len(df) - 1):
            timestamp = df.index[idx]
            bar = df.iloc[idx]

            context = SignalContext(
                ticker=ticker,
                timestamp=timestamp,
                close=bar['close'],
                high=bar['high'],
                low=bar['low'],
                open=bar['open'],
                volume=bar.get('volume', 0),
                df=df.iloc[:idx+1]
            )

            signal = engine.generate_signal(context)

            if signal.direction in ['long', 'short'] and signal.is_valid:
                size = self._calculate_position_size(ticker, signal.entry_price, signal.stop_loss, capital)

                trade = BacktestTrade(
                    entry_time=timestamp,
                    ticker=ticker,
                    direction=signal.direction,
                    entry_price=signal.entry_price,
                    size=size,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    risk_reward=signal.risk_reward_ratio,
                    ensemble_prob=signal.confidence,
                    signal_strength=signal.confidence,
                    engine_type='trend'  # TRUE engine attribution
                )

                trade = self._simulate_specialized_trade_exit(df, idx, trade, max_hold_bars=72)

                if trade and trade.exit_time:
                    self.trades.append(trade)
                    capital += trade.net_pnl
                    self.equity_curve.append((trade.exit_time, capital))

            if len(self.equity_curve) == 0 or self.equity_curve[-1][0] != timestamp:
                self.equity_curve.append((timestamp, capital))

        self.metrics = self._calculate_metrics()
        logger.info(f"Trend backtest complete: {self.metrics.total_trades} trades, "
                   f"Sharpe={self.metrics.sharpe_ratio:.2f}, Win Rate={self.metrics.win_rate:.1f}%")
        return self.metrics

    async def run_mean_reversion_backtest(
        self,
        ticker: str = 'MES',
        days: int = 90,
        end_date: Optional[datetime] = None
    ) -> BacktestMetrics:
        """
        Run backtest using Mean Reversion engine.

        Phase 5C: True specialized engine execution.

        Strategy:
        - Bollinger Band extremes (price touches +/- 2 std)
        - RSI confirmation (oversold < 30, overbought > 70)
        - Regime confirmation (ranging or mean-reverting)
        - Stop: Beyond extreme + 0.5 ATR
        - Target: Middle Bollinger Band or fair value
        """
        logger.info(f"Starting MEAN REVERSION backtest for {ticker}, {days} days")

        end = end_date or datetime.now()
        start = end - timedelta(days=days)

        df = await self.fetch_data(ticker, start, end)
        if df.empty:
            logger.error("No data available for mean reversion backtest")
            return BacktestMetrics()

        df = self._calculate_indicators(df)

        self.trades = []
        self.equity_curve = []
        capital = self.config.initial_capital

        try:
            from app.services.strategy_engines.mean_reversion import MeanReversionEngine
            from app.services.strategy_engines.base import SignalContext
            engine = MeanReversionEngine('mean_reversion_v1')
        except ImportError as e:
            logger.error(f"Failed to import MeanReversionEngine: {e}")
            return BacktestMetrics()

        for idx in range(50, len(df) - 1):
            timestamp = df.index[idx]
            bar = df.iloc[idx]

            context = SignalContext(
                ticker=ticker,
                timestamp=timestamp,
                close=bar['close'],
                high=bar['high'],
                low=bar['low'],
                open=bar['open'],
                volume=bar.get('volume', 0),
                df=df.iloc[:idx+1]
            )

            signal = engine.generate_signal(context)

            if signal.direction in ['long', 'short'] and signal.is_valid:
                size = self._calculate_position_size(ticker, signal.entry_price, signal.stop_loss, capital)

                trade = BacktestTrade(
                    entry_time=timestamp,
                    ticker=ticker,
                    direction=signal.direction,
                    entry_price=signal.entry_price,
                    size=size,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    risk_reward=signal.risk_reward_ratio,
                    ensemble_prob=signal.confidence,
                    signal_strength=signal.confidence,
                    engine_type='mean_reversion'  # TRUE engine attribution
                )

                trade = self._simulate_specialized_trade_exit(df, idx, trade, max_hold_bars=36)

                if trade and trade.exit_time:
                    self.trades.append(trade)
                    capital += trade.net_pnl
                    self.equity_curve.append((trade.exit_time, capital))

            if len(self.equity_curve) == 0 or self.equity_curve[-1][0] != timestamp:
                self.equity_curve.append((timestamp, capital))

        self.metrics = self._calculate_metrics()
        logger.info(f"Mean Reversion backtest complete: {self.metrics.total_trades} trades, "
                   f"Sharpe={self.metrics.sharpe_ratio:.2f}, Win Rate={self.metrics.win_rate:.1f}%")
        return self.metrics

    async def run_liquidity_reversal_backtest(
        self,
        ticker: str = 'MES',
        days: int = 90,
        end_date: Optional[datetime] = None
    ) -> BacktestMetrics:
        """
        Run backtest using Liquidity Reversal engine (stop hunts).

        Phase 5C: True specialized engine execution.

        Strategy:
        - Equal highs/lows detection (liquidity pools)
        - Sweep beyond levels (stop hunt)
        - Rapid reversal confirmation (close back inside range)
        - Stop: Beyond sweep extreme
        - Target: Opposite liquidity pool or 2-3 ATR
        """
        logger.info(f"Starting LIQUIDITY REVERSAL backtest for {ticker}, {days} days")

        end = end_date or datetime.now()
        start = end - timedelta(days=days)

        df = await self.fetch_data(ticker, start, end)
        if df.empty:
            logger.error("No data available for liquidity reversal backtest")
            return BacktestMetrics()

        df = self._calculate_indicators(df)

        self.trades = []
        self.equity_curve = []
        capital = self.config.initial_capital

        try:
            from app.services.strategy_engines.liquidity_reversal import LiquidityReversalEngine
            from app.services.strategy_engines.base import SignalContext
            engine = LiquidityReversalEngine('liquidity_reversal_v1')
        except ImportError as e:
            logger.error(f"Failed to import LiquidityReversalEngine: {e}")
            return BacktestMetrics()

        for idx in range(50, len(df) - 1):
            timestamp = df.index[idx]
            bar = df.iloc[idx]

            context = SignalContext(
                ticker=ticker,
                timestamp=timestamp,
                close=bar['close'],
                high=bar['high'],
                low=bar['low'],
                open=bar['open'],
                volume=bar.get('volume', 0),
                df=df.iloc[:idx+1]
            )

            signal = engine.generate_signal(context)

            if signal.direction in ['long', 'short'] and signal.is_valid:
                size = self._calculate_position_size(ticker, signal.entry_price, signal.stop_loss, capital)

                trade = BacktestTrade(
                    entry_time=timestamp,
                    ticker=ticker,
                    direction=signal.direction,
                    entry_price=signal.entry_price,
                    size=size,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    risk_reward=signal.risk_reward_ratio,
                    ensemble_prob=signal.confidence,
                    signal_strength=signal.confidence,
                    engine_type='liquidity_reversal'  # TRUE engine attribution
                )

                trade = self._simulate_specialized_trade_exit(df, idx, trade, max_hold_bars=24)

                if trade and trade.exit_time:
                    self.trades.append(trade)
                    capital += trade.net_pnl
                    self.equity_curve.append((trade.exit_time, capital))

            if len(self.equity_curve) == 0 or self.equity_curve[-1][0] != timestamp:
                self.equity_curve.append((timestamp, capital))

        self.metrics = self._calculate_metrics()
        logger.info(f"Liquidity Reversal backtest complete: {self.metrics.total_trades} trades, "
                   f"Sharpe={self.metrics.sharpe_ratio:.2f}, Win Rate={self.metrics.win_rate:.1f}%")
        return self.metrics

    def _simulate_specialized_trade_exit(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        trade: BacktestTrade,
        max_hold_bars: int = 48
    ) -> Optional[BacktestTrade]:
        """
        Generic trade exit simulation for specialized engines.

        Args:
            df: Price data
            entry_idx: Entry bar index
            trade: Trade to simulate
            max_hold_bars: Maximum holding period in bars
        """
        for offset in range(1, min(max_hold_bars + 1, len(df) - entry_idx)):
            idx = entry_idx + offset
            bar = df.iloc[idx]
            high = bar['high']
            low = bar['low']

            if trade.direction == 'long':
                if low <= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                elif high >= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break
            else:  # short
                if high >= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                elif low <= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break

        # Timeout exit
        if trade.exit_time is None:
            exit_idx = min(entry_idx + max_hold_bars, len(df) - 1)
            trade.exit_price = df.iloc[exit_idx]['close']
            trade.exit_time = df.index[exit_idx]
            trade.exit_reason = 'timeout'

        # Calculate P&L
        if trade.direction == 'long':
            trade.gross_pnl = (trade.exit_price - trade.entry_price) * trade.size
        else:
            trade.gross_pnl = (trade.entry_price - trade.exit_price) * trade.size

        trade.slippage_cost = self.config.base_slippage_ticks * trade.size
        trade.commission = self.config.commission_per_trade
        trade.net_pnl = trade.gross_pnl - trade.slippage_cost - trade.commission
        trade.is_winner = trade.net_pnl > 0
        trade.pnl_pct = (trade.net_pnl / self.config.initial_capital) * 100

        return trade

    # ========================================
    # PYRAMID DYNAMIC STRATEGY BACKTEST
    # ========================================

    async def run_pyramid_backtest(
        self,
        ticker: str = 'MES',
        days: int = 90,
        end_date: Optional[datetime] = None
    ) -> BacktestMetrics:
        """
        Run backtest using Pyramid Dynamic Strategy.

        Phase 5C: True pyramid engine with regime-based parameters.

        Strategy:
        - 2%/2% stops for trending (or regime-adjusted)
        - Pullback-based pyramid entries (50% retracement + 2 bars)
        - Max 3 pyramid positions
        - Position sizing multipliers per regime
        """
        logger.info(f"Starting PYRAMID DYNAMIC backtest for {ticker}, {days} days")

        end = end_date or datetime.now()
        start = end - timedelta(days=days)

        df = await self.fetch_data(ticker, start, end)
        if df.empty:
            logger.error("No data available for pyramid backtest")
            return BacktestMetrics()

        df = self._calculate_indicators(df)

        self.trades = []
        self.equity_curve = []
        capital = self.config.initial_capital

        # Import pyramid strategy handler
        try:
            from app.services.pyramid_strategy import PyramidStrategyHandler
            pyramid_handler = PyramidStrategyHandler()
        except ImportError as e:
            logger.error(f"Failed to import PyramidStrategyHandler: {e}")
            return BacktestMetrics()

        # Pyramid state tracking
        active_positions = []  # List of open pyramid entries
        max_pyramid_positions = 3
        last_signal_direction = None
        pullback_detected = False
        continuation_count = 0

        for idx in range(50, len(df) - 1):
            timestamp = df.index[idx]
            bar = df.iloc[idx]
            close = bar['close']
            high = bar['high']
            low = bar['low']

            # Detect regime (simplified)
            regime = self._detect_simple_regime(df, idx)

            # Get pyramid parameters for this regime
            params = pyramid_handler.get_parameters(regime)

            # Calculate stops/targets based on percentage
            stop_distance = close * (params.stop_pct / 100)
            target_distance = close * (params.target_pct / 100)

            # Generate signal using momentum indicators
            direction, prob, strength = self._generate_pyramid_signal(df, idx, params)

            # Check for pyramid entry conditions
            if direction and direction != 'none' and prob >= 0.55:
                # Check if we can add to position
                can_add = len(active_positions) < max_pyramid_positions

                # Check pullback condition for pyramiding
                if len(active_positions) > 0:
                    # Need pullback before adding
                    if self._check_pullback_condition(df, idx, direction, params.pullback_pct):
                        pullback_detected = True

                    if pullback_detected and self._check_continuation(df, idx, direction, params.continuation_bars):
                        can_add = True
                        continuation_count = 0
                        pullback_detected = False
                    else:
                        can_add = False

                if can_add:
                    size = self._calculate_position_size(ticker, close, close - stop_distance, capital)
                    size = size * params.size_mult  # Apply regime size multiplier

                    if direction == 'long':
                        stop_loss = close - stop_distance
                        take_profit = close + target_distance
                    else:
                        stop_loss = close + stop_distance
                        take_profit = close - target_distance

                    trade = BacktestTrade(
                        entry_time=timestamp,
                        ticker=ticker,
                        direction=direction,
                        entry_price=close,
                        size=size,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        risk_reward=params.target_pct / params.stop_pct,
                        ensemble_prob=prob,
                        signal_strength=strength,
                        regime=regime,
                        engine_type='pyramid',
                        scaled_in=len(active_positions) > 0
                    )

                    # Simulate trade
                    trade = self._simulate_pyramid_trade_exit(df, idx, trade, params)

                    if trade and trade.exit_time:
                        self.trades.append(trade)
                        capital += trade.net_pnl
                        self.equity_curve.append((trade.exit_time, capital))

            if len(self.equity_curve) == 0 or self.equity_curve[-1][0] != timestamp:
                self.equity_curve.append((timestamp, capital))

        self.metrics = self._calculate_metrics()
        logger.info(f"Pyramid backtest complete: {self.metrics.total_trades} trades, "
                   f"Sharpe={self.metrics.sharpe_ratio:.2f}, Win Rate={self.metrics.win_rate:.1f}%")
        return self.metrics

    def _detect_simple_regime(self, df: pd.DataFrame, idx: int) -> str:
        """Simplified regime detection for pyramid backtest."""
        if idx < 20:
            return 'neutral'

        close = df.iloc[idx]['close']
        sma20 = df.iloc[idx-20:idx]['close'].mean()
        sma50 = df.iloc[max(0, idx-50):idx]['close'].mean() if idx >= 50 else sma20

        # Calculate recent volatility
        returns = df.iloc[idx-20:idx]['close'].pct_change().dropna()
        volatility = returns.std() * 100 if len(returns) > 0 else 0

        if close > sma20 > sma50:
            return 'trending_up'
        elif close < sma20 < sma50:
            return 'trending_down'
        elif volatility > 2.0:
            return 'volatile'
        elif abs(close - sma20) / sma20 < 0.005:
            return 'ranging'
        else:
            return 'neutral'

    def _generate_pyramid_signal(
        self,
        df: pd.DataFrame,
        idx: int,
        params
    ) -> Tuple[str, float, float]:
        """Generate pyramid entry signal."""
        if idx < 20:
            return None, 0.5, 0.0

        close = df.iloc[idx]['close']
        prev_close = df.iloc[idx-1]['close']

        # EMA crossover
        ema9 = df.iloc[idx-9:idx+1]['close'].ewm(span=9).mean().iloc[-1]
        ema21 = df.iloc[idx-21:idx+1]['close'].ewm(span=21).mean().iloc[-1]

        # Momentum
        rsi = self._calc_rsi(df['close'].iloc[idx-14:idx+1])

        direction = None
        prob = 0.5
        strength = 0.0

        if ema9 > ema21 and close > prev_close and rsi > 50:
            direction = 'long'
            prob = min(0.85, 0.5 + (ema9 - ema21) / close * 10 + (rsi - 50) / 100)
            strength = (ema9 - ema21) / close * 100
        elif ema9 < ema21 and close < prev_close and rsi < 50:
            direction = 'short'
            prob = min(0.85, 0.5 + (ema21 - ema9) / close * 10 + (50 - rsi) / 100)
            strength = (ema21 - ema9) / close * 100

        return direction, prob, strength

    def _calc_rsi(self, prices, period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50.0

        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain.iloc[-1] / loss.iloc[-1] if loss.iloc[-1] != 0 else 100
        rsi = 100 - (100 / (1 + rs))

        return float(rsi) if not np.isnan(rsi) else 50.0

    def _check_pullback_condition(
        self,
        df: pd.DataFrame,
        idx: int,
        direction: str,
        pullback_pct: float
    ) -> bool:
        """Check if price has pulled back enough for pyramid entry."""
        if idx < 10:
            return False

        recent_high = df.iloc[idx-10:idx]['high'].max()
        recent_low = df.iloc[idx-10:idx]['low'].min()
        current_close = df.iloc[idx]['close']
        range_size = recent_high - recent_low

        if direction == 'long':
            # For long, need pullback from recent high
            pullback = (recent_high - current_close) / range_size if range_size > 0 else 0
            return pullback >= pullback_pct
        else:
            # For short, need pullback from recent low
            pullback = (current_close - recent_low) / range_size if range_size > 0 else 0
            return pullback >= pullback_pct

    def _check_continuation(
        self,
        df: pd.DataFrame,
        idx: int,
        direction: str,
        bars_required: int
    ) -> bool:
        """Check if price has shown continuation after pullback."""
        if idx < bars_required:
            return False

        continuation = 0
        for i in range(bars_required):
            bar_idx = idx - bars_required + i + 1
            close = df.iloc[bar_idx]['close']
            prev_close = df.iloc[bar_idx - 1]['close']

            if direction == 'long' and close > prev_close:
                continuation += 1
            elif direction == 'short' and close < prev_close:
                continuation += 1

        return continuation >= bars_required

    def _simulate_pyramid_trade_exit(
        self,
        df: pd.DataFrame,
        entry_idx: int,
        trade: BacktestTrade,
        params
    ) -> Optional[BacktestTrade]:
        """Simulate pyramid trade exit with percentage-based stops."""
        max_hold_bars = 96  # 8 hours max hold for pyramid

        for offset in range(1, min(max_hold_bars + 1, len(df) - entry_idx)):
            idx = entry_idx + offset
            bar = df.iloc[idx]
            high = bar['high']
            low = bar['low']

            if trade.direction == 'long':
                if low <= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                elif high >= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break
            else:
                if high >= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'stop'
                    break
                elif low <= trade.take_profit:
                    trade.exit_price = trade.take_profit
                    trade.exit_time = df.index[idx]
                    trade.exit_reason = 'target'
                    break

        # Timeout exit
        if trade.exit_time is None:
            exit_idx = min(entry_idx + max_hold_bars, len(df) - 1)
            trade.exit_price = df.iloc[exit_idx]['close']
            trade.exit_time = df.index[exit_idx]
            trade.exit_reason = 'timeout'

        # Calculate P&L
        if trade.direction == 'long':
            trade.gross_pnl = (trade.exit_price - trade.entry_price) * trade.size
        else:
            trade.gross_pnl = (trade.entry_price - trade.exit_price) * trade.size

        trade.slippage_cost = self.config.base_slippage_ticks * trade.size
        trade.commission = self.config.commission_per_trade
        trade.net_pnl = trade.gross_pnl - trade.slippage_cost - trade.commission
        trade.is_winner = trade.net_pnl > 0
        trade.pnl_pct = (trade.net_pnl / self.config.initial_capital) * 100

        return trade

    def _calculate_metrics(self) -> BacktestMetrics:
        """Calculate backtest performance metrics."""
        metrics = BacktestMetrics()

        if not self.trades:
            return metrics

        trades_df = pd.DataFrame([asdict(t) for t in self.trades])

        # Period
        metrics.start_date = str(self.trades[0].entry_time.date())
        metrics.end_date = str(self.trades[-1].exit_time.date())
        metrics.trading_days = (
            self.trades[-1].exit_time - self.trades[0].entry_time
        ).days

        # Trade counts
        metrics.total_trades = len(self.trades)
        metrics.winning_trades = sum(1 for t in self.trades if t.is_winner)
        metrics.losing_trades = metrics.total_trades - metrics.winning_trades
        metrics.win_rate = metrics.winning_trades / metrics.total_trades * 100

        # P&L
        pnls = [t.net_pnl for t in self.trades]
        metrics.gross_profit = sum(p for p in pnls if p > 0)
        metrics.gross_loss = abs(sum(p for p in pnls if p < 0))
        metrics.net_profit = sum(pnls)

        if metrics.gross_loss > 0:
            metrics.profit_factor = metrics.gross_profit / metrics.gross_loss

        metrics.avg_trade = np.mean(pnls)
        winning_pnls = [p for p in pnls if p > 0]
        losing_pnls = [p for p in pnls if p < 0]

        if winning_pnls:
            metrics.avg_win = np.mean(winning_pnls)
            metrics.largest_win = max(winning_pnls)
        if losing_pnls:
            metrics.avg_loss = np.mean(losing_pnls)
            metrics.largest_loss = min(losing_pnls)

        # Expectancy
        if metrics.win_rate > 0:
            metrics.expectancy = (
                (metrics.win_rate / 100 * metrics.avg_win) +
                ((100 - metrics.win_rate) / 100 * metrics.avg_loss)
            )

        # Returns
        metrics.total_return_pct = (
            metrics.net_profit / self.config.initial_capital * 100
        )

        if metrics.trading_days > 0:
            metrics.cagr = (
                ((self.config.initial_capital + metrics.net_profit) /
                 self.config.initial_capital) ** (365 / metrics.trading_days) - 1
            ) * 100

        # Sharpe ratio (daily)
        daily_returns = np.array([])
        if len(pnls) > 1:
            daily_returns = np.array(pnls) / self.config.initial_capital
            if np.std(daily_returns) > 0:
                metrics.sharpe_ratio = (
                    np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
                )

            # Sortino ratio (inside same block to ensure daily_returns exists)
            negative_returns = [r for r in daily_returns if r < 0]
            if negative_returns:
                downside_std = np.std(negative_returns)
                if downside_std > 0:
                    metrics.sortino_ratio = (
                        np.mean(daily_returns) / downside_std * np.sqrt(252)
                    )

        # Drawdown
        equity = np.array([e[1] for e in self.equity_curve])
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak * 100
        metrics.max_drawdown_pct = np.max(drawdown)
        metrics.avg_drawdown_pct = np.mean(drawdown)

        # Calmar
        if metrics.max_drawdown_pct > 0:
            metrics.calmar_ratio = metrics.cagr / metrics.max_drawdown_pct

        # Regime breakdown
        regime_trades = {}
        for t in self.trades:
            if t.regime not in regime_trades:
                regime_trades[t.regime] = []
            regime_trades[t.regime].append(t)

        for regime, trades in regime_trades.items():
            wins = sum(1 for t in trades if t.is_winner)
            metrics.regime_win_rates[regime] = wins / len(trades) * 100
            metrics.regime_pnl[regime] = sum(t.net_pnl for t in trades)

        # Costs
        metrics.total_slippage = sum(t.slippage_cost for t in self.trades)
        metrics.total_commission = sum(t.commission for t in self.trades)

        # Flow confirmation metrics
        flow_confirmed_trades = [t for t in self.trades if t.flow_confirmed]
        flow_unconfirmed_trades = [t for t in self.trades if not t.flow_confirmed]

        metrics.flow_confirmed_trades = len(flow_confirmed_trades)

        if flow_confirmed_trades:
            fc_wins = sum(1 for t in flow_confirmed_trades if t.is_winner)
            metrics.flow_confirmed_win_rate = fc_wins / len(flow_confirmed_trades) * 100
            metrics.flow_confirmed_pnl = sum(t.net_pnl for t in flow_confirmed_trades)

        if flow_unconfirmed_trades:
            fu_wins = sum(1 for t in flow_unconfirmed_trades if t.is_winner)
            metrics.flow_unconfirmed_win_rate = fu_wins / len(flow_unconfirmed_trades) * 100
            metrics.flow_unconfirmed_pnl = sum(t.net_pnl for t in flow_unconfirmed_trades)

        # Holding time
        holding_times = [
            (t.exit_time - t.entry_time).total_seconds() / 3600
            for t in self.trades if t.exit_time
        ]
        if holding_times:
            metrics.avg_holding_time_hours = np.mean(holding_times)

        return metrics

    # ========================================
    # WALK-FORWARD VALIDATION
    # ========================================

    async def run_walk_forward(
        self,
        ticker: str = 'MES',
        total_days: int = 180
    ) -> List[WalkForwardResult]:
        """Run walk-forward validation."""
        logger.info(f"Starting walk-forward validation: {self.config.wf_folds} folds")

        end = datetime.now()
        start = end - timedelta(days=total_days)

        # Fetch all data
        df = await self.fetch_data(ticker, start, end)
        df = self._calculate_indicators(df)

        fold_size = len(df) // self.config.wf_folds
        train_size = int(fold_size * 0.75)
        test_size = fold_size - train_size

        results = []

        for fold in range(self.config.wf_folds):
            fold_start = fold * fold_size
            train_end = fold_start + train_size
            test_end = train_end + test_size

            train_df = df.iloc[fold_start:train_end]
            test_df = df.iloc[train_end:test_end]

            # Run on train
            train_trades = self._backtest_period(train_df)
            train_metrics = self._calculate_period_metrics(train_trades)

            # Run on test
            test_trades = self._backtest_period(test_df)
            test_metrics = self._calculate_period_metrics(test_trades)

            result = WalkForwardResult(
                fold=fold + 1,
                train_start=str(train_df.index[0].date()),
                train_end=str(train_df.index[-1].date()),
                test_start=str(test_df.index[0].date()),
                test_end=str(test_df.index[-1].date()),
                train_sharpe=train_metrics.get('sharpe', 0),
                test_sharpe=test_metrics.get('sharpe', 0),
                train_win_rate=train_metrics.get('win_rate', 0),
                test_win_rate=test_metrics.get('win_rate', 0),
                is_valid=test_metrics.get('sharpe', 0) > train_metrics.get('sharpe', 0) * 0.5
            )

            results.append(result)

            logger.info(
                f"Fold {fold+1}: Train Sharpe={result.train_sharpe:.2f}, "
                f"Test Sharpe={result.test_sharpe:.2f}, Valid={result.is_valid}"
            )

        self.walk_forward_results = results
        return results

    def _backtest_period(self, df: pd.DataFrame) -> List[BacktestTrade]:
        """Backtest a specific period."""
        trades = []
        capital = self.config.initial_capital

        for idx in range(50, len(df) - 1):
            regime, _ = self._detect_regime(df, idx)
            direction, prob, strength = self._generate_signal(df, idx, regime)

            if direction and strength >= self.config.min_signal_strength:
                trade = self._execute_trade(
                    df, idx, direction, regime, prob, strength, capital
                )
                if trade:
                    trades.append(trade)
                    capital += trade.net_pnl

        return trades

    def _calculate_period_metrics(self, trades: List[BacktestTrade]) -> Dict[str, float]:
        """Calculate metrics for a period."""
        if not trades:
            return {'sharpe': 0, 'win_rate': 0}

        pnls = [t.net_pnl for t in trades]
        daily_returns = np.array(pnls) / self.config.initial_capital

        sharpe = 0
        if np.std(daily_returns) > 0:
            sharpe = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)

        win_rate = sum(1 for t in trades if t.is_winner) / len(trades) * 100

        return {'sharpe': sharpe, 'win_rate': win_rate}

    # ========================================
    # MONTE CARLO
    # ========================================

    def run_monte_carlo(self) -> Dict[str, float]:
        """Run Monte Carlo simulation on trade results."""
        if not self.trades:
            return {}

        pnls = [t.net_pnl for t in self.trades]
        n_sims = self.config.mc_simulations

        # Shuffle and accumulate
        final_equities = []
        max_drawdowns = []

        for _ in range(n_sims):
            shuffled = np.random.permutation(pnls)
            equity = self.config.initial_capital + np.cumsum(shuffled)
            final_equities.append(equity[-1])

            peak = np.maximum.accumulate(equity)
            dd = (peak - equity) / peak * 100
            max_drawdowns.append(np.max(dd))

        results = {
            'median_return': (np.median(final_equities) - self.config.initial_capital) / self.config.initial_capital * 100,
            '5th_percentile_return': (np.percentile(final_equities, 5) - self.config.initial_capital) / self.config.initial_capital * 100,
            '95th_percentile_return': (np.percentile(final_equities, 95) - self.config.initial_capital) / self.config.initial_capital * 100,
            'worst_case_dd': np.percentile(max_drawdowns, 95),
            'median_dd': np.median(max_drawdowns),
        }

        if self.metrics:
            self.metrics.mc_worst_case_dd = results['worst_case_dd']
            self.metrics.mc_median_return = results['median_return']
            self.metrics.mc_5th_percentile_return = results['5th_percentile_return']

        logger.info(
            f"Monte Carlo: Median Return={results['median_return']:.1f}%, "
            f"Worst DD={results['worst_case_dd']:.1f}%"
        )

        return results

    # ========================================
    # EXPORT
    # ========================================

    def export_results(self, filepath: str):
        """Export backtest results to JSON."""
        data = {
            'config': asdict(self.config),
            'metrics': asdict(self.metrics) if self.metrics else {},
            'walk_forward': [asdict(r) for r in self.walk_forward_results],
            'trades': [
                {
                    'entry_time': str(t.entry_time),
                    'exit_time': str(t.exit_time),
                    'direction': t.direction,
                    'entry_price': t.entry_price,
                    'exit_price': t.exit_price,
                    'net_pnl': t.net_pnl,
                    'regime': t.regime,
                    'is_winner': t.is_winner,
                    'exit_reason': t.exit_reason,
                }
                for t in self.trades
            ],
            'equity_curve': [
                {'timestamp': str(ts), 'equity': eq}
                for ts, eq in self.equity_curve[-500:]  # Last 500 points
            ],
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        logger.info(f"Results exported to {filepath}")

    def get_summary(self) -> str:
        """Get human-readable summary."""
        if not self.metrics:
            return "No backtest results available"

        m = self.metrics
        return f"""
SmartFlow Backtest Summary
==========================
Period: {m.start_date} to {m.end_date} ({m.trading_days} days)

PERFORMANCE
-----------
Total Return: {m.total_return_pct:.2f}%
CAGR: {m.cagr:.2f}%
Sharpe Ratio: {m.sharpe_ratio:.2f}
Sortino Ratio: {m.sortino_ratio:.2f}
Calmar Ratio: {m.calmar_ratio:.2f}

DRAWDOWN
--------
Max Drawdown: {m.max_drawdown_pct:.2f}%
Avg Drawdown: {m.avg_drawdown_pct:.2f}%
MC Worst Case DD: {m.mc_worst_case_dd:.2f}%

TRADES
------
Total Trades: {m.total_trades}
Win Rate: {m.win_rate:.1f}%
Profit Factor: {m.profit_factor:.2f}
Expectancy: ${m.expectancy:.2f}

P&L
---
Net Profit: ${m.net_profit:.2f}
Avg Trade: ${m.avg_trade:.2f}
Avg Win: ${m.avg_win:.2f}
Avg Loss: ${m.avg_loss:.2f}

COSTS
-----
Total Slippage: ${m.total_slippage:.2f}
Total Commission: ${m.total_commission:.2f}

REGIME BREAKDOWN
----------------
{chr(10).join(f'  {r}: {wr:.1f}% WR, ${pnl:.2f} P&L' for r, (wr, pnl) in zip(m.regime_win_rates.keys(), zip(m.regime_win_rates.values(), m.regime_pnl.values())))}

FLOW CONFIRMATION
-----------------
Flow Confirmed Trades: {m.flow_confirmed_trades}
Flow Confirmed WR: {m.flow_confirmed_win_rate:.1f}%
Flow Unconfirmed WR: {m.flow_unconfirmed_win_rate:.1f}%
Flow Confirmed P&L: ${m.flow_confirmed_pnl:.2f}
Flow Unconfirmed P&L: ${m.flow_unconfirmed_pnl:.2f}
"""


# CLI entry point
async def main():
    """Run backtest from CLI."""
    import argparse

    parser = argparse.ArgumentParser(description='SmartFlow Backtest')
    parser.add_argument('--ticker', default='MES', help='Ticker symbol')
    parser.add_argument('--days', type=int, default=90, help='Days to backtest')
    parser.add_argument('--walk-forward', action='store_true', help='Run walk-forward')
    parser.add_argument('--monte-carlo', action='store_true', help='Run Monte Carlo')
    parser.add_argument('--export', type=str, help='Export results to file')
    args = parser.parse_args()

    bt = SmartFlowBacktester()

    # Run backtest
    metrics = await bt.run_backtest(args.ticker, args.days)

    # Walk-forward
    if args.walk_forward:
        await bt.run_walk_forward(args.ticker, args.days * 2)

    # Monte Carlo
    if args.monte_carlo:
        bt.run_monte_carlo()

    # Print summary
    print(bt.get_summary())

    # Export
    if args.export:
        bt.export_results(args.export)


if __name__ == "__main__":
    asyncio.run(main())
