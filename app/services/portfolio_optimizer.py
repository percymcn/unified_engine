"""
Portfolio Optimizer - 2026 Best Practices
==========================================

Optimal portfolio allocation using modern portfolio theory:
- Min-variance optimization via pyportfolioopt
- Black-Litterman for incorporating views
- Risk parity for balanced risk contribution
- Hierarchical Risk Parity (HRP) for robustness

Supports active basket: MES, NQ, RTY, GC, etc.

Pi5 optimized: ~100-300ms for optimization with 5-10 assets
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)

# Try to import pypfopt (pyportfolioopt)
try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
    from pypfopt import BlackLittermanModel, CovarianceShrinkage
    from pypfopt import HRPOpt, DiscreteAllocation
    from pypfopt import objective_functions
    PYPFOPT_AVAILABLE = True
except ImportError:
    PYPFOPT_AVAILABLE = False
    logger.warning("pypfopt not available - install with: pip install pyportfolioopt")

# Try scipy for fallback optimization
try:
    from scipy.optimize import minimize
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


@dataclass
class OptimizationConfig:
    """Configuration for portfolio optimization"""
    # Optimization method
    method: str = 'min_variance'  # 'min_variance', 'max_sharpe', 'risk_parity', 'hrp'

    # Constraints
    min_weight: float = 0.05  # Minimum 5% allocation
    max_weight: float = 0.40  # Maximum 40% per asset
    allow_short: bool = False

    # Risk parameters
    target_volatility: float = 0.15  # 15% annualized target vol
    risk_free_rate: float = 0.05  # 5% risk-free rate

    # Covariance estimation
    cov_method: str = 'shrinkage'  # 'sample', 'shrinkage', 'ewma'
    ewma_span: int = 60  # For EWMA covariance

    # Returns estimation
    returns_method: str = 'mean_historical'  # 'mean_historical', 'capm', 'ema'
    returns_lookback_days: int = 252

    # Rebalancing
    rebalance_threshold_pct: float = 5.0  # Rebalance if drift > 5%
    min_rebalance_interval_hours: int = 24

    # Black-Litterman (if using views)
    prior_weight: float = 0.5  # Weight of prior vs views


@dataclass
class PortfolioWeights:
    """Optimized portfolio weights"""
    weights: Dict[str, float]  # {ticker: weight}
    timestamp: datetime = field(default_factory=datetime.now)
    method_used: str = 'min_variance'

    # Risk metrics
    expected_return: float = 0.0
    expected_volatility: float = 0.0
    sharpe_ratio: float = 0.0

    # Diversification
    effective_n: float = 0.0  # Effective number of assets
    max_drawdown_expected: float = 0.0

    # Rebalancing info
    needs_rebalance: bool = False
    drift_from_target: Dict[str, float] = field(default_factory=dict)

    # Debug
    warnings: List[str] = field(default_factory=list)


@dataclass
class AllocationResult:
    """Discrete allocation for trading"""
    allocations: Dict[str, int]  # {ticker: number_of_contracts}
    leftover: float = 0.0  # Cash leftover
    total_value: float = 0.0

    # Per-asset details
    allocation_details: List[Dict] = field(default_factory=list)


class PortfolioOptimizer:
    """
    Portfolio optimization using modern portfolio theory.

    Supports:
    - Min-variance (least volatile for given return)
    - Max Sharpe (optimal risk-adjusted returns)
    - Risk Parity (equal risk contribution)
    - HRP (Hierarchical Risk Parity - robust to estimation error)
    """

    # Default futures basket
    DEFAULT_BASKET = ['MES', 'NQ', 'RTY', 'GC', 'CL']

    # Contract multipliers (approximate)
    CONTRACT_MULTIPLIERS = {
        'MES': 5,      # $5 per point
        'NQ': 2,       # $2 per point
        'RTY': 5,      # $5 per point
        'MYM': 0.5,    # $0.50 per point
        'GC': 10,      # $10 per point
        'MGC': 1,      # $1 per point
        'CL': 10,      # $10 per barrel
        'MCL': 1,      # $1 per barrel
    }

    def __init__(
        self,
        config: Optional[OptimizationConfig] = None,
        tickers: Optional[List[str]] = None
    ):
        self.config = config or OptimizationConfig()
        self.tickers = tickers or self.DEFAULT_BASKET

        # Price/returns history
        self.prices: Dict[str, deque] = {t: deque(maxlen=500) for t in self.tickers}
        self.returns: Dict[str, deque] = {t: deque(maxlen=500) for t in self.tickers}

        # Current weights and last optimization
        self.current_weights: Optional[PortfolioWeights] = None
        self.last_optimization: Optional[datetime] = None

        # Covariance matrix cache
        self.cov_matrix: Optional[pd.DataFrame] = None
        self.cov_matrix_timestamp: Optional[datetime] = None

        logger.info(
            f"PortfolioOptimizer initialized: method={self.config.method}, "
            f"tickers={self.tickers}, PYPFOPT={PYPFOPT_AVAILABLE}"
        )

    def update_prices(self, ticker: str, price: float, timestamp: Optional[datetime] = None):
        """Update price history for a ticker."""
        if ticker not in self.prices:
            self.prices[ticker] = deque(maxlen=500)
            self.returns[ticker] = deque(maxlen=500)

        # Calculate return if we have previous price
        if len(self.prices[ticker]) > 0:
            prev_price = self.prices[ticker][-1]
            if prev_price > 0:
                ret = (price - prev_price) / prev_price
                self.returns[ticker].append(ret)

        self.prices[ticker].append(price)

    def update_returns(self, ticker: str, daily_return: float):
        """Directly update returns (alternative to price updates)."""
        if ticker not in self.returns:
            self.returns[ticker] = deque(maxlen=500)

        self.returns[ticker].append(daily_return)

    def _build_returns_df(self) -> Optional[pd.DataFrame]:
        """Build DataFrame of returns for optimization."""
        if not self.returns:
            return None

        # Get minimum length across all tickers
        min_len = min(len(r) for r in self.returns.values() if len(r) > 0)

        if min_len < 30:
            logger.warning(f"Insufficient history: {min_len} periods (need 30+)")
            return None

        # Build DataFrame
        data = {}
        for ticker in self.tickers:
            if ticker in self.returns and len(self.returns[ticker]) >= min_len:
                data[ticker] = list(self.returns[ticker])[-min_len:]

        if len(data) < 2:
            return None

        return pd.DataFrame(data)

    def optimize(
        self,
        method: Optional[str] = None,
        views: Optional[Dict[str, float]] = None
    ) -> PortfolioWeights:
        """
        Run portfolio optimization.

        Args:
            method: Override optimization method
            views: Dict of {ticker: expected_return} for Black-Litterman

        Returns:
            PortfolioWeights with optimal allocation
        """
        method = method or self.config.method

        result = PortfolioWeights(
            weights={t: 0.0 for t in self.tickers},
            method_used=method
        )

        # Build returns DataFrame
        returns_df = self._build_returns_df()

        if returns_df is None:
            result.warnings.append("Insufficient data for optimization")
            # Equal weight fallback
            n = len(self.tickers)
            result.weights = {t: 1.0/n for t in self.tickers}
            return result

        # Try pypfopt first, then fallback
        if PYPFOPT_AVAILABLE:
            result = self._optimize_pypfopt(returns_df, method, views)
        elif SCIPY_AVAILABLE:
            result = self._optimize_scipy(returns_df, method)
        else:
            result.warnings.append("No optimization library available")
            n = len(self.tickers)
            result.weights = {t: 1.0/n for t in self.tickers}

        self.current_weights = result
        self.last_optimization = datetime.now()

        logger.info(
            f"📊 Portfolio optimized ({method}): "
            f"E[R]={result.expected_return:.1%} "
            f"Vol={result.expected_volatility:.1%} "
            f"Sharpe={result.sharpe_ratio:.2f}"
        )
        for ticker, weight in sorted(result.weights.items(), key=lambda x: -x[1]):
            logger.info(f"   {ticker}: {weight:.1%}")

        return result

    def _optimize_pypfopt(
        self,
        returns_df: pd.DataFrame,
        method: str,
        views: Optional[Dict[str, float]] = None
    ) -> PortfolioWeights:
        """Optimize using pypfopt library."""
        result = PortfolioWeights(
            weights={},
            method_used=method
        )

        try:
            # Calculate expected returns
            if self.config.returns_method == 'mean_historical':
                mu = expected_returns.mean_historical_return(returns_df)
            elif self.config.returns_method == 'ema':
                mu = expected_returns.ema_historical_return(returns_df)
            else:
                mu = expected_returns.mean_historical_return(returns_df)

            # Calculate covariance matrix
            if self.config.cov_method == 'shrinkage':
                S = CovarianceShrinkage(returns_df).ledoit_wolf()
            elif self.config.cov_method == 'ewma':
                S = risk_models.exp_cov(returns_df, span=self.config.ewma_span)
            else:
                S = risk_models.sample_cov(returns_df)

            self.cov_matrix = S
            self.cov_matrix_timestamp = datetime.now()

            # Apply Black-Litterman if views provided
            if views and method != 'hrp':
                prior = mu
                bl = BlackLittermanModel(S, pi=prior, absolute_views=views)
                mu = bl.bl_returns()
                S = bl.bl_cov()

            # Optimize based on method
            if method == 'min_variance':
                ef = EfficientFrontier(mu, S, weight_bounds=(
                    self.config.min_weight if not self.config.allow_short else -self.config.max_weight,
                    self.config.max_weight
                ))
                ef.min_volatility()
                weights = ef.clean_weights()

            elif method == 'max_sharpe':
                ef = EfficientFrontier(mu, S, weight_bounds=(
                    self.config.min_weight if not self.config.allow_short else -self.config.max_weight,
                    self.config.max_weight
                ))
                ef.max_sharpe(risk_free_rate=self.config.risk_free_rate)
                weights = ef.clean_weights()

            elif method == 'risk_parity':
                # Risk parity - equal risk contribution
                ef = EfficientFrontier(mu, S, weight_bounds=(0, self.config.max_weight))
                ef.add_objective(objective_functions.L2_reg, gamma=0.1)

                # Custom risk parity optimization
                def risk_parity_objective(w, cov_matrix):
                    vol = np.sqrt(w @ cov_matrix @ w)
                    marginal_contrib = cov_matrix @ w
                    risk_contrib = w * marginal_contrib / vol
                    target = vol / len(w)
                    return np.sum((risk_contrib - target) ** 2)

                n_assets = len(returns_df.columns)
                initial_weights = np.ones(n_assets) / n_assets
                bounds = [(self.config.min_weight, self.config.max_weight)] * n_assets
                constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}

                res = minimize(
                    risk_parity_objective,
                    initial_weights,
                    args=(S.values,),
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraints
                )

                weights = dict(zip(returns_df.columns, res.x))

            elif method == 'hrp':
                # Hierarchical Risk Parity - more robust
                hrp = HRPOpt(returns_df)
                hrp.optimize()
                weights = hrp.clean_weights()

            else:
                # Default to min variance
                ef = EfficientFrontier(mu, S)
                ef.min_volatility()
                weights = ef.clean_weights()

            result.weights = dict(weights)

            # Calculate portfolio metrics
            if method == 'hrp':
                # HRP doesn't use expected returns in the same way
                port_return = sum(mu.get(t, 0) * w for t, w in weights.items())
                w_array = np.array([weights.get(t, 0) for t in returns_df.columns])
                port_vol = np.sqrt(w_array @ S.values @ w_array)
            else:
                port_return = sum(mu.get(t, 0) * w for t, w in weights.items())
                w_array = np.array([weights.get(t, 0) for t in returns_df.columns])
                port_vol = np.sqrt(w_array @ S.values @ w_array)

            result.expected_return = float(port_return)
            result.expected_volatility = float(port_vol)

            if port_vol > 0:
                result.sharpe_ratio = (port_return - self.config.risk_free_rate) / port_vol
            else:
                result.sharpe_ratio = 0.0

            # Effective number of assets (diversification measure)
            # Higher = more diversified
            weights_array = np.array(list(weights.values()))
            result.effective_n = 1.0 / np.sum(weights_array ** 2)

            # Expected max drawdown (approximation)
            # MDD ≈ -σ * √(2 * log(T))
            trading_days = 252
            result.max_drawdown_expected = -port_vol * np.sqrt(2 * np.log(trading_days))

        except Exception as e:
            logger.error(f"pypfopt optimization failed: {e}")
            result.warnings.append(f"Optimization error: {str(e)}")
            # Equal weight fallback
            n = len(returns_df.columns)
            result.weights = {t: 1.0/n for t in returns_df.columns}

        return result

    def _optimize_scipy(
        self,
        returns_df: pd.DataFrame,
        method: str
    ) -> PortfolioWeights:
        """Fallback optimization using scipy."""
        result = PortfolioWeights(
            weights={},
            method_used=method
        )

        try:
            returns_array = returns_df.values
            n_assets = returns_array.shape[1]
            tickers = list(returns_df.columns)

            # Calculate mean returns and covariance
            mu = np.mean(returns_array, axis=0) * 252  # Annualize
            S = np.cov(returns_array.T) * 252

            # Objective functions
            def portfolio_volatility(w):
                return np.sqrt(w @ S @ w)

            def negative_sharpe(w):
                ret = w @ mu
                vol = portfolio_volatility(w)
                return -(ret - self.config.risk_free_rate) / vol if vol > 0 else 0

            # Constraints and bounds
            constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
            bounds = [(self.config.min_weight, self.config.max_weight)] * n_assets
            initial_weights = np.ones(n_assets) / n_assets

            # Optimize
            if method == 'min_variance':
                res = minimize(
                    portfolio_volatility,
                    initial_weights,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraints
                )
            else:  # max_sharpe
                res = minimize(
                    negative_sharpe,
                    initial_weights,
                    method='SLSQP',
                    bounds=bounds,
                    constraints=constraints
                )

            weights = dict(zip(tickers, res.x))
            result.weights = weights

            # Calculate metrics
            w = res.x
            result.expected_return = float(w @ mu)
            result.expected_volatility = float(portfolio_volatility(w))

            if result.expected_volatility > 0:
                result.sharpe_ratio = (
                    (result.expected_return - self.config.risk_free_rate) /
                    result.expected_volatility
                )

        except Exception as e:
            logger.error(f"scipy optimization failed: {e}")
            result.warnings.append(f"Optimization error: {str(e)}")
            n = len(returns_df.columns)
            result.weights = {t: 1.0/n for t in returns_df.columns}

        return result

    def get_discrete_allocation(
        self,
        total_capital: float,
        current_prices: Dict[str, float]
    ) -> AllocationResult:
        """
        Convert weights to discrete contract allocations.

        Args:
            total_capital: Total capital to allocate
            current_prices: Current prices {ticker: price}

        Returns:
            AllocationResult with number of contracts per ticker
        """
        result = AllocationResult(
            allocations={},
            total_value=total_capital
        )

        if self.current_weights is None:
            logger.warning("No optimized weights available")
            return result

        if PYPFOPT_AVAILABLE:
            try:
                # Use pypfopt DiscreteAllocation
                da = DiscreteAllocation(
                    self.current_weights.weights,
                    pd.Series(current_prices),
                    total_portfolio_value=total_capital
                )
                alloc, leftover = da.greedy_portfolio()

                result.allocations = alloc
                result.leftover = leftover

            except Exception as e:
                logger.warning(f"pypfopt discrete allocation failed: {e}")

        # Fallback to manual calculation
        if not result.allocations:
            for ticker, weight in self.current_weights.weights.items():
                if ticker in current_prices and weight > 0:
                    target_value = total_capital * weight
                    price = current_prices[ticker]
                    multiplier = self.CONTRACT_MULTIPLIERS.get(ticker, 1)
                    contract_value = price * multiplier

                    if contract_value > 0:
                        n_contracts = int(target_value / contract_value)
                        result.allocations[ticker] = n_contracts

            # Calculate leftover
            allocated = sum(
                result.allocations.get(t, 0) * current_prices.get(t, 0) *
                self.CONTRACT_MULTIPLIERS.get(t, 1)
                for t in result.allocations
            )
            result.leftover = total_capital - allocated

        # Build allocation details
        for ticker, n_contracts in result.allocations.items():
            price = current_prices.get(ticker, 0)
            multiplier = self.CONTRACT_MULTIPLIERS.get(ticker, 1)
            target_weight = self.current_weights.weights.get(ticker, 0)
            actual_value = n_contracts * price * multiplier
            actual_weight = actual_value / total_capital if total_capital > 0 else 0

            result.allocation_details.append({
                'ticker': ticker,
                'contracts': n_contracts,
                'price': price,
                'value': actual_value,
                'target_weight': target_weight,
                'actual_weight': actual_weight,
                'drift': actual_weight - target_weight
            })

        return result

    def check_rebalance_needed(
        self,
        current_values: Dict[str, float],
        total_value: float
    ) -> Tuple[bool, Dict[str, float]]:
        """
        Check if rebalancing is needed based on drift threshold.

        Args:
            current_values: Current value per ticker
            total_value: Total portfolio value

        Returns:
            (needs_rebalance, drift_dict)
        """
        if self.current_weights is None:
            return False, {}

        # Check minimum interval
        if self.last_optimization:
            hours_since = (datetime.now() - self.last_optimization).total_seconds() / 3600
            if hours_since < self.config.min_rebalance_interval_hours:
                return False, {}

        drift = {}
        max_drift = 0.0

        for ticker, target_weight in self.current_weights.weights.items():
            current_value = current_values.get(ticker, 0)
            current_weight = current_value / total_value if total_value > 0 else 0

            drift[ticker] = (current_weight - target_weight) * 100  # As percentage
            max_drift = max(max_drift, abs(drift[ticker]))

        needs_rebalance = max_drift > self.config.rebalance_threshold_pct

        if needs_rebalance:
            logger.info(f"Rebalance needed: max drift = {max_drift:.1f}%")

        return needs_rebalance, drift

    def get_correlation_matrix(self) -> Optional[pd.DataFrame]:
        """Get correlation matrix of returns."""
        returns_df = self._build_returns_df()
        if returns_df is None:
            return None
        return returns_df.corr()

    def get_status(self) -> Dict:
        """Get optimizer status."""
        return {
            'tickers': self.tickers,
            'method': self.config.method,
            'has_weights': self.current_weights is not None,
            'last_optimization': self.last_optimization.isoformat() if self.last_optimization else None,
            'weights': self.current_weights.weights if self.current_weights else {},
            'expected_return': self.current_weights.expected_return if self.current_weights else 0,
            'expected_volatility': self.current_weights.expected_volatility if self.current_weights else 0,
            'sharpe_ratio': self.current_weights.sharpe_ratio if self.current_weights else 0,
            'data_points': {t: len(self.returns.get(t, [])) for t in self.tickers},
            'pypfopt_available': PYPFOPT_AVAILABLE,
        }


# Global instance
_portfolio_optimizer: Optional[PortfolioOptimizer] = None


def get_portfolio_optimizer(tickers: Optional[List[str]] = None) -> PortfolioOptimizer:
    """Get or create global portfolio optimizer instance."""
    global _portfolio_optimizer
    if _portfolio_optimizer is None:
        _portfolio_optimizer = PortfolioOptimizer(tickers=tickers)
    return _portfolio_optimizer
