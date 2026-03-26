"""
Strategy Evaluator Service - Phase 6C
======================================

Backtest-based evaluation of candidate strategies with:
- Automated backtest execution
- Criteria-based scoring (Sharpe, win rate, max DD, etc.)
- Evaluation results tracking
- Approval/rejection recommendations
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.strategy_registry.registry import StrategyRegistry, get_strategy_registry
from app.services.strategy_registry.schemas import (
    EvaluationRequest,
    EvaluationResponse,
    EvaluationCriteriaResult,
)
from app.models.strategy_registry_models import StrategyEvaluation
from app.services.smartflow_backtest import SmartFlowBacktester
from app.services.backtesting.comparison_runner import ComparisonRunner

logger = logging.getLogger(__name__)


class StrategyEvaluator:
    """
    Evaluates strategy candidates through backtest-based criteria.

    Phase 6C MVP Criteria:
    - Sharpe Ratio >= 1.0
    - Win Rate >= 50%
    - Max Drawdown <= 20%
    - Total Trades >= 20 (statistical significance)
    - Net Profit > 0

    All criteria must pass for APPROVE recommendation.
    """

    # Evaluation criteria thresholds
    MIN_SHARPE_RATIO = 1.0
    MIN_WIN_RATE = 50.0  # percent
    MAX_DRAWDOWN_LIMIT = 20.0  # percent (absolute value)
    MIN_TOTAL_TRADES = 20
    MIN_NET_PROFIT = 0.0

    def __init__(self, registry: Optional[StrategyRegistry] = None):
        """Initialize evaluator with registry."""
        self.registry = registry or get_strategy_registry()
        logger.info("StrategyEvaluator initialized")

    async def evaluate_strategy(
        self,
        request: EvaluationRequest
    ) -> EvaluationResponse:
        """
        Evaluate a strategy through backtest and criteria checks.

        Args:
            request: Evaluation request

        Returns:
            Evaluation response with recommendation

        Raises:
            ValueError: If strategy not found or not eligible for evaluation
        """
        # Get strategy
        strategy = self.registry.get_strategy(request.strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {request.strategy_id}")

        logger.info(
            f"Evaluating strategy {request.strategy_id} "
            f"(ticker={request.ticker}, days={request.backtest_days})"
        )

        # Run backtest
        backtest_result = await self._run_backtest(
            strategy_id=request.strategy_id,
            strategy_type=strategy.strategy_type,
            parameters=strategy.parameters,
            ticker=request.ticker,
            backtest_days=request.backtest_days
        )

        # Extract performance metrics
        metrics = backtest_result['metrics']
        comparison_id = backtest_result['comparison_id']

        # Evaluate criteria
        criteria_results = self._evaluate_criteria(metrics)
        passed = all(cr.passed for cr in criteria_results)
        recommendation = "APPROVE" if passed else "REJECT"

        # Helper to convert numpy types to Python types
        def to_python_type(value):
            """Convert numpy types to Python native types for DB storage."""
            if value is None:
                return None
            if hasattr(value, 'item'):  # numpy scalar
                return value.item()
            return value

        # Create evaluation record
        evaluation = StrategyEvaluation(
            strategy_id=request.strategy_id,
            comparison_id=comparison_id,
            ticker=request.ticker,
            backtest_days=request.backtest_days,
            start_date=metrics.get('start_date'),
            end_date=metrics.get('end_date'),
            sharpe_ratio=to_python_type(metrics.get('sharpe_ratio')),
            win_rate=to_python_type(metrics.get('win_rate')),
            max_drawdown=to_python_type(metrics.get('max_drawdown')),
            total_return_pct=to_python_type(metrics.get('total_return_pct')),
            total_trades=to_python_type(metrics.get('total_trades')),
            net_profit=to_python_type(metrics.get('net_profit')),
            profit_factor=to_python_type(metrics.get('profit_factor')),
            criteria_checked=[cr.criterion for cr in criteria_results],
            criteria_results=[cr.dict() for cr in criteria_results],
            passed=passed,
            recommendation=recommendation,
            evaluated_by=request.evaluated_by,
            notes=request.notes
        )

        self.registry.db.add(evaluation)
        self.registry.db.commit()
        self.registry.db.refresh(evaluation)

        # Update strategy performance
        self.registry.update_strategy_performance(
            strategy_id=request.strategy_id,
            sharpe_ratio=to_python_type(metrics.get('sharpe_ratio')),
            win_rate=to_python_type(metrics.get('win_rate')),
            max_drawdown=to_python_type(metrics.get('max_drawdown')),
            total_return_pct=to_python_type(metrics.get('total_return_pct')),
            total_trades=to_python_type(metrics.get('total_trades')),
            backtest_days=request.backtest_days,
            latest_evaluation_id=evaluation.id,
            latest_comparison_id=comparison_id
        )

        logger.info(
            f"Evaluation complete for {request.strategy_id}: "
            f"{recommendation} (passed={passed}, Sharpe={metrics.get('sharpe_ratio'):.2f}, "
            f"WinRate={metrics.get('win_rate'):.1f}%)"
        )

        # Return response
        return EvaluationResponse(
            evaluation_id=evaluation.id,
            strategy_id=evaluation.strategy_id,
            comparison_id=evaluation.comparison_id,
            ticker=evaluation.ticker,
            backtest_days=evaluation.backtest_days,
            sharpe_ratio=evaluation.sharpe_ratio,
            win_rate=evaluation.win_rate,
            max_drawdown=evaluation.max_drawdown,
            total_return_pct=evaluation.total_return_pct,
            total_trades=evaluation.total_trades,
            net_profit=evaluation.net_profit,
            criteria_results=criteria_results,
            passed=passed,
            recommendation=recommendation,
            evaluated_at=evaluation.evaluated_at,
            notes=evaluation.notes
        )

    async def _run_backtest(
        self,
        strategy_id: str,
        strategy_type: str,
        parameters: Dict[str, Any],
        ticker: str,
        backtest_days: int
    ) -> Dict[str, Any]:
        """
        Run backtest for a strategy.

        Args:
            strategy_id: Strategy ID
            strategy_type: Strategy type (unified, deterministic, quick, flow, ai)
            parameters: Strategy parameters
            ticker: Ticker to backtest
            backtest_days: Days to backtest

        Returns:
            {
                'metrics': BacktestMetrics dict,
                'comparison_id': str (from comparison_store)
            }
        """
        # Use ComparisonRunner to execute backtest with proper routing
        runner = ComparisonRunner()

        # Run single-engine backtest
        # TODO: Add custom_params support to override variant params
        result = await runner.run_engine_comparison(
            ticker=ticker,
            days=backtest_days,
            engines=[strategy_type],
            config_overrides=None  # Would pass variant parameters here
        )

        # Extract metrics for this engine
        engine_metrics = result.engine_results[strategy_type]

        return {
            'metrics': engine_metrics,
            'comparison_id': result.comparison_id
        }

    def _evaluate_criteria(self, metrics: Dict[str, Any]) -> List[EvaluationCriteriaResult]:
        """
        Evaluate performance against criteria.

        Args:
            metrics: Backtest metrics

        Returns:
            List of criteria results
        """
        results = []

        # Criterion 1: Sharpe Ratio >= 1.0
        sharpe = metrics.get('sharpe_ratio', 0.0)
        results.append(EvaluationCriteriaResult(
            criterion="Sharpe Ratio >= 1.0",
            passed=sharpe >= self.MIN_SHARPE_RATIO,
            value=sharpe,
            threshold=self.MIN_SHARPE_RATIO,
            details=f"Sharpe Ratio: {sharpe:.2f}"
        ))

        # Criterion 2: Win Rate >= 50%
        win_rate = metrics.get('win_rate', 0.0)
        results.append(EvaluationCriteriaResult(
            criterion="Win Rate >= 50%",
            passed=win_rate >= self.MIN_WIN_RATE,
            value=win_rate,
            threshold=self.MIN_WIN_RATE,
            details=f"Win Rate: {win_rate:.1f}%"
        ))

        # Criterion 3: Max Drawdown <= 20%
        max_dd = abs(metrics.get('max_drawdown', 0.0))  # Ensure positive for comparison
        results.append(EvaluationCriteriaResult(
            criterion="Max Drawdown <= 20%",
            passed=max_dd <= self.MAX_DRAWDOWN_LIMIT,
            value=max_dd,
            threshold=self.MAX_DRAWDOWN_LIMIT,
            details=f"Max Drawdown: {max_dd:.1f}%"
        ))

        # Criterion 4: Total Trades >= 20
        total_trades = metrics.get('total_trades', 0)
        results.append(EvaluationCriteriaResult(
            criterion="Total Trades >= 20",
            passed=total_trades >= self.MIN_TOTAL_TRADES,
            value=float(total_trades),
            threshold=float(self.MIN_TOTAL_TRADES),
            details=f"Total Trades: {total_trades}"
        ))

        # Criterion 5: Net Profit > 0
        net_profit = metrics.get('net_profit', 0.0)
        results.append(EvaluationCriteriaResult(
            criterion="Net Profit > 0",
            passed=net_profit > self.MIN_NET_PROFIT,
            value=net_profit,
            threshold=self.MIN_NET_PROFIT,
            details=f"Net Profit: ${net_profit:.2f}"
        ))

        return results


# Global instance
_evaluator: Optional[StrategyEvaluator] = None


def get_strategy_evaluator() -> StrategyEvaluator:
    """Get or create global strategy evaluator."""
    global _evaluator
    if _evaluator is None:
        _evaluator = StrategyEvaluator()
    return _evaluator
