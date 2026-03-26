"""
Elite Risk Manager Module
=========================

Advanced position sizing and risk management:
- Fractional Kelly Criterion (avoid ruin, maximize growth)
- Portfolio VaR/CVaR using simple mean-variance
- Dynamic sizing based on:
  - ATR-adjusted volatility
  - Correlation penalty (reduce size when correlated assets signal together)
  - Drawdown state (reduce size after losses)
  - Regime awareness

Pi5 lightweight implementation using numpy.
"""

import logging
import numpy as np
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    """Risk management configuration - TIGHTENED FOR GO-LIVE (2026)"""
    # Kelly parameters
    kelly_fraction: float = 0.25  # Use 25% of Kelly (fractional for safety)
    max_position_pct: float = 3.5  # TIGHTENED: Max 3.5% of capital per position (was 5%)
    min_position_pct: float = 0.5  # Min 0.5% per position

    # Portfolio limits - TIGHTENED
    max_portfolio_risk_pct: float = 12.0  # TIGHTENED: Max 12% portfolio at risk (was 15%)
    max_correlated_positions: int = 2  # Max 2 positions in correlated assets
    max_concurrent_positions: int = 3  # NEW: Max 3 concurrent positions (was unlimited)
    max_daily_drawdown_pct: float = 2.5  # TIGHTENED: Stop trading after 2.5% daily DD (was 3%)

    # Correlation penalty
    correlation_threshold: float = 0.7  # Assets above this are "correlated"
    correlation_size_factor: float = 0.5  # Halve size for correlated position

    # VaR parameters
    var_confidence: float = 0.95  # 95% VaR
    var_lookback_days: int = 20

    # Regime-based adjustments - UPDATED with vol_expansion
    regime_size_mults: Dict[str, float] = field(default_factory=lambda: {
        'trending_up': 1.0,        # Full size in uptrend
        'trending_down': 1.0,      # Full size in downtrend
        'trending': 1.0,           # Legacy: full size
        'ranging': 0.8,            # 80% in ranging
        'mean_reverting': 0.8,     # 80% in mean-reverting
        'vol_expansion': 0.65,     # TIGHTENED: 65% in vol expansion (was 0.5)
        'vol_contraction': 0.9,    # 90% in vol contraction (breakout setup)
        'high_vol': 0.5,           # Legacy: half size in high volatility
        'chaotic': 0.4,            # NEW: 40% in chaotic regime
        'low_vol': 1.0,
        'neutral': 1.0
    })


@dataclass
class PositionSizeResult:
    """Position sizing result"""
    ticker: str
    suggested_size_pct: float  # % of capital
    kelly_raw: float  # Raw Kelly suggestion
    kelly_fractional: float  # Fractional Kelly

    # Adjustments applied
    atr_adjusted: float = 0.0
    correlation_adjusted: float = 0.0
    drawdown_adjusted: float = 0.0
    regime_adjusted: float = 0.0

    # Final
    final_size_pct: float = 0.0
    max_loss_pct: float = 0.0  # Expected max loss at stop

    # Risk metrics
    position_var: float = 0.0  # Value at Risk for this position
    portfolio_utilization: float = 0.0  # How much of risk budget used

    # Warnings
    warnings: List[str] = field(default_factory=list)


@dataclass
class PortfolioRisk:
    """Portfolio-level risk metrics"""
    total_positions: int = 0
    total_risk_pct: float = 0.0
    portfolio_var: float = 0.0
    portfolio_cvar: float = 0.0
    correlation_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    daily_pnl: float = 0.0
    drawdown_pct: float = 0.0
    is_trading_halted: bool = False
    halt_reason: str = ''


class RiskManager:
    """
    Elite risk manager for position sizing and portfolio protection.

    Uses fractional Kelly criterion with multiple adjustments
    to maximize long-term growth while avoiding ruin.
    """

    def __init__(self, config: Optional[RiskConfig] = None):
        self.config = config or RiskConfig()

        # Track active positions
        self.active_positions: Dict[str, Dict] = {}

        # Historical returns for correlation
        self.returns_history: Dict[str, deque] = {}
        self.max_history = 100

        # Daily P&L tracking
        self.daily_pnl: float = 0.0
        self.daily_start: datetime = datetime.now().replace(hour=0, minute=0, second=0)

        # Assumed win rate and payoff for Kelly (updated from actual results)
        self.default_win_rate = 0.55  # 55% win rate assumption
        self.default_avg_win = 2.0  # Average winner = 2x average loser

        # Correlation groups (assets that tend to move together)
        self.correlation_groups = {
            'equity_indices': ['MES', 'NQ', 'RTY', 'MYM', 'SPY', 'QQQ', 'IWM', 'DIA'],
            'metals': ['GC', 'MGC', 'GLD'],
            'crypto': ['BTCUSD', 'ETHUSD'],
        }

        logger.info(f"RiskManager initialized: Kelly={self.config.kelly_fraction}, "
                   f"max_pos={self.config.max_position_pct}%")

    def calculate_kelly(
        self,
        win_rate: float,
        avg_win_loss_ratio: float
    ) -> float:
        """
        Calculate Kelly Criterion.

        Kelly % = W - [(1-W) / R]
        Where:
            W = Win rate
            R = Win/Loss ratio (average winner / average loser)

        Returns:
            Kelly percentage (can be negative if edge is negative)
        """
        if avg_win_loss_ratio <= 0:
            return 0.0

        kelly = win_rate - ((1 - win_rate) / avg_win_loss_ratio)
        return kelly

    def calculate_position_size(
        self,
        ticker: str,
        entry_price: float,
        stop_loss: float,
        confidence: float,
        regime: str = 'neutral',
        capital: float = 100000.0,
        win_rate: Optional[float] = None,
        avg_rr: Optional[float] = None
    ) -> PositionSizeResult:
        """
        Calculate optimal position size using fractional Kelly.

        Args:
            ticker: Symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            confidence: Signal confidence (0-100)
            regime: Current market regime
            capital: Account capital
            win_rate: Historical win rate (optional)
            avg_rr: Average risk/reward (optional)

        Returns:
            PositionSizeResult with suggested sizing
        """
        result = PositionSizeResult(ticker=ticker, suggested_size_pct=0.0, kelly_raw=0.0, kelly_fractional=0.0)

        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_loss)
        risk_pct = (risk_per_unit / entry_price) * 100 if entry_price > 0 else 5.0

        # Use provided or default win rate / RR
        wr = win_rate if win_rate is not None else self.default_win_rate
        rr = avg_rr if avg_rr is not None else self.default_avg_win

        # Adjust win rate based on confidence
        # Higher confidence = higher expected win rate
        confidence_adj = (confidence / 100.0 - 0.5) * 0.2  # ±10% adjustment
        adjusted_wr = max(0.35, min(0.75, wr + confidence_adj))

        # ========================================
        # KELLY CRITERION
        # ========================================
        result.kelly_raw = self.calculate_kelly(adjusted_wr, rr)
        result.kelly_fractional = result.kelly_raw * self.config.kelly_fraction

        # Kelly gives us the optimal fraction of bankroll to bet
        # Convert to position size percentage
        if result.kelly_fractional > 0:
            base_size = result.kelly_fractional * 100  # Convert to %
        else:
            result.warnings.append("Negative Kelly - no edge detected")
            base_size = 0.0

        # ========================================
        # ATR ADJUSTMENT
        # ========================================
        # Higher risk_pct means wider stops = smaller position
        # Normalize: 1% risk = 1x, 2% risk = 0.5x, etc.
        atr_mult = 1.0 / (risk_pct / 1.0) if risk_pct > 0 else 1.0
        atr_mult = max(0.25, min(2.0, atr_mult))
        result.atr_adjusted = base_size * atr_mult

        # ========================================
        # CORRELATION ADJUSTMENT
        # ========================================
        corr_mult = 1.0
        correlated_count = self._count_correlated_positions(ticker)

        if correlated_count >= self.config.max_correlated_positions:
            result.warnings.append(f"Max correlated positions ({correlated_count}) reached")
            corr_mult = self.config.correlation_size_factor
        elif correlated_count > 0:
            corr_mult = 1.0 - (correlated_count * 0.15)  # 15% reduction per correlated position

        result.correlation_adjusted = result.atr_adjusted * corr_mult

        # ========================================
        # DRAWDOWN ADJUSTMENT
        # ========================================
        dd_mult = 1.0
        current_dd = self._get_current_drawdown()

        if current_dd >= self.config.max_daily_drawdown_pct:
            result.warnings.append(f"Daily drawdown limit reached: {current_dd:.1f}%")
            dd_mult = 0.0  # Stop trading
        elif current_dd > 1.0:
            # Reduce size proportionally to drawdown
            dd_mult = max(0.25, 1.0 - (current_dd / self.config.max_daily_drawdown_pct))

        result.drawdown_adjusted = result.correlation_adjusted * dd_mult

        # ========================================
        # REGIME ADJUSTMENT
        # ========================================
        regime_mult = self.config.regime_size_mults.get(regime, 1.0)
        result.regime_adjusted = result.drawdown_adjusted * regime_mult

        # ========================================
        # FINAL SIZE
        # ========================================
        final_size = result.regime_adjusted

        # Apply limits
        final_size = max(self.config.min_position_pct, min(self.config.max_position_pct, final_size))

        # Check portfolio risk budget
        portfolio_risk = self._get_portfolio_risk()
        remaining_budget = self.config.max_portfolio_risk_pct - portfolio_risk.total_risk_pct

        if final_size * (risk_pct / 100) > remaining_budget:
            old_size = final_size
            max_allowed = (remaining_budget / (risk_pct / 100)) if risk_pct > 0 else 0
            final_size = max(0, min(final_size, max_allowed))
            if final_size < old_size:
                result.warnings.append(f"Size reduced for portfolio risk budget: {remaining_budget:.1f}% remaining")

        result.final_size_pct = final_size
        result.suggested_size_pct = final_size

        # Calculate expected max loss
        result.max_loss_pct = final_size * (risk_pct / 100)

        # Position VaR (simplified)
        result.position_var = self._calculate_position_var(ticker, final_size, capital)

        # Portfolio utilization
        if self.config.max_portfolio_risk_pct > 0:
            result.portfolio_utilization = (portfolio_risk.total_risk_pct + result.max_loss_pct) / self.config.max_portfolio_risk_pct * 100

        logger.info(
            f"📊 Size {ticker}: Kelly={result.kelly_fractional:.2f} → "
            f"ATR={result.atr_adjusted:.2f}% → Corr={result.correlation_adjusted:.2f}% → "
            f"DD={result.drawdown_adjusted:.2f}% → Regime={result.regime_adjusted:.2f}% → "
            f"FINAL={result.final_size_pct:.2f}% (max_loss={result.max_loss_pct:.2f}%)"
        )

        return result

    def _count_correlated_positions(self, ticker: str) -> int:
        """Count how many active positions are correlated with this ticker."""
        count = 0
        ticker_group = None

        # Find which group this ticker belongs to
        for group_name, tickers in self.correlation_groups.items():
            if ticker in tickers:
                ticker_group = group_name
                break

        if ticker_group is None:
            return 0

        # Count active positions in same group
        group_tickers = self.correlation_groups[ticker_group]
        for pos_ticker in self.active_positions.keys():
            if pos_ticker != ticker and pos_ticker in group_tickers:
                count += 1

        return count

    def _get_current_drawdown(self) -> float:
        """Get current daily drawdown percentage."""
        # Reset at start of new day
        now = datetime.now()
        if now.date() > self.daily_start.date():
            self.daily_pnl = 0.0
            self.daily_start = now.replace(hour=0, minute=0, second=0)

        # Return as positive percentage (drawdown)
        return abs(min(0, self.daily_pnl))

    def _get_portfolio_risk(self) -> PortfolioRisk:
        """Calculate current portfolio risk metrics."""
        risk = PortfolioRisk()

        risk.total_positions = len(self.active_positions)

        # Sum up risk from all positions
        for ticker, pos in self.active_positions.items():
            risk.total_risk_pct += pos.get('risk_pct', 0)

        risk.daily_pnl = self.daily_pnl
        risk.drawdown_pct = self._get_current_drawdown()

        # Check if trading should be halted
        if risk.drawdown_pct >= self.config.max_daily_drawdown_pct:
            risk.is_trading_halted = True
            risk.halt_reason = f"Daily drawdown limit reached: {risk.drawdown_pct:.1f}%"

        return risk

    def _calculate_position_var(
        self,
        ticker: str,
        size_pct: float,
        capital: float
    ) -> float:
        """
        Calculate Value at Risk for a position.

        Uses simplified parametric VaR.
        """
        # Get historical volatility if available
        returns = self.returns_history.get(ticker, deque())

        if len(returns) < 10:
            # Use default volatility assumption (2% daily)
            daily_vol = 0.02
        else:
            daily_vol = np.std(list(returns))

        # Position value
        position_value = capital * (size_pct / 100)

        # VaR at confidence level
        z_score = {0.95: 1.645, 0.99: 2.326}.get(self.config.var_confidence, 1.645)

        var = position_value * daily_vol * z_score

        return var

    def add_return(self, ticker: str, pct_return: float):
        """Record a return for correlation calculations."""
        if ticker not in self.returns_history:
            self.returns_history[ticker] = deque(maxlen=self.max_history)

        self.returns_history[ticker].append(pct_return)

    def update_position(
        self,
        ticker: str,
        action: str,
        size_pct: float = 0.0,
        risk_pct: float = 0.0
    ):
        """Update active position tracking."""
        if action in ['buy', 'sell']:
            self.active_positions[ticker] = {
                'action': action,
                'size_pct': size_pct,
                'risk_pct': risk_pct,
                'opened_at': datetime.now()
            }
        elif action == 'close':
            if ticker in self.active_positions:
                del self.active_positions[ticker]

    def record_pnl(self, pnl_pct: float):
        """Record P&L for daily tracking."""
        self.daily_pnl += pnl_pct

    def reset_daily(self):
        """Reset daily tracking (call at market open)."""
        self.daily_pnl = 0.0
        self.daily_start = datetime.now().replace(hour=0, minute=0, second=0)
        logger.info("Daily risk tracking reset")

    def get_status(self) -> Dict:
        """Get current risk manager status."""
        portfolio_risk = self._get_portfolio_risk()

        return {
            'active_positions': len(self.active_positions),
            'total_risk_pct': portfolio_risk.total_risk_pct,
            'daily_pnl': self.daily_pnl,
            'daily_drawdown': portfolio_risk.drawdown_pct,
            'is_halted': portfolio_risk.is_trading_halted,
            'halt_reason': portfolio_risk.halt_reason,
            'remaining_budget': max(0, self.config.max_portfolio_risk_pct - portfolio_risk.total_risk_pct),
            'positions': list(self.active_positions.keys())
        }


# Global instance
_risk_manager: Optional[RiskManager] = None


def get_risk_manager() -> RiskManager:
    """Get or create global risk manager instance."""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager


# =============================================================================
# SmartFlow Guardrail Risk Manager
# =============================================================================

@dataclass
class GuardrailConfig:
    """Guardrail limits for autonomous SmartFlow trading."""
    max_daily_loss: float = 0.0  # Default 0.0 = disabled
    max_open_positions: int = 3
    max_position_size: float = 0.0  # Default 0.0 = disabled
    max_drawdown_pct: float = 5.0
    starting_equity: float = 0.0


class GuardrailRiskManager:
    """Lightweight guardrail-based risk manager for SmartFlow."""

    def __init__(self, config: Optional[GuardrailConfig] = None):
        self.config = config or GuardrailConfig()
        self.open_positions: Dict[str, Dict] = {}
        self.daily_pnl: float = 0.0
        self.total_realized_pnl: float = 0.0
        self.peak_equity: float = self.config.starting_equity
        self.halted: bool = False
        self.halt_reason: str = ""
        self._current_day = datetime.utcnow().date()

    def _roll_day_if_needed(self) -> None:
        today = datetime.utcnow().date()
        if today != self._current_day:
            self._current_day = today
            self.daily_pnl = 0.0

    def _check_drawdown(self) -> Optional[str]:
        if self.config.max_drawdown_pct <= 0 or self.peak_equity <= 0:
            return None
        current_equity = self.config.starting_equity + self.total_realized_pnl
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        drawdown_pct = ((self.peak_equity - current_equity) / self.peak_equity) * 100
        if drawdown_pct >= self.config.max_drawdown_pct:
            return f"Max drawdown hit ({drawdown_pct:.2f}% >= {self.config.max_drawdown_pct:.2f}%)"
        return None

    def halt_trading(self, reason: str) -> None:
        self.halted = True
        self.halt_reason = reason
        logger.warning(f"🛑 SmartFlow trading halted: {reason}")

    def check_trade_allowed(self, symbol: str, quantity: float) -> tuple[bool, str]:
        """Check whether a new trade is allowed."""
        self._roll_day_if_needed()

        if self.halted:
            return False, self.halt_reason or "Trading halted"

        if self.config.max_open_positions > 0 and len(self.open_positions) >= self.config.max_open_positions:
            reason = "Max open positions reached"
            self.halt_trading(reason)
            return False, reason

        if self.config.max_position_size > 0 and quantity > self.config.max_position_size:
            reason = "Max position size exceeded"
            self.halt_trading(reason)
            return False, reason

        if self.config.max_daily_loss > 0 and self.daily_pnl <= -self.config.max_daily_loss:
            reason = "Max daily loss reached"
            self.halt_trading(reason)
            return False, reason

        drawdown_reason = self._check_drawdown()
        if drawdown_reason:
            self.halt_trading(drawdown_reason)
            return False, drawdown_reason

        return True, ""

    def record_trade_open(self, trade_id: Optional[int], symbol: str, quantity: float) -> None:
        """Record an open position for guardrail tracking."""
        self.open_positions[symbol] = {
            "trade_id": trade_id,
            "quantity": quantity,
            "opened_at": datetime.utcnow(),
        }

    def record_trade_close(self, symbol: str, pnl: float) -> None:
        """Record a closed position and update P&L."""
        self._roll_day_if_needed()

        if symbol in self.open_positions:
            del self.open_positions[symbol]

        self.daily_pnl += pnl
        self.total_realized_pnl += pnl

        drawdown_reason = self._check_drawdown()
        if drawdown_reason:
            self.halt_trading(drawdown_reason)
