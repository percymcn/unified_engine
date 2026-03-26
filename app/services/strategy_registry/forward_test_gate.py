"""
Forward-Test Gate Service - Phase 7
====================================

Safety bridge between backtest-approved and router-eligible strategies.

Gate Criteria:
- Minimum 30 trades for statistical significance
- Win rate >= 45%
- Max drawdown <= 25%
- Profit factor >= 1.2
- No catastrophic degradation vs backtest profile
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import SessionLocal
from app.models.forward_test_models import ForwardTestSession
from app.models.strategy_registry_models import SmartFlowStrategy

logger = logging.getLogger(__name__)


class GateCriteriaResult(BaseModel):
    """Result for a single gate criterion."""
    criterion: str
    passed: bool
    value: Optional[float] = None
    threshold: Optional[float] = None
    details: str


class ForwardTestGateDecision(BaseModel):
    """Forward-test gate decision with full justification."""
    session_id: str
    strategy_id: str
    passed: bool
    recommendation: str  # 'APPROVE_FOR_ROUTER' or 'FAIL_FORWARD_TEST'
    criteria_results: List[GateCriteriaResult]
    decision_reason: str
    degradation_analysis: Optional[Dict[str, Any]] = None
    evaluated_at: datetime
    evaluated_by: Optional[str] = None


class ForwardTestGate:
    """
    Forward-test gate evaluator.

    Phase 7: Safety layer ensuring strategies prove themselves in forward testing
    before becoming router-eligible.
    """

    # Gate Criteria Thresholds
    MIN_TRADES = 30
    MIN_WIN_RATE = 45.0  # percent
    MAX_DRAWDOWN_LIMIT = 25.0  # percent (absolute value)
    MIN_PROFIT_FACTOR = 1.2
    MAX_BACKTEST_DEGRADATION = 15.0  # percent (win rate drop)

    def __init__(self, db: Optional[Session] = None):
        """Initialize gate with database session."""
        self.db = db or SessionLocal()
        logger.info("ForwardTestGate initialized")

    def evaluate_gate(
        self,
        session_id: str,
        strategy_id: str,
        evaluated_by: Optional[str] = None
    ) -> ForwardTestGateDecision:
        """
        Evaluate forward-test session against gate criteria.

        Args:
            session_id: Forward-test session ID
            strategy_id: Strategy being tested
            evaluated_by: Admin who triggered evaluation

        Returns:
            Gate decision with full justification

        Raises:
            ValueError: If session or strategy not found
        """
        # Get forward-test session
        session = self.db.query(ForwardTestSession).filter(
            ForwardTestSession.session_id == session_id
        ).first()

        if not session:
            raise ValueError(f"Forward-test session not found: {session_id}")

        # Get strategy
        strategy = self.db.query(SmartFlowStrategy).filter(
            SmartFlowStrategy.strategy_id == strategy_id
        ).first()

        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        logger.info(
            f"Evaluating forward-test gate for {strategy_id} "
            f"(session: {session_id}, trades: {session.total_trades})"
        )

        # Evaluate criteria
        criteria_results = self._evaluate_criteria(session, strategy)
        passed = all(cr.passed for cr in criteria_results)

        # Build decision reason
        if passed:
            recommendation = "APPROVE_FOR_ROUTER"
            decision_reason = self._build_approval_reason(criteria_results, session)
        else:
            recommendation = "FAIL_FORWARD_TEST"
            decision_reason = self._build_failure_reason(criteria_results, session)

        # Degradation analysis
        degradation_analysis = self._analyze_degradation(strategy, session) if strategy.win_rate else None

        decision = ForwardTestGateDecision(
            session_id=session_id,
            strategy_id=strategy_id,
            passed=passed,
            recommendation=recommendation,
            criteria_results=criteria_results,
            decision_reason=decision_reason,
            degradation_analysis=degradation_analysis,
            evaluated_at=datetime.now(),
            evaluated_by=evaluated_by
        )

        logger.info(
            f"Gate decision for {strategy_id}: {recommendation} "
            f"(passed={passed}, criteria={sum(1 for cr in criteria_results if cr.passed)}/{len(criteria_results)})"
        )

        return decision

    def _evaluate_criteria(
        self,
        session: ForwardTestSession,
        strategy: SmartFlowStrategy
    ) -> List[GateCriteriaResult]:
        """
        Evaluate all gate criteria.

        Args:
            session: Forward-test session
            strategy: Strategy being evaluated

        Returns:
            List of criterion results
        """
        results = []

        # Criterion 1: Minimum trades >= 30
        results.append(GateCriteriaResult(
            criterion="Minimum Trades >= 30",
            passed=session.total_trades >= self.MIN_TRADES,
            value=float(session.total_trades),
            threshold=float(self.MIN_TRADES),
            details=f"Total Trades: {session.total_trades}"
        ))

        # Criterion 2: Win rate >= 45%
        results.append(GateCriteriaResult(
            criterion="Win Rate >= 45%",
            passed=session.win_rate >= self.MIN_WIN_RATE,
            value=session.win_rate,
            threshold=self.MIN_WIN_RATE,
            details=f"Win Rate: {session.win_rate:.1f}%"
        ))

        # Criterion 3: Max drawdown <= 25%
        max_dd = abs(session.max_drawdown) if session.max_drawdown else 0.0
        results.append(GateCriteriaResult(
            criterion="Max Drawdown <= 25%",
            passed=max_dd <= self.MAX_DRAWDOWN_LIMIT,
            value=max_dd,
            threshold=self.MAX_DRAWDOWN_LIMIT,
            details=f"Max Drawdown: {max_dd:.1f}%"
        ))

        # Criterion 4: Profit factor >= 1.2
        results.append(GateCriteriaResult(
            criterion="Profit Factor >= 1.2",
            passed=session.profit_factor >= self.MIN_PROFIT_FACTOR,
            value=session.profit_factor,
            threshold=self.MIN_PROFIT_FACTOR,
            details=f"Profit Factor: {session.profit_factor:.2f}"
        ))

        # Criterion 5: No catastrophic degradation vs backtest
        if strategy.win_rate is not None:
            degradation = strategy.win_rate - session.win_rate
            passed_degradation = degradation <= self.MAX_BACKTEST_DEGRADATION
            results.append(GateCriteriaResult(
                criterion="No Catastrophic Degradation",
                passed=passed_degradation,
                value=degradation,
                threshold=self.MAX_BACKTEST_DEGRADATION,
                details=f"Win Rate Drop: {degradation:.1f}% (backtest: {strategy.win_rate:.1f}%, forward: {session.win_rate:.1f}%)"
            ))
        else:
            # No backtest data, consider passed
            results.append(GateCriteriaResult(
                criterion="No Catastrophic Degradation",
                passed=True,
                value=None,
                threshold=self.MAX_BACKTEST_DEGRADATION,
                details="No backtest profile available for comparison"
            ))

        return results

    def _build_approval_reason(
        self,
        criteria_results: List[GateCriteriaResult],
        session: ForwardTestSession
    ) -> str:
        """Build human-readable approval reason."""
        return (
            f"Forward-test gate PASSED. "
            f"Completed {session.total_trades} trades with "
            f"{session.win_rate:.1f}% win rate, "
            f"{session.profit_factor:.2f} profit factor, and "
            f"{abs(session.max_drawdown):.1f}% max drawdown. "
            f"All {len(criteria_results)} criteria met. "
            f"Strategy is approved for router selection."
        )

    def _build_failure_reason(
        self,
        criteria_results: List[GateCriteriaResult],
        session: ForwardTestSession
    ) -> str:
        """Build human-readable failure reason."""
        failed_criteria = [cr for cr in criteria_results if not cr.passed]
        failed_names = ", ".join(cr.criterion for cr in failed_criteria)

        return (
            f"Forward-test gate FAILED. "
            f"Completed {session.total_trades} trades but failed {len(failed_criteria)} criteria: "
            f"{failed_names}. "
            f"Strategy requires improvement before router eligibility."
        )

    def _analyze_degradation(
        self,
        strategy: SmartFlowStrategy,
        session: ForwardTestSession
    ) -> Dict[str, Any]:
        """
        Analyze performance degradation from backtest to forward test.

        Args:
            strategy: Strategy with backtest metrics
            session: Forward-test session

        Returns:
            Degradation analysis
        """
        return {
            "backtest_win_rate": strategy.win_rate,
            "forward_test_win_rate": session.win_rate,
            "win_rate_degradation": strategy.win_rate - session.win_rate if strategy.win_rate else None,
            "backtest_sharpe": strategy.sharpe_ratio,
            "backtest_max_dd": strategy.max_drawdown,
            "forward_test_max_dd": session.max_drawdown,
            "backtest_total_trades": strategy.total_trades,
            "forward_test_total_trades": session.total_trades,
        }


# Global instance
_forward_test_gate: Optional[ForwardTestGate] = None


def get_forward_test_gate() -> ForwardTestGate:
    """Get or create global forward-test gate."""
    global _forward_test_gate
    if _forward_test_gate is None:
        _forward_test_gate = ForwardTestGate()
    return _forward_test_gate
