"""
SmartFlow Strategy Allocator - Phase 9
=======================================

Portfolio allocator that scores strategies and computes allocation weights.

Sits between router decision and signal execution, producing:
- Strategy scores based on performance metrics
- Allocation weights (sum to 1.0)
- Health/safety throttles
- AI feature adjustments
- Full traceability

Design:
- Transparent scoring (no black boxes)
- Each score component is explainable
- Metadata-first integration (doesn't modify position sizing yet)
- Preserves existing webhook execution path
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Session

from app.models.strategy_registry_models import SmartFlowStrategy, StrategyHealthSnapshot, PortfolioRiskSnapshot
from app.services.strategy_registry.health import get_health_monitor, should_exclude_from_allocation
from app.services.strategy_registry.portfolio_risk import get_portfolio_risk_engine, PortfolioRiskSnapshot as RiskSnapshot

logger = logging.getLogger(__name__)


class ExclusionReason(Enum):
    """Reasons a strategy might be excluded from allocation"""
    PAUSED = "paused"
    UNHEALTHY = "unhealthy"
    NOT_APPROVED = "not_approved"
    NO_FORWARD_TEST = "no_forward_test"
    POOR_METRICS = "poor_metrics"
    ZERO_SCORE = "zero_score"


@dataclass
class StrategyScore:
    """
    Detailed scoring breakdown for a strategy.

    Every component is explainable and traceable.
    """
    strategy_id: str
    engine_type: str

    # Raw metrics from strategy registry
    sharpe_ratio: Optional[float] = None
    win_rate: Optional[float] = None
    max_drawdown: Optional[float] = None
    total_return_pct: Optional[float] = None
    profit_factor: Optional[float] = None

    # Health & status
    health_status: str = "unknown"
    is_paused: bool = False
    forward_test_passed: bool = False

    # Score components (each 0-1)
    sharpe_component: float = 0.0
    drawdown_component: float = 0.0
    profit_factor_component: float = 0.0
    forward_test_bonus: float = 0.0
    health_multiplier: float = 1.0
    ai_adjustment: float = 0.0

    # Final computed score
    raw_score: float = 0.0
    adjusted_score: float = 0.0

    # Allocation
    allocation_weight: float = 0.0

    # Exclusion
    excluded: bool = False
    exclusion_reason: Optional[ExclusionReason] = None

    # Metadata
    computed_at: datetime = field(default_factory=datetime.now)
    notes: str = ""


@dataclass
class AllocationDecision:
    """
    Complete allocation decision for a signal.

    Contains:
    - All strategy scores
    - Final weights
    - Exclusions
    - Traceability metadata
    """
    selected_strategies: List[StrategyScore] = field(default_factory=list)
    excluded_strategies: List[StrategyScore] = field(default_factory=list)
    total_weight: float = 0.0
    current_regime: Optional[str] = None
    regime_confidence: Optional[float] = None
    ai_features_used: bool = False
    decision_source: str = "allocator"
    computed_at: datetime = field(default_factory=datetime.now)
    notes: str = ""


class StrategyAllocator:
    """
    Portfolio allocator for SmartFlow strategies.

    Scores eligible strategies and computes allocation weights based on:
    - Performance metrics (Sharpe, drawdown, profit factor)
    - Forward-test results
    - Health status
    - AI feature adjustments (optional)

    Phase 9: Metadata-first integration
    - Computes weights but doesn't modify position sizing yet
    - Attaches allocation metadata to signals
    - Preserves existing webhook execution
    """

    def __init__(self, db: Session):
        self.db = db

        # Scoring weights (sum to 1.0)
        self.sharpe_weight = 0.35
        self.drawdown_weight = 0.25
        self.profit_factor_weight = 0.20
        self.forward_test_weight = 0.20

        # Health multipliers
        self.health_multipliers = {
            "healthy": 1.0,
            "degraded": 0.7,
            "unhealthy": 0.3,
            "unknown": 0.8
        }

        # Minimum thresholds
        self.min_sharpe = 0.5
        self.max_drawdown_threshold = 30.0  # Exclude if > 30%
        self.min_win_rate = 0.30  # Exclude if < 30%

        logger.info("✅ StrategyAllocator initialized")

    def get_eligible_strategies(
        self,
        strategy_ids: Optional[List[str]] = None,
        engine_type: Optional[str] = None
    ) -> List[SmartFlowStrategy]:
        """
        Get eligible strategies from registry.

        Args:
            strategy_ids: Optional list of specific strategy IDs to score
            engine_type: Optional engine type filter

        Returns:
            List of SmartFlowStrategy objects that are:
            - approved_for_router or built_in status
            - not paused
            - healthy or degraded (excludes unhealthy)
        """
        query = self.db.query(SmartFlowStrategy)

        # Filter by status
        query = query.filter(
            SmartFlowStrategy.status.in_(['built_in', 'approved_for_router'])
        )

        # Filter by specific IDs if provided
        if strategy_ids:
            query = query.filter(SmartFlowStrategy.strategy_id.in_(strategy_ids))

        # Filter by engine type if provided
        if engine_type:
            query = query.filter(SmartFlowStrategy.strategy_type == engine_type)

        # Exclude paused
        query = query.filter(SmartFlowStrategy.is_paused == False)

        # Phase 10: Exclude critical/unhealthy (but allow degraded)
        # Note: Strategies with 'critical' health_status are auto-paused,
        # so they're already excluded above. This is redundant but explicit.
        query = query.filter(
            SmartFlowStrategy.health_status.in_(['healthy', 'degraded', 'unknown'])
        )

        strategies = query.all()

        logger.info(
            f"📊 Allocator: Found {len(strategies)} eligible strategies "
            f"(IDs: {strategy_ids or 'all'}, engine: {engine_type or 'all'})"
        )

        return strategies

    def score_strategy(
        self,
        strategy: SmartFlowStrategy,
        ai_features: Optional[Dict[str, float]] = None
    ) -> StrategyScore:
        """
        Score a single strategy with full traceability.

        Args:
            strategy: SmartFlowStrategy from database
            ai_features: Optional AI feature adjustments (from AI Feature Engine)

        Returns:
            StrategyScore with detailed breakdown
        """
        score = StrategyScore(
            strategy_id=strategy.strategy_id,
            engine_type=strategy.strategy_type,
            sharpe_ratio=strategy.sharpe_ratio,
            win_rate=strategy.win_rate,
            max_drawdown=strategy.max_drawdown,
            total_return_pct=strategy.total_return_pct,
            health_status=strategy.health_status,
            is_paused=strategy.is_paused,
            forward_test_passed=(strategy.forward_test_gate_passed_at is not None)
        )

        # Check exclusion criteria first
        if strategy.is_paused:
            score.excluded = True
            score.exclusion_reason = ExclusionReason.PAUSED
            score.notes = "Strategy is paused"
            return score

        if strategy.health_status == "unhealthy":
            score.excluded = True
            score.exclusion_reason = ExclusionReason.UNHEALTHY
            score.notes = f"Health status: {strategy.health_status}"
            return score

        if strategy.status not in ['built_in', 'approved_for_router']:
            score.excluded = True
            score.exclusion_reason = ExclusionReason.NOT_APPROVED
            score.notes = f"Status: {strategy.status}"
            return score

        # Check metric thresholds
        if score.max_drawdown and score.max_drawdown > self.max_drawdown_threshold:
            score.excluded = True
            score.exclusion_reason = ExclusionReason.POOR_METRICS
            score.notes = f"Max drawdown {score.max_drawdown:.1f}% exceeds threshold {self.max_drawdown_threshold}%"
            return score

        if score.win_rate and score.win_rate < self.min_win_rate:
            score.excluded = True
            score.exclusion_reason = ExclusionReason.POOR_METRICS
            score.notes = f"Win rate {score.win_rate:.2%} below threshold {self.min_win_rate:.2%}"
            return score

        # Compute score components

        # 1. Sharpe component (0-1, with 2.0 as excellent)
        if score.sharpe_ratio is not None:
            score.sharpe_component = min(max(score.sharpe_ratio / 2.0, 0.0), 1.0)
        else:
            score.sharpe_component = 0.5  # Neutral if unknown

        # 2. Drawdown component (0-1, inverse of drawdown %)
        if score.max_drawdown is not None:
            # Convert drawdown to positive score (lower drawdown = higher score)
            normalized_dd = 1.0 - min(score.max_drawdown / 100.0, 1.0)
            score.drawdown_component = max(normalized_dd, 0.0)
        else:
            score.drawdown_component = 0.5  # Neutral if unknown

        # 3. Profit factor component (0-1, with 2.0 as excellent)
        if score.profit_factor is not None:
            score.profit_factor_component = min(max(score.profit_factor / 2.0, 0.0), 1.0)
        else:
            # Estimate from win rate if available
            if score.win_rate:
                estimated_pf = score.win_rate / (1.0 - score.win_rate + 0.01)
                score.profit_factor_component = min(max(estimated_pf / 2.0, 0.0), 1.0)
            else:
                score.profit_factor_component = 0.5  # Neutral

        # 4. Forward-test bonus (0-1, binary for now)
        if score.forward_test_passed:
            score.forward_test_bonus = 1.0
        else:
            score.forward_test_bonus = 0.5  # Half credit if no forward test

        # 5. Health multiplier (Phase 10: Use drift-based health score)
        health_monitor = get_health_monitor()

        # Try to get latest health score from snapshots
        latest_health_snapshot = self.db.query(StrategyHealthSnapshot).filter(
            StrategyHealthSnapshot.strategy_id == strategy.strategy_id
        ).order_by(StrategyHealthSnapshot.snapshot_at.desc()).first()

        if latest_health_snapshot:
            # Use Phase 10 health penalty factor (based on 0-100 score)
            score.health_multiplier = health_monitor.get_health_penalty_factor(
                latest_health_snapshot.health_score
            )
        else:
            # Fallback to old string-based multipliers if no health snapshot
            score.health_multiplier = self.health_multipliers.get(
                strategy.health_status,
                0.8
            )

        # 6. AI adjustment (optional)
        if ai_features and 'overall_ai_bias' in ai_features:
            # AI bias is -1 to +1, convert to multiplier 0.5 to 1.5
            ai_bias = ai_features['overall_ai_bias']
            score.ai_adjustment = ai_bias * 0.5  # Maps [-1,1] to [-0.5,0.5]

        # Compute raw score (weighted sum)
        score.raw_score = (
            score.sharpe_component * self.sharpe_weight +
            score.drawdown_component * self.drawdown_weight +
            score.profit_factor_component * self.profit_factor_weight +
            score.forward_test_bonus * self.forward_test_weight
        )

        # Apply health multiplier and AI adjustment
        score.adjusted_score = score.raw_score * score.health_multiplier + score.ai_adjustment
        score.adjusted_score = max(score.adjusted_score, 0.0)  # Ensure non-negative

        # Exclude if score too low
        if score.adjusted_score < 0.1:
            score.excluded = True
            score.exclusion_reason = ExclusionReason.ZERO_SCORE
            score.notes = f"Adjusted score {score.adjusted_score:.3f} below minimum threshold"
        else:
            score.notes = f"Sharpe: {score.sharpe_component:.2f}, DD: {score.drawdown_component:.2f}, PF: {score.profit_factor_component:.2f}, FT: {score.forward_test_bonus:.2f}, Health: {score.health_multiplier:.2f}"

        return score

    def normalize_weights(self, scores: List[StrategyScore]) -> List[StrategyScore]:
        """
        Normalize strategy scores into allocation weights that sum to 1.0.

        Args:
            scores: List of StrategyScore objects (non-excluded only)

        Returns:
            Same list with allocation_weight set for each strategy
        """
        eligible_scores = [s for s in scores if not s.excluded]

        if not eligible_scores:
            logger.warning("⚠️ No eligible strategies to normalize weights")
            return scores

        # Sum of adjusted scores
        total_score = sum(s.adjusted_score for s in eligible_scores)

        if total_score == 0:
            # Equal weight fallback
            weight = 1.0 / len(eligible_scores)
            for s in eligible_scores:
                s.allocation_weight = weight
            logger.info(f"⚖️ Equal weight allocation: {weight:.3f} each across {len(eligible_scores)} strategies")
        else:
            # Proportional to adjusted score
            for s in eligible_scores:
                s.allocation_weight = s.adjusted_score / total_score

            logger.info(
                f"⚖️ Weight normalization: {len(eligible_scores)} strategies, "
                f"total score: {total_score:.3f}"
            )

        return scores

    def compute_allocation(
        self,
        strategy_ids: Optional[List[str]] = None,
        engine_type: Optional[str] = None,
        regime: Optional[str] = None,
        regime_confidence: Optional[float] = None,
        ai_features: Optional[Dict[str, float]] = None
    ) -> AllocationDecision:
        """
        Compute complete allocation decision.

        Args:
            strategy_ids: Optional list of specific strategies to score
            engine_type: Optional engine type filter
            regime: Current market regime (for metadata)
            regime_confidence: Regime detection confidence (for metadata)
            ai_features: Optional AI feature adjustments

        Returns:
            AllocationDecision with all scores, weights, and exclusions
        """
        # Get eligible strategies from registry
        strategies = self.get_eligible_strategies(strategy_ids, engine_type)

        if not strategies:
            logger.warning(f"⚠️ No eligible strategies found (IDs: {strategy_ids}, engine: {engine_type})")
            return AllocationDecision(
                notes="No eligible strategies found",
                current_regime=regime,
                regime_confidence=regime_confidence,
                ai_features_used=(ai_features is not None)
            )

        # Score each strategy
        all_scores = []
        for strategy in strategies:
            strategy_score = self.score_strategy(strategy, ai_features)
            all_scores.append(strategy_score)

            log_level = logging.INFO if not strategy_score.excluded else logging.DEBUG
            logger.log(
                log_level,
                f"  Strategy {strategy_score.strategy_id}: "
                f"score={strategy_score.adjusted_score:.3f}, "
                f"excluded={strategy_score.excluded}, "
                f"reason={strategy_score.exclusion_reason.value if strategy_score.exclusion_reason else 'N/A'}"
            )

        # Separate selected vs excluded
        selected = [s for s in all_scores if not s.excluded]
        excluded = [s for s in all_scores if s.excluded]

        # Normalize weights among selected strategies
        if selected:
            selected = self.normalize_weights(selected)

        # Build decision
        decision = AllocationDecision(
            selected_strategies=selected,
            excluded_strategies=excluded,
            total_weight=sum(s.allocation_weight for s in selected),
            current_regime=regime,
            regime_confidence=regime_confidence,
            ai_features_used=(ai_features is not None),
            decision_source="allocator",
            notes=f"Scored {len(all_scores)} strategies: {len(selected)} selected, {len(excluded)} excluded"
        )

        logger.info(
            f"✅ Allocation decision: {len(selected)} strategies selected, "
            f"total weight: {decision.total_weight:.3f}"
        )

        return decision

    def apply_portfolio_risk_constraints(
        self,
        decision: AllocationDecision,
        apply_correlation_penalty: bool = True
    ) -> Tuple[AllocationDecision, Optional[RiskSnapshot]]:
        """
        Apply portfolio-level risk constraints to allocation decision.

        Phase 11: Adjusts allocations based on:
        - Portfolio VaR limits
        - Correlation penalties
        - Risk budget constraints

        Args:
            decision: Initial allocation decision
            apply_correlation_penalty: Whether to apply correlation adjustments

        Returns:
            (adjusted_decision, portfolio_risk_snapshot)
        """
        if not decision.selected_strategies:
            return decision, None

        # Build allocation dict
        allocations = {
            s.strategy_id: s.allocation_weight
            for s in decision.selected_strategies
        }

        # Get portfolio risk engine
        risk_engine = get_portfolio_risk_engine()

        # Calculate portfolio risk
        portfolio_risk = risk_engine.calculate_portfolio_risk(self.db, allocations)

        # Apply correlation penalty if enabled
        if apply_correlation_penalty and portfolio_risk.strategy_risks:
            # Build correlation matrix from forward test data
            strategy_ids = list(allocations.keys())
            corr_matrix = risk_engine.estimate_correlation_matrix(
                self.db, strategy_ids, risk_engine.config.var_lookback_days
            )

            # Apply penalty
            adjusted_allocations = risk_engine.apply_correlation_penalty(
                allocations, corr_matrix
            )

            # Update strategy weights
            for strategy_score in decision.selected_strategies:
                if strategy_score.strategy_id in adjusted_allocations:
                    old_weight = strategy_score.allocation_weight
                    new_weight = adjusted_allocations[strategy_score.strategy_id]
                    strategy_score.allocation_weight = new_weight

                    if abs(new_weight - old_weight) > 0.01:
                        logger.info(
                            f"   Correlation adjusted {strategy_score.strategy_id}: "
                            f"{old_weight:.3f} → {new_weight:.3f}"
                        )

            # Recalculate total weight
            decision.total_weight = sum(
                s.allocation_weight for s in decision.selected_strategies
            )

            # Recalculate portfolio risk with adjusted allocations
            portfolio_risk = risk_engine.calculate_portfolio_risk(
                self.db, adjusted_allocations
            )

        # Update decision notes
        decision.notes += f" | Portfolio VaR: {portfolio_risk.portfolio_var:.2%}" if portfolio_risk.portfolio_var else ""
        decision.notes += f" | Risk budget: {portfolio_risk.risk_budget_used:.1f}%"

        if portfolio_risk.is_halted:
            decision.notes += f" | ⚠️ HALTED: {portfolio_risk.halt_reason}"
            logger.warning(f"🚨 Portfolio risk halt: {portfolio_risk.halt_reason}")

        logger.info(
            f"📊 Portfolio Risk Applied: VaR={portfolio_risk.portfolio_var:.2%}, "
            f"Vol={portfolio_risk.portfolio_volatility:.2%}, "
            f"Budget={portfolio_risk.risk_budget_used:.1f}%"
        )

        return decision, portfolio_risk

    def get_allocator_status(self) -> Dict:
        """
        Get current allocator status and configuration.

        Returns:
            Dict with allocator state, thresholds, and eligible strategy count
        """
        eligible_count = len(self.get_eligible_strategies())

        return {
            "allocator_enabled": True,
            "mode": "metadata_first",
            "eligible_strategies": eligible_count,
            "scoring_weights": {
                "sharpe": self.sharpe_weight,
                "drawdown": self.drawdown_weight,
                "profit_factor": self.profit_factor_weight,
                "forward_test": self.forward_test_weight
            },
            "thresholds": {
                "min_sharpe": self.min_sharpe,
                "max_drawdown_pct": self.max_drawdown_threshold,
                "min_win_rate": self.min_win_rate
            },
            "health_multipliers": self.health_multipliers
        }
