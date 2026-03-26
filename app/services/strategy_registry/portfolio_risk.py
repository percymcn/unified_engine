"""
SmartFlow Portfolio Risk Engine
================================

Phase 11: Portfolio-level risk management and budgeting

Aggregates risk across all active strategies and provides:
- Portfolio VaR (Value at Risk) calculation
- Correlation-aware risk budgeting
- Max drawdown enforcement
- Dynamic leverage adjustment
- Position sizing recommendations based on portfolio risk

Integrates with StrategyAllocator to apply portfolio-level constraints.
"""

import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.strategy_registry_models import (
    SmartFlowStrategy,
    StrategyForwardTestSnapshot,
)

logger = logging.getLogger(__name__)


@dataclass
class PortfolioRiskConfig:
    """Portfolio risk management configuration."""
    # Portfolio limits
    max_portfolio_risk_pct: float = 15.0  # Max 15% of capital at risk
    max_drawdown_pct: float = 20.0  # Max 20% drawdown before halting
    max_leverage: float = 2.0  # Max 2x leverage
    
    # VaR parameters
    var_confidence: float = 0.95  # 95% confidence VaR
    var_lookback_days: int = 20
    
    # Correlation parameters
    correlation_threshold: float = 0.7  # High correlation threshold
    correlation_penalty: float = 0.5  # Reduce allocation by 50% for correlated strategies
    
    # Risk budgeting
    total_risk_budget: float = 100.0  # Total risk units available
    min_strategy_allocation_pct: float = 5.0  # Min 5% allocation per strategy
    max_strategy_allocation_pct: float = 40.0  # Max 40% allocation per strategy
    
    # Dynamic adjustment
    drawdown_scale_factor: float = 0.5  # Reduce leverage by 50% per 10% drawdown


@dataclass
class StrategyRiskMetrics:
    """Risk metrics for a single strategy."""
    strategy_id: str
    
    # Volatility
    daily_vol: Optional[float] = None  # Daily volatility
    annual_vol: Optional[float] = None  # Annualized volatility
    
    # Drawdown
    current_drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    
    # VaR
    var_95: Optional[float] = None  # 95% VaR
    cvar_95: Optional[float] = None  # 95% CVaR (expected shortfall)
    
    # Correlation with portfolio
    portfolio_correlation: float = 0.0
    
    # Risk contribution
    marginal_var: Optional[float] = None  # Contribution to portfolio VaR
    risk_budget_used: float = 0.0  # Risk units consumed


@dataclass
class PortfolioRiskSnapshot:
    """Portfolio-level risk snapshot."""
    timestamp: datetime
    
    # Portfolio metrics
    total_strategies: int = 0
    active_strategies: int = 0
    total_allocation_pct: float = 0.0
    
    # Risk metrics
    portfolio_var: Optional[float] = None  # Portfolio VaR
    portfolio_cvar: Optional[float] = None  # Portfolio CVaR
    portfolio_volatility: Optional[float] = None  # Portfolio volatility
    portfolio_sharpe: Optional[float] = None  # Portfolio Sharpe ratio
    
    # Drawdown
    current_drawdown_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    
    # Leverage
    current_leverage: float = 1.0
    recommended_leverage: float = 1.0
    
    # Risk budget
    risk_budget_used: float = 0.0  # Out of 100
    risk_budget_available: float = 100.0
    
    # Flags
    is_halted: bool = False
    halt_reason: str = ''
    
    # Strategy contributions
    strategy_risks: List[StrategyRiskMetrics] = field(default_factory=list)


class PortfolioRiskEngine:
    """
    Portfolio-level risk management engine.
    
    Aggregates risk across strategies and provides portfolio-level
    risk metrics, constraints, and sizing recommendations.
    """
    
    def __init__(self, config: Optional[PortfolioRiskConfig] = None):
        """
        Initialize portfolio risk engine.
        
        Args:
            config: Risk configuration (uses defaults if None)
        """
        self.config = config or PortfolioRiskConfig()
        
        # Risk state
        self.current_portfolio_dd = 0.0
        self.portfolio_peak = 0.0
        
        logger.info("✅ PortfolioRiskEngine initialized")
        logger.info(f"   Max portfolio risk: {self.config.max_portfolio_risk_pct}%")
        logger.info(f"   Max drawdown: {self.config.max_drawdown_pct}%")
        logger.info(f"   VaR confidence: {self.config.var_confidence:.0%}")
    
    def calculate_strategy_volatility(
        self,
        db: Session,
        strategy_id: str,
        lookback_days: int = 20
    ) -> Optional[float]:
        """
        Calculate strategy volatility from forward test results.
        
        Args:
            db: Database session
            strategy_id: Strategy to analyze
            lookback_days: Days of history to use
            
        Returns:
            Daily volatility or None if insufficient data
        """
        # Get recent forward test snapshots
        snapshots = db.query(StrategyForwardTestSnapshot).filter(
            StrategyForwardTestSnapshot.strategy_id == strategy_id
        ).order_by(desc(StrategyForwardTestSnapshot.snapshot_at)).limit(lookback_days).all()
        
        if len(snapshots) < 5:  # Need at least 5 days
            return None
        
        # Calculate returns from PnL
        returns = []
        for i in range(len(snapshots) - 1):
            if snapshots[i].total_pnl and snapshots[i+1].total_pnl:
                ret = (snapshots[i].total_pnl - snapshots[i+1].total_pnl) / abs(snapshots[i+1].total_pnl + 1e-8)
                returns.append(ret)
        
        if not returns:
            return None
        
        # Daily volatility
        return float(np.std(returns))
    
    def calculate_var(
        self,
        returns: List[float],
        confidence: float = 0.95
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate VaR and CVaR from returns.
        
        Args:
            returns: List of historical returns
            confidence: VaR confidence level
            
        Returns:
            (VaR, CVaR) tuple or (None, None) if insufficient data
        """
        if len(returns) < 10:
            return None, None
        
        returns_array = np.array(returns)
        
        # VaR: percentile of losses
        var = float(np.percentile(returns_array, (1 - confidence) * 100))
        
        # CVaR: mean of returns below VaR
        cvar_returns = returns_array[returns_array <= var]
        cvar = float(np.mean(cvar_returns)) if len(cvar_returns) > 0 else var
        
        return var, cvar
    
    def estimate_correlation_matrix(
        self,
        db: Session,
        strategy_ids: List[str],
        lookback_days: int = 20
    ) -> Dict[str, Dict[str, float]]:
        """
        Estimate correlation matrix between strategies.
        
        Args:
            db: Database session
            strategy_ids: List of strategy IDs
            lookback_days: Days of history
            
        Returns:
            Correlation matrix as nested dict
        """
        # Get returns for each strategy
        strategy_returns = {}
        
        for strategy_id in strategy_ids:
            snapshots = db.query(StrategyForwardTestSnapshot).filter(
                StrategyForwardTestSnapshot.strategy_id == strategy_id
            ).order_by(desc(StrategyForwardTestSnapshot.snapshot_at)).limit(lookback_days).all()
            
            if len(snapshots) < 5:
                continue
            
            returns = []
            for i in range(len(snapshots) - 1):
                if snapshots[i].total_pnl and snapshots[i+1].total_pnl:
                    ret = (snapshots[i].total_pnl - snapshots[i+1].total_pnl) / abs(snapshots[i+1].total_pnl + 1e-8)
                    returns.append(ret)
            
            if returns:
                strategy_returns[strategy_id] = returns
        
        # Calculate correlation matrix
        corr_matrix = {}
        for sid1 in strategy_ids:
            corr_matrix[sid1] = {}
            for sid2 in strategy_ids:
                if sid1 == sid2:
                    corr_matrix[sid1][sid2] = 1.0
                elif sid1 in strategy_returns and sid2 in strategy_returns:
                    # Align returns (use minimum length)
                    len1 = len(strategy_returns[sid1])
                    len2 = len(strategy_returns[sid2])
                    min_len = min(len1, len2)
                    
                    if min_len >= 5:
                        r1 = np.array(strategy_returns[sid1][:min_len])
                        r2 = np.array(strategy_returns[sid2][:min_len])
                        corr = float(np.corrcoef(r1, r2)[0, 1])
                        corr_matrix[sid1][sid2] = corr
                    else:
                        corr_matrix[sid1][sid2] = 0.0
                else:
                    corr_matrix[sid1][sid2] = 0.0
        
        return corr_matrix
    
    def calculate_portfolio_risk(
        self,
        db: Session,
        strategy_allocations: Dict[str, float]  # {strategy_id: weight}
    ) -> PortfolioRiskSnapshot:
        """
        Calculate comprehensive portfolio risk metrics.
        
        Args:
            db: Database session
            strategy_allocations: Strategy weights (should sum to 1.0)
            
        Returns:
            PortfolioRiskSnapshot with all risk metrics
        """
        snapshot = PortfolioRiskSnapshot(
            timestamp=datetime.now(timezone.utc),
            total_strategies=len(strategy_allocations),
            active_strategies=len([w for w in strategy_allocations.values() if w > 0]),
            total_allocation_pct=sum(strategy_allocations.values()) * 100
        )
        
        if not strategy_allocations:
            return snapshot
        
        strategy_ids = list(strategy_allocations.keys())
        
        # Calculate individual strategy risks
        strategy_vols = {}
        strategy_vars = {}
        
        for strategy_id in strategy_ids:
            # Get volatility
            vol = self.calculate_strategy_volatility(db, strategy_id, self.config.var_lookback_days)
            strategy_vols[strategy_id] = vol or 0.0
            
            # Get VaR (simplified: use volatility-based estimate)
            if vol:
                # Assuming normal distribution: VaR = z * volatility
                z_score = 1.645  # 95% confidence
                var = -z_score * vol
                strategy_vars[strategy_id] = var
            else:
                strategy_vars[strategy_id] = 0.0
            
            # Create strategy risk metrics
            strategy_risk = StrategyRiskMetrics(
                strategy_id=strategy_id,
                daily_vol=vol,
                annual_vol=vol * np.sqrt(252) if vol else None,
                var_95=strategy_vars[strategy_id]
            )
            snapshot.strategy_risks.append(strategy_risk)
        
        # Calculate correlation matrix
        corr_matrix = self.estimate_correlation_matrix(db, strategy_ids, self.config.var_lookback_days)
        
        # Calculate portfolio volatility (weighted sum with correlations)
        portfolio_var = 0.0
        for i, sid1 in enumerate(strategy_ids):
            for j, sid2 in enumerate(strategy_ids):
                w1 = strategy_allocations.get(sid1, 0.0)
                w2 = strategy_allocations.get(sid2, 0.0)
                vol1 = strategy_vols.get(sid1, 0.0)
                vol2 = strategy_vols.get(sid2, 0.0)
                corr = corr_matrix.get(sid1, {}).get(sid2, 0.0)
                
                portfolio_var += w1 * w2 * vol1 * vol2 * corr
        
        portfolio_vol = np.sqrt(max(portfolio_var, 0.0))
        snapshot.portfolio_volatility = float(portfolio_vol)
        
        # Portfolio VaR (simplified)
        z_score = 1.645  # 95% confidence
        snapshot.portfolio_var = -z_score * portfolio_vol if portfolio_vol > 0 else 0.0
        
        # Portfolio CVaR (assume CVaR = 1.3 * VaR for normal distribution)
        snapshot.portfolio_cvar = snapshot.portfolio_var * 1.3 if snapshot.portfolio_var else 0.0
        
        # Calculate risk budget usage
        # Simple model: each strategy consumes risk budget proportional to weight * volatility
        total_risk_contribution = sum(
            strategy_allocations.get(sid, 0.0) * strategy_vols.get(sid, 0.0)
            for sid in strategy_ids
        )
        
        if total_risk_contribution > 0:
            for strategy_risk in snapshot.strategy_risks:
                sid = strategy_risk.strategy_id
                weight = strategy_allocations.get(sid, 0.0)
                vol = strategy_vols.get(sid, 0.0)
                contribution = weight * vol
                
                # Risk budget used (as percentage of total)
                risk_pct = (contribution / total_risk_contribution) * 100
                strategy_risk.risk_budget_used = risk_pct
        
        # Total risk budget used
        snapshot.risk_budget_used = min(total_risk_contribution * 100, 100.0)
        snapshot.risk_budget_available = 100.0 - snapshot.risk_budget_used
        
        # Check for halts
        if snapshot.current_drawdown_pct > self.config.max_drawdown_pct:
            snapshot.is_halted = True
            snapshot.halt_reason = f"Max drawdown exceeded ({snapshot.current_drawdown_pct:.1f}% > {self.config.max_drawdown_pct}%)"
        
        if snapshot.risk_budget_used > self.config.max_portfolio_risk_pct:
            snapshot.is_halted = True
            snapshot.halt_reason = f"Max portfolio risk exceeded ({snapshot.risk_budget_used:.1f}% > {self.config.max_portfolio_risk_pct}%)"
        
        # Recommended leverage based on risk
        if snapshot.portfolio_volatility and snapshot.portfolio_volatility > 0:
            # Target volatility approach
            target_vol = 0.10  # 10% daily target
            snapshot.recommended_leverage = min(
                target_vol / snapshot.portfolio_volatility,
                self.config.max_leverage
            )
        else:
            snapshot.recommended_leverage = 1.0
        
        snapshot.current_leverage = 1.0  # Default, can be updated based on actual positions
        
        logger.info(f"📊 Portfolio Risk: Vol={snapshot.portfolio_volatility:.2%}, VaR={snapshot.portfolio_var:.2%}, "
                   f"Budget={snapshot.risk_budget_used:.1f}%")
        
        return snapshot
    
    def apply_correlation_penalty(
        self,
        strategy_allocations: Dict[str, float],
        correlation_matrix: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Apply correlation penalty to reduce allocation for highly correlated strategies.
        
        Args:
            strategy_allocations: Original allocations
            correlation_matrix: Strategy correlations
            
        Returns:
            Adjusted allocations with correlation penalties applied
        """
        adjusted = strategy_allocations.copy()
        
        for sid1 in strategy_allocations.keys():
            corr_penalty = 0.0
            
            for sid2 in strategy_allocations.keys():
                if sid1 != sid2:
                    corr = correlation_matrix.get(sid1, {}).get(sid2, 0.0)
                    
                    if abs(corr) > self.config.correlation_threshold:
                        # Apply penalty proportional to correlation strength
                        corr_penalty += abs(corr) - self.config.correlation_threshold
            
            if corr_penalty > 0:
                # Reduce allocation
                penalty_factor = 1.0 - min(corr_penalty * self.config.correlation_penalty, 0.8)
                adjusted[sid1] *= penalty_factor
                logger.info(f"   Correlation penalty for {sid1}: {penalty_factor:.2f}x")
        
        # Renormalize weights to sum to 1.0
        total_weight = sum(adjusted.values())
        if total_weight > 0:
            for sid in adjusted.keys():
                adjusted[sid] /= total_weight
        
        return adjusted


# Global instance
_portfolio_risk_engine: Optional[PortfolioRiskEngine] = None


def get_portfolio_risk_engine(config: Optional[PortfolioRiskConfig] = None) -> PortfolioRiskEngine:
    """Get or create global portfolio risk engine instance."""
    global _portfolio_risk_engine
    if _portfolio_risk_engine is None:
        _portfolio_risk_engine = PortfolioRiskEngine(config)
    return _portfolio_risk_engine
