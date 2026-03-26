"""
Strategy Registry Service - Phase 6A
=====================================

Core registry for SmartFlow strategies and variants.

Provides:
- CRUD operations for strategies
- Seeding of built-in strategies
- Query interface
- Version management
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.database import SessionLocal
from app.models.strategy_registry_models import SmartFlowStrategy, StrategyCandidate
from app.services.strategy_registry.schemas import (
    StrategyStatus,
    StrategyType,
    StrategyCreate,
    StrategyResponse,
    CandidateStats,
)

logger = logging.getLogger(__name__)


# Built-in strategies definition
BUILT_IN_STRATEGIES = [
    {
        'strategy_id': 'unified_v1',
        'strategy_type': 'unified',
        'version': '1.0.0',
        'status': 'built_in',
        'parameters': {
            'score_threshold_buy': 5.0,
            'score_threshold_sell': -5.0,
            'enable_regime_detection': True,
            'min_confidence_score': 30.0
        },
        'notes': 'Default unified strategy with regime detection - fully routed and verified'
    },
    {
        'strategy_id': 'deterministic_v1',
        'strategy_type': 'deterministic',
        'version': '1.0.0',
        'status': 'built_in',
        'parameters': {
            'min_aligned_timeframes': 4,
            'require_higher_tf_agreement': True,
            'min_confidence_score': 75.0,
            'min_risk_reward': 2.0
        },
        'notes': 'True multi-timeframe deterministic indicators (>=4/5 TFs, 75% conf, 2:1 R:R) - fully routed and verified'
    },
    {
        'strategy_id': 'quick_v1',
        'strategy_type': 'quick',
        'version': '1.0.0',
        'status': 'built_in',
        'parameters': {
            'min_confidence_score': 60.0,
            'min_risk_reward': 1.5,
            'max_hold_hours': 2.0,
            'require_volume_confirmation': True
        },
        'notes': 'True 5m momentum quick mode (60% conf, 1.5:1 R:R, 2hr max hold) - fully routed and verified'
    },
    {
        'strategy_id': 'flow_v1',
        'strategy_type': 'flow',
        'version': '1.0.0',
        'status': 'built_in',
        'parameters': {
            'score_threshold_buy': 3.0,
            'score_threshold_sell': -3.0,
            'min_premium': 40000.0,
            'signal_cooldown_minutes': 30
        },
        'notes': 'Historical flow replay using real Polygon options trade data - fully routed structurally, pending real-data validation with actual Polygon API key'
    },
    {
        'strategy_id': 'ai_v1_proxy',
        'strategy_type': 'ai',
        'version': '1.0.0',
        'status': 'built_in',
        'parameters': {
            'min_confidence_score': 70.0,
            'require_mtf_alignment': True
        },
        'notes': 'AI-proxy using MTF analysis + AI thresholds (NOT true Claude analysis) - partially routed proxy implementation only'
    }
]


class StrategyRegistry:
    """
    SmartFlow Strategy Registry.

    Manages lifecycle of built-in strategies and user-generated variants.
    """

    # Configuration
    MAX_CANDIDATES_PER_BASE = 10  # MVP limit

    def __init__(self, db: Session = None):
        """Initialize registry with optional database session."""
        self.db = db or SessionLocal()
        logger.info("StrategyRegistry initialized")

    def seed_built_in_strategies(self) -> List[SmartFlowStrategy]:
        """
        Seed database with built-in SmartFlow strategies.

        Only creates strategies that don't already exist.

        Returns:
            List of created/existing built-in strategies
        """
        created = []

        for built_in in BUILT_IN_STRATEGIES:
            # Check if already exists
            existing = self.db.query(SmartFlowStrategy).filter(
                SmartFlowStrategy.strategy_id == built_in['strategy_id']
            ).first()

            if existing:
                logger.info(f"Built-in strategy already exists: {built_in['strategy_id']}")
                created.append(existing)
                continue

            # Create new built-in strategy
            strategy = SmartFlowStrategy(
                strategy_id=built_in['strategy_id'],
                strategy_type=built_in['strategy_type'],
                version=built_in['version'],
                status=built_in['status'],
                parameters=built_in['parameters'],
                parent_strategy_id=None,  # Built-ins have no parent
                parameter_changes=None,
                hypothesis=built_in.get('notes'),
                created_by='system'
            )

            self.db.add(strategy)
            created.append(strategy)
            logger.info(f"Seeded built-in strategy: {built_in['strategy_id']}")

        self.db.commit()

        logger.info(f"Seeded {len(created)} built-in strategies")
        return created

    def create_strategy(self, strategy: StrategyCreate) -> SmartFlowStrategy:
        """
        Create a new strategy (variant).

        For candidates, enforces max candidates limit.

        Args:
            strategy: Strategy creation request

        Returns:
            Created strategy

        Raises:
            ValueError: If candidate limit exceeded or strategy_id already exists
        """
        # Check if strategy_id already exists
        existing = self.db.query(SmartFlowStrategy).filter(
            SmartFlowStrategy.strategy_id == strategy.strategy_id
        ).first()

        if existing:
            raise ValueError(f"Strategy ID already exists: {strategy.strategy_id}")

        # For candidates, check limit
        if strategy.status == StrategyStatus.CANDIDATE and strategy.parent_strategy_id:
            stats = self.get_candidate_stats(strategy.parent_strategy_id)
            if not stats.can_create_more:
                raise ValueError(
                    f"Candidate limit reached for {strategy.parent_strategy_id}: "
                    f"{stats.active_candidates}/{stats.max_candidates}"
                )

        # Create strategy
        db_strategy = SmartFlowStrategy(
            strategy_id=strategy.strategy_id,
            strategy_type=strategy.strategy_type.value,
            version=strategy.version,
            status=strategy.status.value,
            parameters=strategy.parameters,
            parent_strategy_id=strategy.parent_strategy_id,
            parameter_changes=strategy.parameter_changes,
            hypothesis=strategy.hypothesis,
            created_by=strategy.created_by
        )

        self.db.add(db_strategy)

        # If candidate, also create candidate tracking entry
        if strategy.status == StrategyStatus.CANDIDATE:
            candidate = StrategyCandidate(
                strategy_id=strategy.strategy_id,
                parent_strategy_id=strategy.parent_strategy_id,
                created_by=strategy.created_by,
                is_active=True
            )
            self.db.add(candidate)

        self.db.commit()
        self.db.refresh(db_strategy)

        logger.info(f"Created strategy: {strategy.strategy_id} (status: {strategy.status.value})")

        return db_strategy

    def get_strategy(self, strategy_id: str) -> Optional[SmartFlowStrategy]:
        """Get strategy by ID."""
        return self.db.query(SmartFlowStrategy).filter(
            SmartFlowStrategy.strategy_id == strategy_id
        ).first()

    def list_strategies(
        self,
        status: Optional[List[str]] = None,
        strategy_type: Optional[str] = None,
        parent_strategy_id: Optional[str] = None
    ) -> List[SmartFlowStrategy]:
        """
        List strategies with optional filters.

        Args:
            status: Filter by status (list of statuses)
            strategy_type: Filter by type
            parent_strategy_id: Filter by parent (variants only)

        Returns:
            List of matching strategies
        """
        query = self.db.query(SmartFlowStrategy)

        if status:
            query = query.filter(SmartFlowStrategy.status.in_(status))

        if strategy_type:
            query = query.filter(SmartFlowStrategy.strategy_type == strategy_type)

        if parent_strategy_id:
            query = query.filter(SmartFlowStrategy.parent_strategy_id == parent_strategy_id)

        return query.order_by(SmartFlowStrategy.created_at.desc()).all()

    def get_candidate_stats(self, parent_strategy_id: str) -> CandidateStats:
        """
        Get candidate statistics for a base strategy.

        Args:
            parent_strategy_id: Base strategy ID

        Returns:
            Candidate statistics
        """
        active_count = self.db.query(StrategyCandidate).join(
            SmartFlowStrategy,
            StrategyCandidate.strategy_id == SmartFlowStrategy.strategy_id
        ).filter(
            and_(
                StrategyCandidate.parent_strategy_id == parent_strategy_id,
                StrategyCandidate.is_active == True,
                SmartFlowStrategy.status == StrategyStatus.CANDIDATE.value
            )
        ).count()

        return CandidateStats(
            parent_strategy_id=parent_strategy_id,
            active_candidates=active_count,
            max_candidates=self.MAX_CANDIDATES_PER_BASE,
            can_create_more=active_count < self.MAX_CANDIDATES_PER_BASE
        )

    def update_strategy_performance(
        self,
        strategy_id: str,
        sharpe_ratio: Optional[float] = None,
        win_rate: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        total_return_pct: Optional[float] = None,
        total_trades: Optional[int] = None,
        backtest_days: Optional[int] = None,
        latest_evaluation_id: Optional[int] = None,
        latest_comparison_id: Optional[str] = None
    ) -> SmartFlowStrategy:
        """
        Update strategy performance metrics from evaluation.

        Args:
            strategy_id: Strategy to update
            Performance metrics from backtest evaluation

        Returns:
            Updated strategy
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        if sharpe_ratio is not None:
            strategy.sharpe_ratio = sharpe_ratio
        if win_rate is not None:
            strategy.win_rate = win_rate
        if max_drawdown is not None:
            strategy.max_drawdown = max_drawdown
        if total_return_pct is not None:
            strategy.total_return_pct = total_return_pct
        if total_trades is not None:
            strategy.total_trades = total_trades
        if backtest_days is not None:
            strategy.backtest_days = backtest_days
        if latest_evaluation_id is not None:
            strategy.latest_evaluation_id = latest_evaluation_id
        if latest_comparison_id is not None:
            strategy.latest_comparison_id = latest_comparison_id

        strategy.evaluated_at = datetime.now()

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Updated performance for {strategy_id}: Sharpe={sharpe_ratio}, WinRate={win_rate}%")

        return strategy

    def promote_strategy(
        self,
        strategy_id: str,
        approved_by: str,
        approval_notes: str
    ) -> SmartFlowStrategy:
        """
        Promote candidate to approved_for_router status.

        Requires:
        - Strategy is currently a candidate
        - Human approval (approved_by + notes)

        Args:
            strategy_id: Strategy to promote
            approved_by: Admin who approves
            approval_notes: Reason for approval

        Returns:
            Promoted strategy

        Raises:
            ValueError: If strategy not eligible for promotion
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        if strategy.status != StrategyStatus.CANDIDATE.value:
            raise ValueError(f"Only candidates can be promoted (current status: {strategy.status})")

        if not strategy.evaluated_at:
            raise ValueError(f"Strategy must be evaluated before promotion: {strategy_id}")

        if not approved_by or not approval_notes:
            raise ValueError("Human approval required (approved_by + approval_notes)")

        # Promote
        strategy.status = StrategyStatus.APPROVED_FOR_ROUTER.value
        strategy.approved_at = datetime.now()
        strategy.approved_by = approved_by
        strategy.approval_notes = approval_notes

        # Deactivate candidate entry
        candidate = self.db.query(StrategyCandidate).filter(
            StrategyCandidate.strategy_id == strategy_id
        ).first()
        if candidate:
            candidate.is_active = False

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Promoted strategy {strategy_id} to approved_for_router (approved by: {approved_by})")

        return strategy

    def reject_strategy(
        self,
        strategy_id: str,
        rejected_by: str,
        rejection_notes: str
    ) -> SmartFlowStrategy:
        """
        Reject a candidate strategy.

        Args:
            strategy_id: Strategy to reject
            rejected_by: Admin who rejects
            rejection_notes: Reason for rejection

        Returns:
            Rejected strategy

        Raises:
            ValueError: If strategy not eligible for rejection
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        if strategy.status != StrategyStatus.CANDIDATE.value:
            raise ValueError(f"Only candidates can be rejected (current status: {strategy.status})")

        if not rejected_by or not rejection_notes:
            raise ValueError("Rejection requires rejected_by + rejection_notes")

        # Reject
        strategy.status = StrategyStatus.REJECTED.value
        strategy.rejected_at = datetime.now()
        strategy.rejected_by = rejected_by
        strategy.rejection_notes = rejection_notes

        # Deactivate candidate entry
        candidate = self.db.query(StrategyCandidate).filter(
            StrategyCandidate.strategy_id == strategy_id
        ).first()
        if candidate:
            candidate.is_active = False

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Rejected strategy {strategy_id} (rejected by: {rejected_by})")

        return strategy

    def retire_strategy(
        self,
        strategy_id: str,
        retired_by: str,
        retirement_reason: str
    ) -> SmartFlowStrategy:
        """
        Retire an approved strategy.

        Args:
            strategy_id: Strategy to retire
            retired_by: Admin who retires
            retirement_reason: Reason for retirement

        Returns:
            Retired strategy

        Raises:
            ValueError: If strategy not eligible for retirement
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        if strategy.status not in [StrategyStatus.APPROVED_FOR_ROUTER.value]:
            raise ValueError(f"Only approved strategies can be retired (current status: {strategy.status})")

        if strategy.status == StrategyStatus.BUILT_IN.value:
            raise ValueError("Built-in strategies cannot be retired")

        # Retire
        strategy.status = StrategyStatus.RETIRED.value
        strategy.retired_at = datetime.now()
        strategy.retired_by = retired_by
        strategy.retirement_reason = retirement_reason

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Retired strategy {strategy_id} (retired by: {retired_by})")

        return strategy

    # ===================================================================
    # Phase 7: Forward-Test Gate Workflow
    # ===================================================================

    def approve_for_forward_test(
        self,
        strategy_id: str,
        approved_by: str,
        approval_notes: str
    ) -> SmartFlowStrategy:
        """
        Approve candidate for forward testing (after backtest evaluation).

        Phase 7: First gate - backtest passed, ready for forward test.

        Args:
            strategy_id: Strategy to approve
            approved_by: Admin who approves
            approval_notes: Reason for approval

        Returns:
            Updated strategy

        Raises:
            ValueError: If strategy not eligible
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        if strategy.status != StrategyStatus.CANDIDATE.value:
            raise ValueError(f"Only candidates can be approved for forward test (current status: {strategy.status})")

        if not strategy.evaluated_at:
            raise ValueError(f"Strategy must be evaluated before approval: {strategy_id}")

        if not approved_by or not approval_notes:
            raise ValueError("Approval requires approved_by + approval_notes")

        # Approve for forward test
        strategy.status = StrategyStatus.APPROVED_FOR_FORWARD_TEST.value
        strategy.approved_for_forward_test_at = datetime.now()
        strategy.approved_for_forward_test_by = approved_by
        strategy.approval_notes = approval_notes  # Reuse existing field

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Approved {strategy_id} for forward test (by: {approved_by})")

        return strategy

    def start_forward_testing(
        self,
        strategy_id: str,
        session_id: str
    ) -> SmartFlowStrategy:
        """
        Mark strategy as forward_testing and link to session.

        Args:
            strategy_id: Strategy being tested
            session_id: Forward-test session ID

        Returns:
            Updated strategy

        Raises:
            ValueError: If strategy not eligible
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        if strategy.status != StrategyStatus.APPROVED_FOR_FORWARD_TEST.value:
            raise ValueError(
                f"Only approved_for_forward_test strategies can start testing "
                f"(current status: {strategy.status})"
            )

        # Mark as forward_testing
        strategy.status = StrategyStatus.FORWARD_TESTING.value
        strategy.forward_testing_started_at = datetime.now()
        strategy.latest_forward_test_session_id = session_id

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Started forward testing for {strategy_id} (session: {session_id})")

        return strategy

    def approve_for_router_after_gate(
        self,
        strategy_id: str,
        approved_by: str,
        gate_decision: 'ForwardTestGateDecision'
    ) -> SmartFlowStrategy:
        """
        Approve strategy for router after passing forward-test gate.

        Phase 7: Final gate - forward test passed, router-eligible.

        Args:
            strategy_id: Strategy to approve
            approved_by: Admin who approves
            gate_decision: Gate decision with justification

        Returns:
            Updated strategy

        Raises:
            ValueError: If strategy not eligible or gate failed
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        if strategy.status != StrategyStatus.FORWARD_TESTING.value:
            raise ValueError(
                f"Only forward_testing strategies can be approved for router "
                f"(current status: {strategy.status})"
            )

        if not gate_decision.passed:
            raise ValueError(
                f"Cannot approve strategy that failed gate: {gate_decision.decision_reason}"
            )

        # Approve for router
        strategy.status = StrategyStatus.APPROVED_FOR_ROUTER.value
        strategy.forward_test_gate_passed_at = datetime.now()
        strategy.forward_test_gate_passed_by = approved_by
        strategy.approved_for_router_at = datetime.now()
        strategy.approved_for_router_by = approved_by

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Approved {strategy_id} for router (gate passed by: {approved_by})")

        return strategy

    def fail_forward_test(
        self,
        strategy_id: str,
        failed_by: str,
        gate_decision: 'ForwardTestGateDecision'
    ) -> SmartFlowStrategy:
        """
        Fail strategy at forward-test gate.

        Args:
            strategy_id: Strategy to fail
            failed_by: Admin who fails
            gate_decision: Gate decision with failure reason

        Returns:
            Updated strategy

        Raises:
            ValueError: If strategy not eligible
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        if strategy.status != StrategyStatus.FORWARD_TESTING.value:
            raise ValueError(
                f"Only forward_testing strategies can fail gate "
                f"(current status: {strategy.status})"
            )

        # Mark as rejected (failed forward test)
        strategy.status = StrategyStatus.REJECTED.value
        strategy.forward_test_gate_failed_at = datetime.now()
        strategy.forward_test_gate_failed_by = failed_by
        strategy.forward_test_gate_failure_reason = gate_decision.decision_reason
        strategy.rejected_at = datetime.now()
        strategy.rejected_by = failed_by
        strategy.rejection_notes = f"Failed forward-test gate: {gate_decision.decision_reason}"

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Failed forward test for {strategy_id} (by: {failed_by})")

        return strategy

    def get_router_eligible_strategies(self) -> List[SmartFlowStrategy]:
        """
        Get strategies eligible for router selection.

        Phase 7: Only built_in, approved_for_router, and active are eligible.
        Phase 8D: Also excludes paused strategies and unhealthy strategies.

        Returns:
            List of router-eligible strategies
        """
        eligible_statuses = [
            StrategyStatus.BUILT_IN.value,
            StrategyStatus.APPROVED_FOR_ROUTER.value,
            StrategyStatus.ACTIVE.value,
        ]

        # Phase 8D: Add operational filters
        strategies = self.db.query(SmartFlowStrategy).filter(
            SmartFlowStrategy.status.in_(eligible_statuses),
            SmartFlowStrategy.is_paused == False,  # Exclude paused
            SmartFlowStrategy.health_status.in_(["healthy", "degraded"])  # Exclude unhealthy
        ).order_by(SmartFlowStrategy.strategy_type, SmartFlowStrategy.created_at).all()

        logger.debug(f"Found {len(strategies)} router-eligible strategies (excluding paused/unhealthy)")

        return strategies

    def mark_strategy_active(
        self,
        strategy_id: str
    ) -> SmartFlowStrategy:
        """
        Mark strategy as active (router has selected it).

        Args:
            strategy_id: Strategy to mark active

        Returns:
            Updated strategy

        Raises:
            ValueError: If strategy not router-eligible
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        if strategy.status not in [
            StrategyStatus.BUILT_IN.value,
            StrategyStatus.APPROVED_FOR_ROUTER.value,
            StrategyStatus.ACTIVE.value
        ]:
            raise ValueError(
                f"Only router-eligible strategies can be marked active "
                f"(current status: {strategy.status})"
            )

        if strategy.status != StrategyStatus.ACTIVE.value:
            strategy.status = StrategyStatus.ACTIVE.value
            if not strategy.active_at:
                strategy.active_at = datetime.now()

            self.db.commit()
            self.db.refresh(strategy)

            logger.info(f"Marked {strategy_id} as active")

        return strategy

    # Phase 8D: Operational Hardening Methods
    # =========================================

    def pause_strategy(
        self,
        strategy_id: str,
        paused_by: str,
        pause_reason: str
    ) -> SmartFlowStrategy:
        """
        Pause a strategy (excludes from router without retiring).

        Phase 8D: Operational control for runtime management.

        Args:
            strategy_id: Strategy to pause
            paused_by: Admin who paused
            pause_reason: Why strategy is being paused

        Returns:
            Updated strategy

        Raises:
            ValueError: If strategy not found
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        strategy.is_paused = True
        strategy.paused_at = datetime.now()
        strategy.paused_by = paused_by
        strategy.pause_reason = pause_reason

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Strategy paused: {strategy_id} by {paused_by} - {pause_reason}")
        return strategy

    def resume_strategy(
        self,
        strategy_id: str,
        resumed_by: str
    ) -> SmartFlowStrategy:
        """
        Resume a paused strategy.

        Phase 8D: Operational control for runtime management.

        Args:
            strategy_id: Strategy to resume
            resumed_by: Admin who resumed

        Returns:
            Updated strategy

        Raises:
            ValueError: If strategy not found
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        strategy.is_paused = False
        strategy.paused_at = None
        strategy.paused_by = None
        strategy.pause_reason = None

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Strategy resumed: {strategy_id} by {resumed_by}")
        return strategy

    def update_health_status(
        self,
        strategy_id: str,
        health_status: str,
        health_notes: str = None
    ) -> SmartFlowStrategy:
        """
        Update strategy health status.

        Phase 8D: Future hook for monitoring system.

        Args:
            strategy_id: Strategy to update
            health_status: "healthy", "degraded", "unhealthy", "unknown"
            health_notes: Optional notes about health status

        Returns:
            Updated strategy

        Raises:
            ValueError: If strategy not found or invalid health_status
        """
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy not found: {strategy_id}")

        valid_statuses = ["healthy", "degraded", "unhealthy", "unknown"]
        if health_status not in valid_statuses:
            raise ValueError(f"Invalid health_status: {health_status}. Must be one of: {valid_statuses}")

        strategy.health_status = health_status
        strategy.health_checked_at = datetime.now()
        strategy.health_notes = health_notes

        self.db.commit()
        self.db.refresh(strategy)

        logger.info(f"Strategy health updated: {strategy_id} → {health_status}")
        return strategy


# Global instance
_registry: Optional[StrategyRegistry] = None


def get_strategy_registry() -> StrategyRegistry:
    """Get or create global strategy registry."""
    global _registry
    if _registry is None:
        _registry = StrategyRegistry()
    return _registry
