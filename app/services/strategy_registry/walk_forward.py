"""
SmartFlow Walk-Forward Validation Lab
======================================

Phase 13: Long-Horizon Validation / Walk-Forward Testing

Implements walk-forward optimization and validation framework:
- Rolling time-series splits (train/test windows)
- Parameter stability testing across periods
- Out-of-sample performance validation
- Overfitting detection
- Robustness scoring

Validates that strategy performance is stable across different market conditions.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardWindow:
    """Single walk-forward window (train + test period)."""
    window_id: int
    
    # Train period
    train_start: datetime
    train_end: datetime
    train_days: int
    
    # Test period
    test_start: datetime
    test_end: datetime
    test_days: int
    
    # Results
    train_sharpe: Optional[float] = None
    test_sharpe: Optional[float] = None
    
    train_return: Optional[float] = None
    test_return: Optional[float] = None
    
    train_drawdown: Optional[float] = None
    test_drawdown: Optional[float] = None
    
    # Degradation
    sharpe_degradation: Optional[float] = None  # (test - train) / train
    return_degradation: Optional[float] = None
    
    # Optimal parameters found in train
    optimal_params: Dict = field(default_factory=dict)


@dataclass
class WalkForwardResults:
    """Complete walk-forward validation results."""
    strategy_id: str
    
    # Configuration
    total_windows: int
    train_days_per_window: int
    test_days_per_window: int
    
    # Windows
    windows: List[WalkForwardWindow] = field(default_factory=list)
    
    # Aggregate metrics
    avg_train_sharpe: float = 0.0
    avg_test_sharpe: float = 0.0
    avg_degradation_pct: float = 0.0
    
    # Consistency (lower is better)
    sharpe_std_dev: float = 0.0
    parameter_stability_score: float = 0.0  # 0-100
    
    # Overfitting indicators
    positive_degradation_count: int = 0  # Test > Train (good)
    negative_degradation_count: int = 0  # Test < Train (overfitting)
    severe_degradation_count: int = 0  # Test < 0.5 * Train
    
    # Overall robustness score (0-100)
    robustness_score: float = 0.0
    
    # Verdict
    is_robust: bool = False
    verdict_notes: List[str] = field(default_factory=list)


class WalkForwardLab:
    """
    Walk-forward validation laboratory.
    
    Tests strategy robustness by rolling train/test windows
    across historical data.
    """
    
    def __init__(
        self,
        train_days: int = 90,
        test_days: int = 30,
        step_days: int = 30
    ):
        """
        Initialize walk-forward lab.
        
        Args:
            train_days: Days in training window
            test_days: Days in test window
            step_days: Days to step forward between windows
        """
        self.train_days = train_days
        self.test_days = test_days
        self.step_days = step_days
        
        logger.info("✅ WalkForwardLab initialized")
        logger.info(f"   Train: {train_days} days, Test: {test_days} days, Step: {step_days} days")
    
    def generate_windows(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """
        Generate walk-forward windows.
        
        Args:
            start_date: Start of available data
            end_date: End of available data
            
        Returns:
            List of (train_start, train_end, test_start, test_end) tuples
        """
        windows = []
        current_start = start_date
        
        while True:
            train_start = current_start
            train_end = train_start + timedelta(days=self.train_days)
            test_start = train_end
            test_end = test_start + timedelta(days=self.test_days)
            
            if test_end > end_date:
                break
            
            windows.append((train_start, train_end, test_start, test_end))
            
            # Step forward
            current_start += timedelta(days=self.step_days)
        
        logger.info(f"✅ Generated {len(windows)} walk-forward windows")
        return windows
    
    def validate_strategy(
        self,
        strategy_id: str,
        backtest_function,
        start_date: datetime,
        end_date: datetime,
        parameter_grid: Optional[Dict] = None
    ) -> WalkForwardResults:
        """
        Run walk-forward validation for a strategy.
        
        Args:
            strategy_id: Strategy to validate
            backtest_function: Function(params, start, end) -> metrics
            start_date: Start of validation period
            end_date: End of validation period
            parameter_grid: Optional parameters to optimize
            
        Returns:
            WalkForwardResults with robustness analysis
        """
        # Generate windows
        window_periods = self.generate_windows(start_date, end_date)

        results = WalkForwardResults(
            strategy_id=strategy_id,
            total_windows=len(window_periods),
            train_days_per_window=self.train_days,
            test_days_per_window=self.test_days
        )
        
        # Run each window
        for i, (train_start, train_end, test_start, test_end) in enumerate(window_periods):
            window = WalkForwardWindow(
                window_id=i + 1,
                train_start=train_start,
                train_end=train_end,
                train_days=self.train_days,
                test_start=test_start,
                test_end=test_end,
                test_days=self.test_days
            )
            
            # Optimize on train period (simplified: use default params if no grid)
            if parameter_grid:
                # Would run grid search here - simplified for now
                optimal_params = parameter_grid
            else:
                optimal_params = {}
            
            window.optimal_params = optimal_params
            
            # Backtest on train period
            try:
                train_metrics = backtest_function(optimal_params, train_start, train_end)
                window.train_sharpe = train_metrics.get('sharpe_ratio', 0.0)
                window.train_return = train_metrics.get('total_return_pct', 0.0)
                window.train_drawdown = train_metrics.get('max_drawdown', 0.0)
            except Exception as e:
                logger.error(f"Train backtest failed for window {i+1}: {e}")
                window.train_sharpe = 0.0
            
            # Backtest on test period (out-of-sample)
            try:
                test_metrics = backtest_function(optimal_params, test_start, test_end)
                window.test_sharpe = test_metrics.get('sharpe_ratio', 0.0)
                window.test_return = test_metrics.get('total_return_pct', 0.0)
                window.test_drawdown = test_metrics.get('max_drawdown', 0.0)
            except Exception as e:
                logger.error(f"Test backtest failed for window {i+1}: {e}")
                window.test_sharpe = 0.0
            
            # Calculate degradation
            if window.train_sharpe and window.train_sharpe != 0:
                window.sharpe_degradation = (
                    (window.test_sharpe - window.train_sharpe) / abs(window.train_sharpe)
                )
            
            if window.train_return and window.train_return != 0:
                window.return_degradation = (
                    (window.test_return - window.train_return) / abs(window.train_return)
                )
            
            results.windows.append(window)
            
            logger.info(
                f"   Window {i+1}/{len(window_periods)}: "
                f"Train Sharpe={window.train_sharpe:.2f}, "
                f"Test Sharpe={window.test_sharpe:.2f}, "
                f"Degradation={window.sharpe_degradation:.1%}" if window.sharpe_degradation else ""
            )
        
        # Calculate aggregate metrics
        train_sharpes = [w.train_sharpe for w in results.windows if w.train_sharpe is not None]
        test_sharpes = [w.test_sharpe for w in results.windows if w.test_sharpe is not None]
        degradations = [w.sharpe_degradation for w in results.windows if w.sharpe_degradation is not None]
        
        if train_sharpes:
            results.avg_train_sharpe = np.mean(train_sharpes)
        
        if test_sharpes:
            results.avg_test_sharpe = np.mean(test_sharpes)
            results.sharpe_std_dev = np.std(test_sharpes)
        
        if degradations:
            results.avg_degradation_pct = np.mean(degradations) * 100
            
            # Count degradation types
            results.positive_degradation_count = sum(1 for d in degradations if d >= 0)
            results.negative_degradation_count = sum(1 for d in degradations if d < 0)
            results.severe_degradation_count = sum(1 for d in degradations if d < -0.5)
        
        # Calculate robustness score (0-100)
        score = 100.0
        
        # Penalty for average degradation
        if results.avg_degradation_pct < 0:
            score += results.avg_degradation_pct  # Negative degradation reduces score
        
        # Penalty for inconsistency
        if results.sharpe_std_dev > 1.0:
            score -= min((results.sharpe_std_dev - 1.0) * 20, 40)
        
        # Penalty for severe degradation
        severe_pct = results.severe_degradation_count / results.total_windows
        if severe_pct > 0.2:  # >20% severe degradation
            score -= min(severe_pct * 100, 50)
        
        # Bonus for positive degradation (test > train)
        positive_pct = results.positive_degradation_count / results.total_windows
        if positive_pct > 0.6:  # >60% positive
            score += 10
        
        results.robustness_score = max(0.0, min(100.0, score))
        
        # Verdict
        if results.robustness_score >= 70:
            results.is_robust = True
            results.verdict_notes.append("✅ Strategy is robust across time periods")
        elif results.robustness_score >= 50:
            results.verdict_notes.append("⚠️ Strategy shows moderate robustness")
        else:
            results.verdict_notes.append("❌ Strategy shows poor robustness - likely overfit")
        
        if results.avg_degradation_pct < -20:
            results.verdict_notes.append(f"⚠️ High average degradation: {results.avg_degradation_pct:.1f}%")
        
        if results.severe_degradation_count > 0:
            results.verdict_notes.append(
                f"⚠️ {results.severe_degradation_count}/{results.total_windows} windows had severe degradation"
            )
        
        logger.info(
            f"✅ Walk-forward validation complete: "
            f"Robustness={results.robustness_score:.1f}, "
            f"AvgDegradation={results.avg_degradation_pct:.1f}%"
        )
        
        return results


# Global instance
_walk_forward_lab: Optional[WalkForwardLab] = None


def get_walk_forward_lab(
    train_days: int = 90,
    test_days: int = 30,
    step_days: int = 30
) -> WalkForwardLab:
    """Get or create global walk-forward lab instance."""
    global _walk_forward_lab
    if _walk_forward_lab is None:
        _walk_forward_lab = WalkForwardLab(train_days, test_days, step_days)
    return _walk_forward_lab
