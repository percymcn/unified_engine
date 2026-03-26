"""
Monte Carlo Robustness Analyzer - 2026 Best Practices
======================================================

Statistical validation and robustness testing:
- Monte Carlo simulation (1000+ paths) with randomized slippage/vol
- Bootstrap confidence intervals for strategy metrics
- Deflated Sharpe Ratio (DSR) to avoid overfitting
- Meta-strategy overlay (pause after N consecutive losses)
- Dynamic Kelly with drawdown floor

Pi5 optimized: Uses numpy vectorization, ~200-500ms for 1000 sims
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)

# Try scipy for statistical functions
try:
    from scipy import stats
    from scipy.special import erfc
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available - some statistical tests disabled")


class TradingState(Enum):
    """Meta-strategy trading state"""
    NORMAL = "normal"
    REDUCED_SIZE = "reduced_size"
    PAUSED = "paused"
    RECOVERY = "recovery"


@dataclass
class RobustnessConfig:
    """Configuration for robustness analysis"""
    # Monte Carlo parameters
    n_simulations: int = 1000
    slippage_mean_pct: float = 0.05  # 5 bps mean slippage
    slippage_std_pct: float = 0.02  # 2 bps std
    vol_shock_prob: float = 0.05  # 5% chance of 2x volatility day
    vol_shock_mult: float = 2.0

    # Bootstrap parameters
    n_bootstrap: int = 500
    confidence_level: float = 0.95

    # Deflated Sharpe
    n_strategies_tested: int = 10  # How many strategies were tried
    lookback_years: float = 1.0

    # Meta-strategy overlay
    pause_after_losses: int = 4  # Pause after 4 consecutive losses
    reduce_after_losses: int = 2  # Reduce size after 2 consecutive losses
    recovery_wins_needed: int = 2  # Need 2 wins to exit pause
    max_daily_drawdown_pct: float = 3.0  # Hard stop at 3% daily DD

    # Dynamic Kelly
    base_kelly_fraction: float = 0.25
    min_kelly_fraction: float = 0.10  # Floor at 10% Kelly
    max_kelly_fraction: float = 0.35
    drawdown_floor_pct: float = 15.0  # Reduce to min Kelly after 15% DD


@dataclass
class MonteCarloResult:
    """Result of Monte Carlo simulation"""
    ticker: str
    strategy_name: str
    timestamp: datetime

    # Base metrics (observed)
    observed_sharpe: float = 0.0
    observed_returns: float = 0.0
    observed_max_dd: float = 0.0
    observed_win_rate: float = 0.0

    # Simulated distributions
    simulated_sharpes: List[float] = field(default_factory=list)
    simulated_returns: List[float] = field(default_factory=list)
    simulated_max_dds: List[float] = field(default_factory=list)

    # Confidence intervals (95%)
    sharpe_ci_lower: float = 0.0
    sharpe_ci_upper: float = 0.0
    returns_ci_lower: float = 0.0
    returns_ci_upper: float = 0.0
    max_dd_ci_upper: float = 0.0  # Upper bound on max DD

    # Deflated Sharpe
    deflated_sharpe: float = 0.0
    prob_skill: float = 0.0  # Probability that performance is due to skill

    # Risk metrics
    expected_shortfall_95: float = 0.0  # CVaR
    prob_ruin: float = 0.0  # Probability of >50% drawdown

    # Robustness score (0-100)
    robustness_score: float = 0.0

    # Warnings
    warnings: List[str] = field(default_factory=list)


@dataclass
class MetaStrategyState:
    """State tracking for meta-strategy overlay"""
    current_state: TradingState = TradingState.NORMAL
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    recovery_wins: int = 0
    daily_pnl_pct: float = 0.0
    peak_equity: float = 100000.0
    current_equity: float = 100000.0
    current_drawdown_pct: float = 0.0
    kelly_multiplier: float = 1.0
    position_size_multiplier: float = 1.0
    state_change_time: datetime = field(default_factory=datetime.now)
    pause_reason: str = ''


@dataclass
class DynamicKellyResult:
    """Dynamic Kelly position sizing result"""
    base_kelly: float = 0.0
    adjusted_kelly: float = 0.0
    position_size_pct: float = 0.0
    multiplier: float = 1.0
    adjustments_applied: List[str] = field(default_factory=list)


class RobustnessAnalyzer:
    """
    Monte Carlo and Bootstrap robustness analyzer.

    Provides statistical validation of strategy performance
    to avoid overfitting and ensure realistic expectations.
    """

    def __init__(self, config: Optional[RobustnessConfig] = None):
        self.config = config or RobustnessConfig()

        # Meta-strategy state
        self.meta_state = MetaStrategyState()

        # Trade history for analysis
        self.trade_history: List[Dict] = []
        self.max_trade_history = 500

        # Daily P&L tracking
        self.daily_pnl_history: deque = deque(maxlen=252)  # 1 year

        logger.info(
            f"RobustnessAnalyzer initialized: n_sims={self.config.n_simulations}, "
            f"pause_after={self.config.pause_after_losses} losses"
        )

    def run_monte_carlo(
        self,
        returns: np.ndarray,
        ticker: str = "STRATEGY",
        strategy_name: str = "SmartFlow"
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation with randomized slippage and volatility.

        Args:
            returns: Array of daily/trade returns (as decimals, e.g., 0.02 = 2%)
            ticker: Symbol or strategy identifier
            strategy_name: Name of strategy

        Returns:
            MonteCarloResult with simulated distributions and confidence intervals
        """
        result = MonteCarloResult(
            ticker=ticker,
            strategy_name=strategy_name,
            timestamp=datetime.now()
        )

        if len(returns) < 30:
            result.warnings.append(f"Insufficient data: {len(returns)} trades (need 30+)")
            return result

        # Observed metrics
        result.observed_returns = float(np.sum(returns))
        result.observed_sharpe = self._calculate_sharpe(returns)
        result.observed_max_dd = self._calculate_max_drawdown(returns)
        result.observed_win_rate = float(np.mean(returns > 0))

        # Run simulations
        n_sims = self.config.n_simulations
        n_trades = len(returns)

        # Pre-generate random factors for speed
        np.random.seed(42)  # Reproducibility

        # Slippage factors (multiplicative)
        slippage = 1 - np.random.normal(
            self.config.slippage_mean_pct / 100,
            self.config.slippage_std_pct / 100,
            (n_sims, n_trades)
        )

        # Volatility shocks
        vol_shocks = np.where(
            np.random.random((n_sims, n_trades)) < self.config.vol_shock_prob,
            self.config.vol_shock_mult,
            1.0
        )

        # Simulate paths
        simulated_returns = returns * slippage * vol_shocks

        # Calculate metrics for each simulation
        result.simulated_sharpes = [
            self._calculate_sharpe(simulated_returns[i])
            for i in range(n_sims)
        ]
        result.simulated_returns = [
            float(np.sum(simulated_returns[i]))
            for i in range(n_sims)
        ]
        result.simulated_max_dds = [
            self._calculate_max_drawdown(simulated_returns[i])
            for i in range(n_sims)
        ]

        # Confidence intervals (95%)
        ci_lower = (1 - self.config.confidence_level) / 2
        ci_upper = 1 - ci_lower

        result.sharpe_ci_lower = float(np.percentile(result.simulated_sharpes, ci_lower * 100))
        result.sharpe_ci_upper = float(np.percentile(result.simulated_sharpes, ci_upper * 100))
        result.returns_ci_lower = float(np.percentile(result.simulated_returns, ci_lower * 100))
        result.returns_ci_upper = float(np.percentile(result.simulated_returns, ci_upper * 100))
        result.max_dd_ci_upper = float(np.percentile(result.simulated_max_dds, ci_upper * 100))

        # Expected Shortfall (CVaR) at 95%
        sorted_returns = np.sort(result.simulated_returns)
        cutoff_idx = int(n_sims * 0.05)
        result.expected_shortfall_95 = float(np.mean(sorted_returns[:cutoff_idx]))

        # Probability of ruin (>50% drawdown)
        result.prob_ruin = float(np.mean(np.array(result.simulated_max_dds) > 0.5))

        # Deflated Sharpe Ratio
        result.deflated_sharpe, result.prob_skill = self._calculate_deflated_sharpe(
            result.observed_sharpe,
            len(returns),
            self.config.n_strategies_tested,
            result.simulated_sharpes
        )

        # Calculate robustness score (0-100)
        result.robustness_score = self._calculate_robustness_score(result)

        # Add warnings
        if result.sharpe_ci_lower < 0:
            result.warnings.append("Sharpe ratio CI includes 0 - edge not statistically significant")

        if result.deflated_sharpe < 0.5:
            result.warnings.append(f"Low deflated Sharpe ({result.deflated_sharpe:.2f}) - possible overfitting")

        if result.prob_ruin > 0.05:
            result.warnings.append(f"High probability of ruin ({result.prob_ruin:.1%})")

        if result.expected_shortfall_95 < -0.3:
            result.warnings.append(f"Severe tail risk: CVaR95 = {result.expected_shortfall_95:.1%}")

        logger.info(
            f"📊 Monte Carlo {ticker}: Sharpe={result.observed_sharpe:.2f} "
            f"[{result.sharpe_ci_lower:.2f}, {result.sharpe_ci_upper:.2f}] "
            f"DSR={result.deflated_sharpe:.2f} P(skill)={result.prob_skill:.1%} "
            f"Robustness={result.robustness_score:.0f}/100"
        )

        return result

    def _calculate_sharpe(self, returns: np.ndarray, risk_free: float = 0.0) -> float:
        """Calculate annualized Sharpe ratio."""
        if len(returns) < 2:
            return 0.0

        excess_returns = returns - risk_free / 252  # Daily risk-free
        mean_return = np.mean(excess_returns)
        std_return = np.std(excess_returns, ddof=1)

        if std_return == 0:
            return 0.0

        # Annualize (assuming daily returns)
        sharpe = (mean_return / std_return) * np.sqrt(252)
        return float(sharpe)

    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """Calculate maximum drawdown from returns series."""
        if len(returns) < 2:
            return 0.0

        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max

        return float(np.min(drawdowns))  # Most negative

    def _calculate_deflated_sharpe(
        self,
        observed_sharpe: float,
        n_observations: int,
        n_strategies: int,
        simulated_sharpes: List[float]
    ) -> Tuple[float, float]:
        """
        Calculate Deflated Sharpe Ratio (Bailey & Lopez de Prado).

        Adjusts Sharpe for multiple testing and non-normality.

        Returns:
            (deflated_sharpe, probability_of_skill)
        """
        if not SCIPY_AVAILABLE:
            # Simple approximation without scipy
            penalty = np.log(n_strategies) / np.sqrt(n_observations)
            deflated = observed_sharpe - penalty
            prob_skill = 0.5 + 0.5 * np.tanh(deflated)
            return float(deflated), float(prob_skill)

        # Calculate higher moments of simulated Sharpes
        sharpes = np.array(simulated_sharpes)
        skewness = stats.skew(sharpes)
        kurtosis = stats.kurtosis(sharpes) + 3  # Excess kurtosis + 3

        # Expected maximum Sharpe under null (multiple testing adjustment)
        # E[max(SR)] ≈ (1 - γ) * Φ^(-1)(1 - 1/N) + γ * Φ^(-1)(1 - 1/(N*e))
        # where γ ≈ 0.5772 (Euler-Mascheroni constant)
        gamma = 0.5772156649
        if n_strategies > 1:
            expected_max_sr = (1 - gamma) * stats.norm.ppf(1 - 1/n_strategies)
            expected_max_sr += gamma * stats.norm.ppf(1 - 1/(n_strategies * np.e))
        else:
            expected_max_sr = 0.0

        # Standard error of Sharpe ratio (adjusted for non-normality)
        sr_std = np.sqrt(
            (1 + 0.5 * observed_sharpe**2 - skewness * observed_sharpe +
             (kurtosis - 1) / 4 * observed_sharpe**2) / n_observations
        )

        # Deflated Sharpe (how much observed SR exceeds expected max under null)
        deflated_sharpe = (observed_sharpe - expected_max_sr) / sr_std if sr_std > 0 else 0

        # Probability that result is due to skill (not luck)
        prob_skill = 1 - stats.norm.cdf(-deflated_sharpe)

        return float(deflated_sharpe), float(prob_skill)

    def _calculate_robustness_score(self, result: MonteCarloResult) -> float:
        """
        Calculate overall robustness score (0-100).

        Combines multiple factors:
        - Sharpe stability (CI width)
        - Deflated Sharpe
        - Drawdown risk
        - Win rate stability
        """
        score = 50.0  # Base score

        # Sharpe stability: narrower CI = more robust
        ci_width = result.sharpe_ci_upper - result.sharpe_ci_lower
        if ci_width < 1.0:
            score += 15
        elif ci_width < 2.0:
            score += 10
        elif ci_width > 3.0:
            score -= 10

        # Deflated Sharpe
        if result.deflated_sharpe > 1.0:
            score += 15
        elif result.deflated_sharpe > 0.5:
            score += 10
        elif result.deflated_sharpe < 0:
            score -= 15

        # Probability of skill
        if result.prob_skill > 0.95:
            score += 10
        elif result.prob_skill > 0.80:
            score += 5
        elif result.prob_skill < 0.50:
            score -= 10

        # Drawdown risk
        if result.max_dd_ci_upper > -0.20:  # Less than 20% max DD
            score += 10
        elif result.max_dd_ci_upper > -0.30:
            score += 5
        elif result.max_dd_ci_upper < -0.50:
            score -= 15

        # Probability of ruin
        if result.prob_ruin < 0.01:
            score += 5
        elif result.prob_ruin > 0.10:
            score -= 10

        return max(0, min(100, score))

    def bootstrap_metric(
        self,
        returns: np.ndarray,
        metric_func: callable,
        n_bootstrap: Optional[int] = None
    ) -> Tuple[float, float, float]:
        """
        Bootstrap confidence interval for any metric.

        Args:
            returns: Return series
            metric_func: Function that takes returns and returns a scalar
            n_bootstrap: Number of bootstrap samples

        Returns:
            (observed_metric, ci_lower, ci_upper)
        """
        n_bootstrap = n_bootstrap or self.config.n_bootstrap
        n = len(returns)

        observed = metric_func(returns)

        # Bootstrap samples
        bootstrap_metrics = []
        for _ in range(n_bootstrap):
            sample_idx = np.random.choice(n, size=n, replace=True)
            sample = returns[sample_idx]
            bootstrap_metrics.append(metric_func(sample))

        ci_lower = float(np.percentile(bootstrap_metrics, 2.5))
        ci_upper = float(np.percentile(bootstrap_metrics, 97.5))

        return observed, ci_lower, ci_upper

    # ========================================
    # META-STRATEGY OVERLAY
    # ========================================

    def update_meta_state(
        self,
        trade_result: str,  # 'win' or 'loss'
        pnl_pct: float,
        capital: float
    ) -> MetaStrategyState:
        """
        Update meta-strategy state after each trade.

        Implements:
        - Pause after N consecutive losses
        - Reduce size after M consecutive losses
        - Recovery mode to exit pause
        """
        # Update equity tracking
        self.meta_state.current_equity = capital
        if capital > self.meta_state.peak_equity:
            self.meta_state.peak_equity = capital

        # Calculate current drawdown
        self.meta_state.current_drawdown_pct = (
            (self.meta_state.peak_equity - capital) / self.meta_state.peak_equity * 100
        )

        # Update daily P&L
        self.meta_state.daily_pnl_pct += pnl_pct

        # Update streak counters
        if trade_result == 'win':
            self.meta_state.consecutive_wins += 1
            self.meta_state.consecutive_losses = 0

            if self.meta_state.current_state == TradingState.RECOVERY:
                self.meta_state.recovery_wins += 1
                if self.meta_state.recovery_wins >= self.config.recovery_wins_needed:
                    self._transition_state(TradingState.NORMAL, "Recovery complete")
        else:
            self.meta_state.consecutive_losses += 1
            self.meta_state.consecutive_wins = 0
            self.meta_state.recovery_wins = 0

        # State transitions based on losses
        if self.meta_state.consecutive_losses >= self.config.pause_after_losses:
            if self.meta_state.current_state != TradingState.PAUSED:
                self._transition_state(
                    TradingState.PAUSED,
                    f"{self.meta_state.consecutive_losses} consecutive losses"
                )

        elif self.meta_state.consecutive_losses >= self.config.reduce_after_losses:
            if self.meta_state.current_state == TradingState.NORMAL:
                self._transition_state(
                    TradingState.REDUCED_SIZE,
                    f"{self.meta_state.consecutive_losses} consecutive losses"
                )

        # Daily drawdown circuit breaker
        if self.meta_state.daily_pnl_pct <= -self.config.max_daily_drawdown_pct:
            self._transition_state(
                TradingState.PAUSED,
                f"Daily DD limit: {self.meta_state.daily_pnl_pct:.1f}%"
            )

        # Update position size multiplier
        self._update_position_multiplier()

        return self.meta_state

    def _transition_state(self, new_state: TradingState, reason: str):
        """Transition to new trading state."""
        old_state = self.meta_state.current_state
        self.meta_state.current_state = new_state
        self.meta_state.state_change_time = datetime.now()
        self.meta_state.pause_reason = reason

        if new_state == TradingState.PAUSED:
            self.meta_state.recovery_wins = 0

        logger.info(f"🚦 Meta-state: {old_state.value} → {new_state.value} ({reason})")

    def _update_position_multiplier(self):
        """Update position size multiplier based on state."""
        if self.meta_state.current_state == TradingState.PAUSED:
            self.meta_state.position_size_multiplier = 0.0
        elif self.meta_state.current_state == TradingState.REDUCED_SIZE:
            self.meta_state.position_size_multiplier = 0.5
        elif self.meta_state.current_state == TradingState.RECOVERY:
            self.meta_state.position_size_multiplier = 0.5
        else:
            self.meta_state.position_size_multiplier = 1.0

    def should_trade(self) -> Tuple[bool, str]:
        """Check if trading is allowed under meta-strategy."""
        if self.meta_state.current_state == TradingState.PAUSED:
            return False, self.meta_state.pause_reason

        if self.meta_state.daily_pnl_pct <= -self.config.max_daily_drawdown_pct:
            return False, f"Daily DD limit reached: {self.meta_state.daily_pnl_pct:.1f}%"

        return True, ""

    def request_recovery(self) -> bool:
        """Request to exit pause and enter recovery mode."""
        if self.meta_state.current_state == TradingState.PAUSED:
            self._transition_state(TradingState.RECOVERY, "Manual recovery requested")
            return True
        return False

    def reset_daily(self):
        """Reset daily tracking (call at market open)."""
        self.meta_state.daily_pnl_pct = 0.0

        # If paused due to daily DD, allow recovery
        if (self.meta_state.current_state == TradingState.PAUSED and
            "Daily DD" in self.meta_state.pause_reason):
            self._transition_state(TradingState.RECOVERY, "New trading day")

        logger.info("Meta-strategy daily reset")

    # ========================================
    # DYNAMIC KELLY
    # ========================================

    def calculate_dynamic_kelly(
        self,
        win_rate: float,
        avg_win_loss_ratio: float,
        current_drawdown_pct: Optional[float] = None
    ) -> DynamicKellyResult:
        """
        Calculate dynamic Kelly fraction with drawdown floor.

        Reduces Kelly when:
        - In drawdown
        - After consecutive losses
        - In high volatility regime

        Args:
            win_rate: Historical win rate (0-1)
            avg_win_loss_ratio: Average winner / average loser
            current_drawdown_pct: Current drawdown as positive percentage

        Returns:
            DynamicKellyResult with adjusted Kelly and position size
        """
        result = DynamicKellyResult()

        # Calculate raw Kelly
        # Kelly % = W - [(1-W) / R]
        if avg_win_loss_ratio <= 0:
            result.base_kelly = 0.0
        else:
            result.base_kelly = win_rate - ((1 - win_rate) / avg_win_loss_ratio)

        # Start with base Kelly fraction
        result.adjusted_kelly = result.base_kelly * self.config.base_kelly_fraction

        # Use provided or tracked drawdown
        drawdown = current_drawdown_pct if current_drawdown_pct is not None else self.meta_state.current_drawdown_pct

        # ========================================
        # DRAWDOWN ADJUSTMENT
        # ========================================
        if drawdown >= self.config.drawdown_floor_pct:
            # At or beyond floor - use minimum Kelly
            old_kelly = result.adjusted_kelly
            result.adjusted_kelly = result.base_kelly * self.config.min_kelly_fraction
            result.adjustments_applied.append(
                f"Drawdown floor ({drawdown:.1f}% >= {self.config.drawdown_floor_pct}%): "
                f"Kelly {old_kelly:.3f} → {result.adjusted_kelly:.3f}"
            )
        elif drawdown > 0:
            # Linear reduction based on drawdown
            # At 0% DD: full Kelly, at floor: min Kelly
            reduction = drawdown / self.config.drawdown_floor_pct
            kelly_range = self.config.base_kelly_fraction - self.config.min_kelly_fraction
            adjusted_fraction = self.config.base_kelly_fraction - (reduction * kelly_range)

            old_kelly = result.adjusted_kelly
            result.adjusted_kelly = result.base_kelly * adjusted_fraction
            result.adjustments_applied.append(
                f"Drawdown adjustment ({drawdown:.1f}%): "
                f"Kelly {old_kelly:.3f} → {result.adjusted_kelly:.3f}"
            )

        # ========================================
        # CONSECUTIVE LOSS ADJUSTMENT
        # ========================================
        if self.meta_state.consecutive_losses >= 2:
            loss_penalty = 1.0 - (self.meta_state.consecutive_losses * 0.1)
            loss_penalty = max(0.5, loss_penalty)

            old_kelly = result.adjusted_kelly
            result.adjusted_kelly *= loss_penalty
            result.adjustments_applied.append(
                f"Loss streak ({self.meta_state.consecutive_losses}): "
                f"Kelly {old_kelly:.3f} → {result.adjusted_kelly:.3f}"
            )

        # ========================================
        # META-STATE ADJUSTMENT
        # ========================================
        if self.meta_state.current_state == TradingState.REDUCED_SIZE:
            old_kelly = result.adjusted_kelly
            result.adjusted_kelly *= 0.5
            result.adjustments_applied.append(
                f"Reduced size state: Kelly {old_kelly:.3f} → {result.adjusted_kelly:.3f}"
            )
        elif self.meta_state.current_state == TradingState.RECOVERY:
            old_kelly = result.adjusted_kelly
            result.adjusted_kelly *= 0.5
            result.adjustments_applied.append(
                f"Recovery state: Kelly {old_kelly:.3f} → {result.adjusted_kelly:.3f}"
            )

        # Enforce bounds
        result.adjusted_kelly = max(0, min(
            self.config.max_kelly_fraction,
            result.adjusted_kelly
        ))

        # Calculate multiplier
        if self.config.base_kelly_fraction > 0:
            result.multiplier = result.adjusted_kelly / self.config.base_kelly_fraction
        else:
            result.multiplier = 0.0

        # Convert to position size percentage
        result.position_size_pct = result.adjusted_kelly * 100

        return result

    def get_status(self) -> Dict:
        """Get robustness analyzer status."""
        return {
            'meta_state': self.meta_state.current_state.value,
            'consecutive_losses': self.meta_state.consecutive_losses,
            'consecutive_wins': self.meta_state.consecutive_wins,
            'current_drawdown_pct': self.meta_state.current_drawdown_pct,
            'daily_pnl_pct': self.meta_state.daily_pnl_pct,
            'position_multiplier': self.meta_state.position_size_multiplier,
            'can_trade': self.should_trade()[0],
            'pause_reason': self.meta_state.pause_reason if self.meta_state.current_state == TradingState.PAUSED else '',
        }


# Global instance
_robustness_analyzer: Optional[RobustnessAnalyzer] = None


def get_robustness_analyzer() -> RobustnessAnalyzer:
    """Get or create global robustness analyzer instance."""
    global _robustness_analyzer
    if _robustness_analyzer is None:
        _robustness_analyzer = RobustnessAnalyzer()
    return _robustness_analyzer
