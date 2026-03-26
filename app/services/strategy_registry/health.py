"""
SmartFlow Strategy Health Monitor
==================================

Phase 10: Drift Detection + Strategy Health Scoring

Monitors strategy performance degradation by comparing current forward-test
metrics against baseline backtest metrics.

Features:
- Drift detection (Sharpe, win rate, drawdown)
- Health score (0-100) with configurable thresholds
- Auto-pause on critical health
- Health snapshot history
- Integration with allocator (penalize unhealthy strategies)
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.strategy_registry_models import (
    SmartFlowStrategy,
    StrategyBacktestSnapshot,
    StrategyForwardTestSnapshot,
)

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Strategy health status levels."""
    HEALTHY = "healthy"          # Health score >= 70
    DEGRADED = "degraded"        # Health score 40-69
    CRITICAL = "critical"        # Health score < 40
    UNKNOWN = "unknown"          # No forward test data yet


@dataclass
class DriftMetrics:
    """Drift metrics comparing baseline vs current performance."""
    # Baseline (from backtest)
    baseline_sharpe: Optional[float] = None
    baseline_win_rate: Optional[float] = None
    baseline_max_dd: Optional[float] = None
    baseline_trades: Optional[int] = None
    
    # Current (from forward test)
    current_sharpe: Optional[float] = None
    current_win_rate: Optional[float] = None
    current_max_dd: Optional[float] = None
    current_trades: Optional[int] = None
    
    # Drift calculations
    sharpe_drift_pct: Optional[float] = None  # Negative = degradation
    win_rate_drift_pct: Optional[float] = None
    drawdown_drift_pct: Optional[float] = None  # Positive = worse DD
    
    # Flags
    sharpe_drifted: bool = False
    win_rate_drifted: bool = False
    drawdown_drifted: bool = False
    insufficient_trades: bool = False


@dataclass
class HealthScore:
    """Comprehensive health score for a strategy."""
    score: float  # 0-100
    status: HealthStatus
    drift_metrics: DriftMetrics
    health_factors: Dict[str, float]  # Component scores
    timestamp: datetime
    notes: List[str]  # Human-readable health issues


class StrategyHealthMonitor:
    """
    Monitors strategy health by detecting performance drift.
    
    Compares forward-test metrics against baseline backtest metrics
    and calculates a composite health score.
    """
    
    def __init__(
        self,
        sharpe_drift_threshold: float = -0.20,  # -20% drift triggers alert
        win_rate_drift_threshold: float = -0.10,  # -10% drift
        drawdown_drift_threshold: float = 0.30,  # +30% worse DD
        min_trades_for_eval: int = 10,  # Need at least 10 trades
    ):
        """
        Initialize health monitor with drift thresholds.
        
        Args:
            sharpe_drift_threshold: Alert when Sharpe drops by this %
            win_rate_drift_threshold: Alert when win rate drops by this %
            drawdown_drift_threshold: Alert when drawdown increases by this %
            min_trades_for_eval: Minimum trades needed for evaluation
        """
        self.sharpe_drift_threshold = sharpe_drift_threshold
        self.win_rate_drift_threshold = win_rate_drift_threshold
        self.drawdown_drift_threshold = drawdown_drift_threshold
        self.min_trades_for_eval = min_trades_for_eval
        
        logger.info("✅ StrategyHealthMonitor initialized")
        logger.info(f"   Drift thresholds: Sharpe {sharpe_drift_threshold:.0%}, "
                   f"WinRate {win_rate_drift_threshold:.0%}, DD {drawdown_drift_threshold:.0%}")
    
    def calculate_drift(
        self,
        db: Session,
        strategy_id: str
    ) -> Optional[DriftMetrics]:
        """
        Calculate drift metrics for a strategy.
        
        Args:
            db: Database session
            strategy_id: Strategy to evaluate
            
        Returns:
            DriftMetrics or None if insufficient data
        """
        # Get baseline from latest backtest snapshot
        baseline_snapshot = db.query(StrategyBacktestSnapshot).filter(
            StrategyBacktestSnapshot.strategy_id == strategy_id
        ).order_by(desc(StrategyBacktestSnapshot.snapshot_at)).first()
        
        # Get current from latest forward test snapshot
        current_snapshot = db.query(StrategyForwardTestSnapshot).filter(
            StrategyForwardTestSnapshot.strategy_id == strategy_id
        ).order_by(desc(StrategyForwardTestSnapshot.snapshot_at)).first()
        
        if not baseline_snapshot:
            logger.warning(f"No baseline backtest for {strategy_id}")
            return None
            
        if not current_snapshot:
            logger.warning(f"No forward test data for {strategy_id}")
            return None
        
        # Initialize drift metrics
        drift = DriftMetrics(
            baseline_sharpe=baseline_snapshot.sharpe_ratio,
            baseline_win_rate=baseline_snapshot.win_rate,
            baseline_max_dd=baseline_snapshot.max_drawdown,
            baseline_trades=baseline_snapshot.total_trades,
            current_trades=current_snapshot.total_trades,
            current_win_rate=current_snapshot.win_rate,
            current_max_dd=current_snapshot.max_drawdown,
        )
        
        # Check if we have enough trades
        if current_snapshot.total_trades < self.min_trades_for_eval:
            drift.insufficient_trades = True
            return drift
        
        # Calculate Sharpe drift (requires profit factor as proxy if sharpe not available)
        if baseline_snapshot.sharpe_ratio and current_snapshot.profit_factor:
            # Approximate Sharpe from profit factor (rough conversion)
            current_sharpe_approx = (current_snapshot.profit_factor - 1.0) * 1.5
            drift.current_sharpe = current_sharpe_approx
            drift.sharpe_drift_pct = (
                (current_sharpe_approx - baseline_snapshot.sharpe_ratio) /
                baseline_snapshot.sharpe_ratio
            )
            drift.sharpe_drifted = drift.sharpe_drift_pct < self.sharpe_drift_threshold
        
        # Calculate win rate drift
        if baseline_snapshot.win_rate and current_snapshot.win_rate:
            drift.win_rate_drift_pct = (
                (current_snapshot.win_rate - baseline_snapshot.win_rate) /
                baseline_snapshot.win_rate
            )
            drift.win_rate_drifted = drift.win_rate_drift_pct < self.win_rate_drift_threshold
        
        # Calculate drawdown drift (positive = worse)
        if baseline_snapshot.max_drawdown and current_snapshot.max_drawdown:
            drift.drawdown_drift_pct = (
                (current_snapshot.max_drawdown - baseline_snapshot.max_drawdown) /
                baseline_snapshot.max_drawdown
            )
            drift.drawdown_drifted = drift.drawdown_drift_pct > self.drawdown_drift_threshold
        
        return drift
    
    def calculate_health_score(
        self,
        drift: Optional[DriftMetrics]
    ) -> HealthScore:
        """
        Calculate composite health score from drift metrics.
        
        Args:
            drift: Drift metrics
            
        Returns:
            HealthScore with 0-100 score and status
        """
        notes = []
        health_factors = {}
        
        if not drift:
            return HealthScore(
                score=50.0,
                status=HealthStatus.UNKNOWN,
                drift_metrics=DriftMetrics(),
                health_factors={},
                timestamp=datetime.now(timezone.utc),
                notes=["No data available for health calculation"]
            )
        
        if drift.insufficient_trades:
            return HealthScore(
                score=60.0,
                status=HealthStatus.UNKNOWN,
                drift_metrics=drift,
                health_factors={"trades": 60.0},
                timestamp=datetime.now(timezone.utc),
                notes=[f"Insufficient trades ({drift.current_trades}/{self.min_trades_for_eval})"]
            )
        
        # Component scores (0-100 each)
        sharpe_score = 100.0
        win_rate_score = 100.0
        drawdown_score = 100.0
        
        # Sharpe component
        if drift.sharpe_drift_pct is not None:
            if drift.sharpe_drifted:
                # Scale: -20% drift = 50 score, -40% drift = 0 score
                sharpe_score = max(0, 100 + (drift.sharpe_drift_pct / 0.004) * 100)
                notes.append(f"Sharpe degraded {drift.sharpe_drift_pct:.1%}")
            else:
                # Positive drift boosts score
                sharpe_score = min(100, 100 + (drift.sharpe_drift_pct * 50))
        health_factors["sharpe"] = sharpe_score
        
        # Win rate component
        if drift.win_rate_drift_pct is not None:
            if drift.win_rate_drifted:
                # Scale: -10% drift = 50 score, -20% drift = 0 score
                win_rate_score = max(0, 100 + (drift.win_rate_drift_pct / 0.002) * 100)
                notes.append(f"Win rate down {drift.win_rate_drift_pct:.1%}")
            else:
                win_rate_score = min(100, 100 + (drift.win_rate_drift_pct * 50))
        health_factors["win_rate"] = win_rate_score
        
        # Drawdown component
        if drift.drawdown_drift_pct is not None:
            if drift.drawdown_drifted:
                # Scale: +30% drift = 50 score, +60% drift = 0 score
                drawdown_score = max(0, 100 - (drift.drawdown_drift_pct / 0.006) * 100)
                notes.append(f"Drawdown worse by {drift.drawdown_drift_pct:.1%}")
            else:
                # Improvement (negative drift) boosts score
                drawdown_score = min(100, 100 - (drift.drawdown_drift_pct * 50))
        health_factors["drawdown"] = drawdown_score
        
        # Composite score (weighted average)
        composite = (
            sharpe_score * 0.40 +
            win_rate_score * 0.35 +
            drawdown_score * 0.25
        )
        
        # Determine status
        if composite >= 70:
            status = HealthStatus.HEALTHY
        elif composite >= 40:
            status = HealthStatus.DEGRADED
            notes.append("Strategy showing performance degradation")
        else:
            status = HealthStatus.CRITICAL
            notes.append("⚠️ CRITICAL: Significant performance degradation")
        
        return HealthScore(
            score=round(composite, 1),
            status=status,
            drift_metrics=drift,
            health_factors=health_factors,
            timestamp=datetime.now(timezone.utc),
            notes=notes
        )
    
    def evaluate_strategy_health(
        self,
        db: Session,
        strategy_id: str,
        auto_pause_on_critical: bool = True
    ) -> HealthScore:
        """
        Full health evaluation for a strategy.
        
        Args:
            db: Database session
            strategy_id: Strategy to evaluate
            auto_pause_on_critical: Auto-pause if health is critical
            
        Returns:
            HealthScore with complete health assessment
        """
        # Calculate drift
        drift = self.calculate_drift(db, strategy_id)
        
        # Calculate health score
        health = self.calculate_health_score(drift)
        
        # Update strategy health fields
        strategy = db.query(SmartFlowStrategy).filter(
            SmartFlowStrategy.strategy_id == strategy_id
        ).first()
        
        if strategy:
            strategy.health_status = health.status.value
            strategy.health_checked_at = health.timestamp
            strategy.health_notes = "; ".join(health.notes) if health.notes else None
            
            # Auto-pause on critical health
            if auto_pause_on_critical and health.status == HealthStatus.CRITICAL:
                if not strategy.is_paused:
                    strategy.is_paused = True
                    strategy.paused_at = health.timestamp
                    strategy.paused_by = "auto_health_monitor"
                    health.notes.append("⚠️ Strategy auto-paused due to critical health")
                    logger.warning(f"🚨 Auto-paused {strategy_id} due to critical health (score={health.score})")
            
            db.commit()
            db.refresh(strategy)
        
        logger.info(f"✅ Health evaluated for {strategy_id}: {health.status.value} (score={health.score})")
        
        return health
    
    def get_health_penalty_factor(self, health_score: float) -> float:
        """
        Get allocation penalty factor based on health score.
        
        Used by allocator to penalize unhealthy strategies.
        
        Args:
            health_score: Health score 0-100
            
        Returns:
            Penalty factor 0-1 (1 = no penalty, 0 = excluded)
        """
        if health_score >= 70:
            return 1.0  # Healthy, no penalty
        elif health_score >= 40:
            # Degraded: linear penalty from 1.0 to 0.5
            return 0.5 + (health_score - 40) / 60
        else:
            # Critical: severe penalty from 0.5 to 0.0
            return max(0.0, health_score / 80)


# Global instance
_health_monitor: Optional[StrategyHealthMonitor] = None


def get_health_monitor() -> StrategyHealthMonitor:
    """Get or create global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = StrategyHealthMonitor()
    return _health_monitor


def should_exclude_from_allocation(
    strategy: SmartFlowStrategy,
    require_healthy: bool = False
) -> bool:
    """
    Check if strategy should be excluded from allocation.
    
    Args:
        strategy: Strategy to check
        require_healthy: If True, exclude anything not HEALTHY
        
    Returns:
        True if strategy should be excluded
    """
    # Always exclude paused strategies
    if strategy.is_paused:
        return True
    
    # Exclude critical health
    if strategy.health_status == HealthStatus.CRITICAL.value:
        return True
    
    # Optionally exclude degraded
    if require_healthy and strategy.health_status == HealthStatus.DEGRADED.value:
        return True
    
    return False
