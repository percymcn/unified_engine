"""
SmartFlow Execution Quality Tracker
====================================

Phase 12: Execution Quality / Execution Modeling

Tracks and analyzes execution performance metrics:
- Slippage (expected vs actual fill prices)
- Fill rates (partial fills, rejections)
- Execution timing (latency from signal to fill)
- Spread costs
- Market impact

Provides execution quality scores to feed back into strategy evaluation.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Execution status types."""
    FILLED = "filled"
    PARTIAL = "partial"
    REJECTED = "rejected"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class ExecutionMetrics:
    """Execution quality metrics for a single trade."""
    trade_id: str
    strategy_id: str
    
    # Timing
    signal_time: datetime
    order_time: Optional[datetime] = None
    fill_time: Optional[datetime] = None
    
    # Latency (milliseconds)
    signal_to_order_ms: Optional[float] = None
    order_to_fill_ms: Optional[float] = None
    total_latency_ms: Optional[float] = None
    
    # Prices
    expected_price: float = 0.0
    actual_price: Optional[float] = None
    
    # Slippage
    slippage_bps: Optional[float] = None  # Basis points
    slippage_pct: Optional[float] = None  # Percentage
    
    # Fill quality
    requested_qty: float = 0.0
    filled_qty: float = 0.0
    fill_rate: float = 0.0  # filled_qty / requested_qty
    status: ExecutionStatus = ExecutionStatus.PENDING
    
    # Costs
    spread_bps: Optional[float] = None
    commission: Optional[float] = None
    estimated_impact: Optional[float] = None
    
    # Market conditions
    volatility_at_signal: Optional[float] = None
    volume_at_signal: Optional[float] = None


@dataclass
class StrategyExecutionQuality:
    """Aggregated execution quality for a strategy."""
    strategy_id: str
    
    # Counts
    total_signals: int = 0
    total_fills: int = 0
    total_rejections: int = 0
    total_partials: int = 0
    
    # Fill rates
    avg_fill_rate: float = 0.0
    complete_fill_pct: float = 0.0
    
    # Slippage stats
    avg_slippage_bps: float = 0.0
    median_slippage_bps: float = 0.0
    worst_slippage_bps: float = 0.0
    favorable_slippage_count: int = 0
    adverse_slippage_count: int = 0
    
    # Timing stats
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    
    # Quality score (0-100)
    execution_quality_score: float = 100.0
    
    # Period
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ExecutionQualityTracker:
    """
    Tracks and analyzes execution quality metrics.
    
    Provides feedback loop from actual execution performance
    back to strategy evaluation and allocation.
    """
    
    def __init__(self):
        """Initialize execution quality tracker."""
        self.executions: List[ExecutionMetrics] = []
        logger.info("✅ ExecutionQualityTracker initialized")
    
    def record_execution(
        self,
        trade_id: str,
        strategy_id: str,
        signal_time: datetime,
        expected_price: float,
        requested_qty: float,
        order_time: Optional[datetime] = None,
        fill_time: Optional[datetime] = None,
        actual_price: Optional[float] = None,
        filled_qty: Optional[float] = None,
        status: ExecutionStatus = ExecutionStatus.PENDING
    ) -> ExecutionMetrics:
        """
        Record execution metrics for a trade.
        
        Args:
            trade_id: Unique trade identifier
            strategy_id: Strategy that generated signal
            signal_time: When signal was generated
            expected_price: Expected fill price at signal time
            requested_qty: Requested position size
            order_time: When order was placed
            fill_time: When order was filled
            actual_price: Actual fill price
            filled_qty: Actual filled quantity
            status: Execution status
            
        Returns:
            ExecutionMetrics object
        """
        metrics = ExecutionMetrics(
            trade_id=trade_id,
            strategy_id=strategy_id,
            signal_time=signal_time,
            expected_price=expected_price,
            requested_qty=requested_qty,
            order_time=order_time,
            fill_time=fill_time,
            actual_price=actual_price,
            filled_qty=filled_qty or 0.0,
            status=status
        )
        
        # Calculate latencies
        if order_time:
            metrics.signal_to_order_ms = (order_time - signal_time).total_seconds() * 1000
        
        if fill_time and order_time:
            metrics.order_to_fill_ms = (fill_time - order_time).total_seconds() * 1000
        
        if fill_time and signal_time:
            metrics.total_latency_ms = (fill_time - signal_time).total_seconds() * 1000
        
        # Calculate slippage
        if actual_price and expected_price:
            # Slippage in basis points (1 bp = 0.01%)
            slippage = (actual_price - expected_price) / expected_price
            metrics.slippage_pct = slippage
            metrics.slippage_bps = slippage * 10000
        
        # Calculate fill rate
        if requested_qty > 0:
            metrics.fill_rate = metrics.filled_qty / requested_qty
        
        self.executions.append(metrics)
        
        logger.info(
            f"📊 Execution recorded: {trade_id} | {strategy_id} | "
            f"Slippage: {metrics.slippage_bps:.1f}bp | Fill: {metrics.fill_rate:.1%}"
        )
        
        return metrics
    
    def calculate_strategy_quality(
        self,
        strategy_id: str,
        lookback_trades: int = 100
    ) -> StrategyExecutionQuality:
        """
        Calculate aggregated execution quality for a strategy.
        
        Args:
            strategy_id: Strategy to analyze
            lookback_trades: Number of recent trades to analyze
            
        Returns:
            StrategyExecutionQuality metrics
        """
        # Filter executions for this strategy
        strategy_execs = [
            e for e in self.executions
            if e.strategy_id == strategy_id
        ][-lookback_trades:]
        
        if not strategy_execs:
            return StrategyExecutionQuality(strategy_id=strategy_id)
        
        quality = StrategyExecutionQuality(
            strategy_id=strategy_id,
            total_signals=len(strategy_execs)
        )
        
        # Count statuses
        quality.total_fills = sum(1 for e in strategy_execs if e.status == ExecutionStatus.FILLED)
        quality.total_rejections = sum(1 for e in strategy_execs if e.status == ExecutionStatus.REJECTED)
        quality.total_partials = sum(1 for e in strategy_execs if e.status == ExecutionStatus.PARTIAL)
        
        # Fill rates
        filled_execs = [e for e in strategy_execs if e.status in [ExecutionStatus.FILLED, ExecutionStatus.PARTIAL]]
        if filled_execs:
            quality.avg_fill_rate = sum(e.fill_rate for e in filled_execs) / len(filled_execs)
            quality.complete_fill_pct = quality.total_fills / len(strategy_execs)
        
        # Slippage stats
        slippages = [e.slippage_bps for e in filled_execs if e.slippage_bps is not None]
        if slippages:
            quality.avg_slippage_bps = sum(slippages) / len(slippages)
            quality.median_slippage_bps = sorted(slippages)[len(slippages) // 2]
            quality.worst_slippage_bps = max(abs(s) for s in slippages)
            quality.favorable_slippage_count = sum(1 for s in slippages if s < 0)  # Negative = better than expected
            quality.adverse_slippage_count = sum(1 for s in slippages if s > 0)
        
        # Latency stats
        latencies = [e.total_latency_ms for e in filled_execs if e.total_latency_ms is not None]
        if latencies:
            quality.avg_latency_ms = sum(latencies) / len(latencies)
            quality.p95_latency_ms = sorted(latencies)[int(len(latencies) * 0.95)]
        
        # Calculate execution quality score (0-100)
        score = 100.0
        
        # Penalty for low fill rates
        if quality.avg_fill_rate < 0.95:
            score -= (0.95 - quality.avg_fill_rate) * 200  # -10 points per 5% below 95%
        
        # Penalty for adverse slippage
        if quality.avg_slippage_bps > 0:
            score -= min(quality.avg_slippage_bps, 50)  # Up to -50 points for 50bp slippage
        
        # Penalty for high latency
        if quality.avg_latency_ms > 1000:  # >1 second is slow
            score -= min((quality.avg_latency_ms - 1000) / 100, 30)  # Up to -30 points
        
        # Penalty for rejections
        rejection_rate = quality.total_rejections / len(strategy_execs)
        if rejection_rate > 0.05:  # >5% rejections
            score -= min(rejection_rate * 200, 20)  # Up to -20 points
        
        quality.execution_quality_score = max(0.0, min(100.0, score))
        
        # Period
        if strategy_execs:
            quality.start_date = min(e.signal_time for e in strategy_execs)
            quality.end_date = max(e.signal_time for e in strategy_execs)
        
        logger.info(
            f"✅ Execution quality for {strategy_id}: "
            f"Score={quality.execution_quality_score:.1f}, "
            f"AvgSlippage={quality.avg_slippage_bps:.1f}bp, "
            f"FillRate={quality.avg_fill_rate:.1%}"
        )
        
        return quality


# Global instance
_execution_tracker: Optional[ExecutionQualityTracker] = None


def get_execution_tracker() -> ExecutionQualityTracker:
    """Get or create global execution quality tracker instance."""
    global _execution_tracker
    if _execution_tracker is None:
        _execution_tracker = ExecutionQualityTracker()
    return _execution_tracker
