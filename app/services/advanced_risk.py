"""
Advanced Risk Management - 2026 Best Practices
===============================================

Enhanced risk controls beyond basic Kelly:
- Realistic tick-level slippage model (ATR/vol-based)
- CVaR (Conditional Value at Risk) optimization
- Position stacking limits + sector neutrality
- Strategy decay tracking with auto-reduction
- Dynamic position sizing with multiple factors

Pi5 optimized: NumPy vectorized calculations
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)

# Try scipy for statistical functions
try:
    from scipy import stats
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class SlippageModel(Enum):
    """Slippage model types"""
    FIXED = "fixed"  # Fixed tick slippage
    ATR_BASED = "atr_based"  # Based on ATR
    VOLUME_BASED = "volume_based"  # Based on volume/liquidity
    ADAPTIVE = "adaptive"  # Combines multiple factors


@dataclass
class SlippageEstimate:
    """Estimated slippage for a trade"""
    ticker: str
    timestamp: datetime

    # Slippage estimates
    expected_ticks: float = 0.0
    expected_bps: float = 0.0  # Basis points
    expected_dollars: float = 0.0

    # Distribution
    slippage_min_ticks: float = 0.0
    slippage_max_ticks: float = 0.0
    slippage_std_ticks: float = 0.0

    # Factors
    volatility_factor: float = 1.0
    volume_factor: float = 1.0
    time_of_day_factor: float = 1.0

    # Model used
    model: SlippageModel = SlippageModel.FIXED


@dataclass
class CVaRResult:
    """CVaR optimization result"""
    ticker: str
    timestamp: datetime

    # VaR and CVaR
    var_95: float = 0.0  # Value at Risk 95%
    var_99: float = 0.0  # Value at Risk 99%
    cvar_95: float = 0.0  # Conditional VaR 95% (Expected Shortfall)
    cvar_99: float = 0.0

    # Position sizing
    max_position_for_cvar: float = 0.0  # Max position to stay within CVaR limit
    recommended_position_pct: float = 0.0

    # Historical simulation
    worst_case_pnl: float = 0.0
    scenarios_tested: int = 0


@dataclass
class PositionLimits:
    """Position and sector limits"""
    # Per-position limits
    max_positions: int = 5  # Max concurrent positions
    max_per_ticker_pct: float = 25.0  # Max 25% in single ticker
    max_per_sector_pct: float = 50.0  # Max 50% in single sector

    # Sector definitions
    sectors: Dict[str, List[str]] = field(default_factory=lambda: {
        'equity_index': ['MES', 'NQ', 'RTY', 'MYM', 'SPY', 'QQQ', 'IWM', 'DIA'],
        'metals': ['GC', 'MGC', 'GLD', 'SI'],
        'energy': ['CL', 'MCL', 'NG'],
        'crypto': ['BTCUSD', 'ETHUSD', 'SOLUSD'],
        'bonds': ['ZB', 'ZN', 'TLT'],
        'forex': ['EURUSD', 'GBPUSD', 'USDJPY'],
    })

    # Correlation limits
    max_correlated_pct: float = 60.0  # Max 60% in correlated assets
    correlation_threshold: float = 0.7


@dataclass
class StackingCheck:
    """Result of position stacking check"""
    can_add_position: bool = True
    current_positions: int = 0
    sector_exposure: Dict[str, float] = field(default_factory=dict)
    correlation_exposure: float = 0.0
    rejection_reason: str = ''
    recommended_size_mult: float = 1.0


@dataclass
class AdvancedRiskConfig:
    """Configuration for advanced risk management"""
    # Slippage model
    slippage_model: SlippageModel = SlippageModel.ADAPTIVE
    base_slippage_ticks: float = 2.0  # Minimum slippage
    max_slippage_ticks: float = 10.0
    slippage_vol_multiplier: float = 0.5  # Extra slippage per ATR

    # Tick values per instrument
    tick_values: Dict[str, float] = field(default_factory=lambda: {
        'MES': 1.25,  # $1.25 per tick
        'NQ': 0.50,   # $0.50 per tick
        'RTY': 2.50,  # $2.50 per tick
        'MYM': 0.50,  # $0.50 per tick
        'GC': 0.10,   # $0.10 per tick
        'CL': 0.01,   # $0.01 per tick
    })

    # CVaR parameters
    cvar_confidence: float = 0.95
    cvar_max_pct: float = 5.0  # Max 5% CVaR per position
    cvar_lookback_days: int = 60

    # Position limits
    position_limits: PositionLimits = field(default_factory=PositionLimits)

    # Decay tracking
    decay_sharpe_threshold: float = 0.5
    decay_window_days: int = 30
    decay_reduction_factor: float = 0.5

    # Monte Carlo for slippage
    n_slippage_simulations: int = 1000


class AdvancedRiskManager:
    """
    Advanced risk management with realistic slippage and CVaR.

    Features:
    - Tick-level slippage modeling (ATR-based + random)
    - CVaR/Expected Shortfall calculation
    - Position stacking limits
    - Sector/correlation neutrality checks
    - Strategy decay auto-adjustment
    """

    def __init__(self, config: Optional[AdvancedRiskConfig] = None):
        self.config = config or AdvancedRiskConfig()

        # Current positions
        self.active_positions: Dict[str, Dict] = {}

        # Historical returns for CVaR
        self.returns_history: Dict[str, deque] = {}
        self.max_history = 500

        # ATR cache for slippage
        self.atr_cache: Dict[str, float] = {}

        # Performance tracking for decay
        self.performance_history: Dict[str, deque] = {}

        # Correlation matrix
        self.correlation_matrix: Dict[str, Dict[str, float]] = {}

        logger.info(
            f"AdvancedRiskManager initialized: "
            f"slippage_model={self.config.slippage_model.value}, "
            f"cvar_confidence={self.config.cvar_confidence}"
        )

    # ========================================
    # SLIPPAGE MODEL
    # ========================================

    def estimate_slippage(
        self,
        ticker: str,
        entry_price: float,
        position_size: int,
        atr: Optional[float] = None,
        volume: Optional[float] = None,
        is_market_open: bool = True
    ) -> SlippageEstimate:
        """
        Estimate realistic slippage for a trade.

        Uses ATR and volume to estimate expected slippage distribution.

        Args:
            ticker: Symbol
            entry_price: Entry price
            position_size: Number of contracts
            atr: Average True Range (if known)
            volume: Current volume (if known)
            is_market_open: Whether market is currently open

        Returns:
            SlippageEstimate with distribution parameters
        """
        estimate = SlippageEstimate(
            ticker=ticker,
            timestamp=datetime.now(),
            model=self.config.slippage_model
        )

        # Get tick value
        tick_value = self.config.tick_values.get(ticker, 1.0)

        # Base slippage
        base_ticks = self.config.base_slippage_ticks

        # ATR-based adjustment
        estimate.volatility_factor = 1.0
        if atr is not None:
            self.atr_cache[ticker] = atr
            # Higher ATR = wider spreads = more slippage
            # Normalize ATR as percentage of price
            atr_pct = atr / entry_price if entry_price > 0 else 0
            estimate.volatility_factor = 1.0 + (atr_pct * 100 * self.config.slippage_vol_multiplier)

        elif ticker in self.atr_cache:
            atr = self.atr_cache[ticker]
            atr_pct = atr / entry_price if entry_price > 0 else 0
            estimate.volatility_factor = 1.0 + (atr_pct * 100 * self.config.slippage_vol_multiplier)

        # Volume-based adjustment
        estimate.volume_factor = 1.0
        if volume is not None:
            # Lower volume = higher slippage
            # Normalize: assume "normal" volume = 1000 contracts
            if volume > 0:
                estimate.volume_factor = max(0.5, min(2.0, 1000 / volume))

        # Time of day adjustment
        estimate.time_of_day_factor = 1.0
        if not is_market_open:
            estimate.time_of_day_factor = 1.5  # 50% more slippage outside hours

        # Size-based adjustment (larger orders = more slippage)
        size_factor = 1.0 + (position_size / 100) * 0.1  # +10% per 100 contracts

        # Combine factors
        total_factor = (
            estimate.volatility_factor *
            estimate.volume_factor *
            estimate.time_of_day_factor *
            size_factor
        )

        # Calculate expected slippage
        estimate.expected_ticks = min(
            self.config.max_slippage_ticks,
            base_ticks * total_factor
        )

        # Distribution (assume lognormal for positive slippage)
        estimate.slippage_min_ticks = base_ticks * 0.5
        estimate.slippage_max_ticks = self.config.max_slippage_ticks
        estimate.slippage_std_ticks = estimate.expected_ticks * 0.3

        # Convert to dollars
        estimate.expected_dollars = estimate.expected_ticks * tick_value * position_size

        # Convert to basis points
        if entry_price > 0:
            estimate.expected_bps = (
                estimate.expected_ticks * tick_value / entry_price
            ) * 10000

        return estimate

    def simulate_slippage(
        self,
        ticker: str,
        entry_price: float,
        position_size: int,
        n_simulations: Optional[int] = None
    ) -> np.ndarray:
        """
        Monte Carlo simulation of slippage.

        Returns array of simulated slippage values in ticks.
        """
        n = n_simulations or self.config.n_slippage_simulations

        # Get base estimate
        estimate = self.estimate_slippage(ticker, entry_price, position_size)

        # Simulate from lognormal distribution
        # Mean and std of underlying normal distribution
        mu = np.log(estimate.expected_ticks) - 0.5 * (estimate.slippage_std_ticks / estimate.expected_ticks) ** 2
        sigma = estimate.slippage_std_ticks / estimate.expected_ticks

        simulated = np.random.lognormal(mu, sigma, n)

        # Clip to min/max
        simulated = np.clip(
            simulated,
            estimate.slippage_min_ticks,
            estimate.slippage_max_ticks
        )

        return simulated

    # ========================================
    # CVAR / EXPECTED SHORTFALL
    # ========================================

    def update_returns(self, ticker: str, daily_return: float):
        """Update returns history for CVaR calculation."""
        if ticker not in self.returns_history:
            self.returns_history[ticker] = deque(maxlen=self.max_history)

        self.returns_history[ticker].append(daily_return)

    def calculate_cvar(
        self,
        ticker: str,
        position_value: float,
        confidence: Optional[float] = None
    ) -> CVaRResult:
        """
        Calculate CVaR (Conditional Value at Risk) / Expected Shortfall.

        CVaR is the expected loss given that loss exceeds VaR.
        More conservative than VaR for tail risk.

        Args:
            ticker: Symbol
            position_value: Current position value in dollars
            confidence: Confidence level (default: 0.95)

        Returns:
            CVaRResult with risk metrics
        """
        result = CVaRResult(
            ticker=ticker,
            timestamp=datetime.now()
        )

        confidence = confidence or self.config.cvar_confidence

        # Get returns history
        if ticker not in self.returns_history:
            logger.debug(f"No returns history for {ticker}")
            return result

        returns = np.array(list(self.returns_history[ticker]))

        if len(returns) < 30:
            logger.debug(f"Insufficient history for {ticker}: {len(returns)} days")
            return result

        result.scenarios_tested = len(returns)

        # Calculate VaR
        var_pctl = (1 - confidence) * 100
        result.var_95 = -np.percentile(returns, 5)  # 95% VaR
        result.var_99 = -np.percentile(returns, 1)  # 99% VaR

        # Calculate CVaR (expected shortfall)
        # Average of returns below VaR
        var_threshold_95 = np.percentile(returns, 5)
        var_threshold_99 = np.percentile(returns, 1)

        tail_returns_95 = returns[returns <= var_threshold_95]
        tail_returns_99 = returns[returns <= var_threshold_99]

        if len(tail_returns_95) > 0:
            result.cvar_95 = -np.mean(tail_returns_95)
        if len(tail_returns_99) > 0:
            result.cvar_99 = -np.mean(tail_returns_99)

        # Worst case
        result.worst_case_pnl = position_value * np.min(returns)

        # Calculate max position for CVaR limit
        if result.cvar_95 > 0:
            max_loss_allowed = position_value * (self.config.cvar_max_pct / 100)
            result.max_position_for_cvar = max_loss_allowed / result.cvar_95
            result.recommended_position_pct = min(100, (
                result.max_position_for_cvar / position_value * 100
            ))

        return result

    def optimize_position_for_cvar(
        self,
        ticker: str,
        base_position_pct: float,
        capital: float
    ) -> float:
        """
        Optimize position size to stay within CVaR limits.

        Returns adjusted position percentage.
        """
        cvar = self.calculate_cvar(ticker, capital * base_position_pct / 100)

        if cvar.cvar_95 == 0:
            return base_position_pct

        # If CVaR exceeds limit, reduce position
        max_cvar_pct = self.config.cvar_max_pct
        current_cvar_pct = cvar.cvar_95 * 100

        if current_cvar_pct > max_cvar_pct:
            reduction_factor = max_cvar_pct / current_cvar_pct
            adjusted_pct = base_position_pct * reduction_factor

            logger.info(
                f"CVaR limit: {ticker} position reduced "
                f"{base_position_pct:.1f}% → {adjusted_pct:.1f}% "
                f"(CVaR {current_cvar_pct:.1f}% > limit {max_cvar_pct:.1f}%)"
            )

            return adjusted_pct

        return base_position_pct

    # ========================================
    # POSITION STACKING & SECTOR LIMITS
    # ========================================

    def add_position(
        self,
        ticker: str,
        size_pct: float,
        entry_price: float
    ):
        """Add position to tracking."""
        self.active_positions[ticker] = {
            'size_pct': size_pct,
            'entry_price': entry_price,
            'opened_at': datetime.now()
        }

    def close_position(self, ticker: str):
        """Remove position from tracking."""
        if ticker in self.active_positions:
            del self.active_positions[ticker]

    def get_sector(self, ticker: str) -> str:
        """Get sector for a ticker."""
        for sector, tickers in self.config.position_limits.sectors.items():
            if ticker in tickers:
                return sector
        return 'other'

    def check_position_limits(
        self,
        ticker: str,
        proposed_size_pct: float
    ) -> StackingCheck:
        """
        Check if adding position would violate limits.

        Args:
            ticker: Symbol to add
            proposed_size_pct: Proposed position size as % of capital

        Returns:
            StackingCheck with approval/rejection
        """
        check = StackingCheck()
        limits = self.config.position_limits

        # Current position count
        check.current_positions = len(self.active_positions)

        # Check max positions
        if ticker not in self.active_positions:
            if check.current_positions >= limits.max_positions:
                check.can_add_position = False
                check.rejection_reason = f"Max positions ({limits.max_positions}) reached"
                return check

        # Calculate sector exposure
        sector = self.get_sector(ticker)
        sector_exposure = proposed_size_pct

        for pos_ticker, pos_data in self.active_positions.items():
            if pos_ticker == ticker:
                continue
            if self.get_sector(pos_ticker) == sector:
                sector_exposure += pos_data['size_pct']

        check.sector_exposure[sector] = sector_exposure

        # Check sector limit
        if sector_exposure > limits.max_per_sector_pct:
            check.can_add_position = False
            check.rejection_reason = (
                f"Sector '{sector}' exposure {sector_exposure:.1f}% > "
                f"limit {limits.max_per_sector_pct:.1f}%"
            )
            return check

        # Check single ticker limit
        total_ticker_pct = proposed_size_pct
        if ticker in self.active_positions:
            total_ticker_pct += self.active_positions[ticker]['size_pct']

        if total_ticker_pct > limits.max_per_ticker_pct:
            check.can_add_position = False
            check.rejection_reason = (
                f"Ticker {ticker} exposure {total_ticker_pct:.1f}% > "
                f"limit {limits.max_per_ticker_pct:.1f}%"
            )
            return check

        # Check correlation exposure
        correlated_exposure = proposed_size_pct
        for pos_ticker, pos_data in self.active_positions.items():
            if pos_ticker == ticker:
                continue
            correlation = self.correlation_matrix.get(ticker, {}).get(pos_ticker, 0)
            if abs(correlation) > limits.correlation_threshold:
                correlated_exposure += pos_data['size_pct']

        check.correlation_exposure = correlated_exposure

        if correlated_exposure > limits.max_correlated_pct:
            # Don't reject, but recommend smaller size
            recommended = (limits.max_correlated_pct / correlated_exposure) * proposed_size_pct
            check.recommended_size_mult = recommended / proposed_size_pct
            logger.warning(
                f"High correlation exposure for {ticker}: {correlated_exposure:.1f}% "
                f"→ reducing size by {(1-check.recommended_size_mult)*100:.0f}%"
            )

        return check

    def update_correlation_matrix(
        self,
        returns_dict: Dict[str, List[float]]
    ):
        """Update correlation matrix from returns."""
        tickers = list(returns_dict.keys())

        for i, ticker_a in enumerate(tickers):
            if ticker_a not in self.correlation_matrix:
                self.correlation_matrix[ticker_a] = {}

            for j, ticker_b in enumerate(tickers):
                if i >= j:
                    continue

                returns_a = np.array(returns_dict[ticker_a])
                returns_b = np.array(returns_dict[ticker_b])

                min_len = min(len(returns_a), len(returns_b))
                if min_len < 20:
                    continue

                corr = np.corrcoef(returns_a[-min_len:], returns_b[-min_len:])[0, 1]

                self.correlation_matrix[ticker_a][ticker_b] = corr
                if ticker_b not in self.correlation_matrix:
                    self.correlation_matrix[ticker_b] = {}
                self.correlation_matrix[ticker_b][ticker_a] = corr

    # ========================================
    # STRATEGY DECAY
    # ========================================

    def record_trade_result(
        self,
        strategy: str,
        pnl: float,
        is_win: bool
    ):
        """Record trade result for decay tracking."""
        if strategy not in self.performance_history:
            self.performance_history[strategy] = deque(maxlen=self.max_history)

        self.performance_history[strategy].append({
            'timestamp': datetime.now(),
            'pnl': pnl,
            'is_win': is_win
        })

    def check_strategy_decay(
        self,
        strategy: str
    ) -> Tuple[bool, float]:
        """
        Check if strategy is decaying and needs size reduction.

        Returns: (should_reduce, recommended_multiplier)
        """
        if strategy not in self.performance_history:
            return False, 1.0

        history = list(self.performance_history[strategy])
        if len(history) < 30:
            return False, 1.0

        # Recent trades (last N days)
        window_days = self.config.decay_window_days
        now = datetime.now()

        recent = [
            t for t in history
            if (now - t['timestamp']).days <= window_days
        ]

        if len(recent) < 10:
            return False, 1.0

        # Calculate Sharpe
        pnls = [t['pnl'] for t in recent]
        mean_pnl = np.mean(pnls)
        std_pnl = np.std(pnls)

        if std_pnl == 0:
            sharpe = 0
        else:
            sharpe = mean_pnl / std_pnl * np.sqrt(252)

        # Check threshold
        if sharpe < self.config.decay_sharpe_threshold:
            recommended_mult = self.config.decay_reduction_factor

            logger.warning(
                f"📉 Strategy decay: {strategy} Sharpe={sharpe:.2f} "
                f"< threshold={self.config.decay_sharpe_threshold} "
                f"→ reduce size to {recommended_mult:.0%}"
            )

            return True, recommended_mult

        return False, 1.0

    # ========================================
    # COMBINED POSITION SIZING
    # ========================================

    def calculate_position_size(
        self,
        ticker: str,
        entry_price: float,
        stop_loss: float,
        confidence: float,
        capital: float,
        base_size_pct: float = 2.0,
        strategy: str = 'default'
    ) -> Dict[str, Any]:
        """
        Calculate position size with all risk adjustments.

        Applies:
        1. Base size from Kelly/ensemble
        2. CVaR adjustment
        3. Slippage deduction from R:R
        4. Position stacking limits
        5. Strategy decay adjustment

        Returns:
            Dict with final size and all adjustments
        """
        result = {
            'ticker': ticker,
            'base_size_pct': base_size_pct,
            'adjustments': [],
            'final_size_pct': base_size_pct,
        }

        # 1. CVaR adjustment
        cvar_adjusted = self.optimize_position_for_cvar(ticker, base_size_pct, capital)
        if cvar_adjusted != base_size_pct:
            result['adjustments'].append(f"CVaR: {base_size_pct:.1f}% → {cvar_adjusted:.1f}%")
        current_size = cvar_adjusted

        # 2. Slippage adjustment to R:R
        slippage = self.estimate_slippage(ticker, entry_price, 1)
        slippage_cost = slippage.expected_dollars * 2  # Entry + exit

        # Adjust R:R for slippage
        risk_per_unit = abs(entry_price - stop_loss)
        if risk_per_unit > 0:
            slippage_pct_of_risk = slippage_cost / (risk_per_unit * 100) * 100
            if slippage_pct_of_risk > 10:
                # Significant slippage impact
                slippage_adjustment = max(0.7, 1 - slippage_pct_of_risk / 100)
                new_size = current_size * slippage_adjustment
                result['adjustments'].append(
                    f"Slippage ({slippage.expected_ticks:.1f} ticks): "
                    f"{current_size:.1f}% → {new_size:.1f}%"
                )
                current_size = new_size

        # 3. Position stacking check
        stacking = self.check_position_limits(ticker, current_size)
        if not stacking.can_add_position:
            result['adjustments'].append(f"BLOCKED: {stacking.rejection_reason}")
            result['final_size_pct'] = 0
            return result

        if stacking.recommended_size_mult < 1.0:
            new_size = current_size * stacking.recommended_size_mult
            result['adjustments'].append(
                f"Correlation limit: {current_size:.1f}% → {new_size:.1f}%"
            )
            current_size = new_size

        # 4. Strategy decay
        should_reduce, decay_mult = self.check_strategy_decay(strategy)
        if should_reduce:
            new_size = current_size * decay_mult
            result['adjustments'].append(
                f"Strategy decay: {current_size:.1f}% → {new_size:.1f}%"
            )
            current_size = new_size

        result['final_size_pct'] = max(0, current_size)
        result['slippage_estimate'] = slippage
        result['cvar_result'] = self.calculate_cvar(ticker, capital * current_size / 100)

        return result

    # ========================================
    # STATUS
    # ========================================

    def get_status(self) -> Dict[str, Any]:
        """Get risk manager status."""
        sector_exposure = {}
        for sector in self.config.position_limits.sectors:
            sector_exposure[sector] = sum(
                pos['size_pct'] for ticker, pos in self.active_positions.items()
                if self.get_sector(ticker) == sector
            )

        return {
            'active_positions': len(self.active_positions),
            'total_exposure_pct': sum(p['size_pct'] for p in self.active_positions.values()),
            'sector_exposure': sector_exposure,
            'position_details': {
                ticker: {
                    'size_pct': pos['size_pct'],
                    'sector': self.get_sector(ticker)
                }
                for ticker, pos in self.active_positions.items()
            },
            'limits': {
                'max_positions': self.config.position_limits.max_positions,
                'max_per_ticker': self.config.position_limits.max_per_ticker_pct,
                'max_per_sector': self.config.position_limits.max_per_sector_pct,
            },
            'returns_history_tickers': list(self.returns_history.keys()),
        }


# Global instance
_advanced_risk_manager: Optional[AdvancedRiskManager] = None


def get_advanced_risk_manager() -> AdvancedRiskManager:
    """Get or create global advanced risk manager."""
    global _advanced_risk_manager
    if _advanced_risk_manager is None:
        _advanced_risk_manager = AdvancedRiskManager()
    return _advanced_risk_manager
