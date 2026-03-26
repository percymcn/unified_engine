"""
Strategy Registry API Router - Phase 6
=======================================

REST API endpoints for SmartFlow strategy registry, variant generation,
evaluation, and promotion workflow.

Phase 6A-6D: Core system endpoints (no router integration yet)
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.strategy_registry import (
    StrategyRegistry,
    get_strategy_registry,
    VariantGenerator,
    get_variant_generator,
    StrategyEvaluator,
    get_strategy_evaluator,
    StrategyStatus,
    StrategyType,
    VariantGenerateRequest,
    VariantGenerateResponse,
    EvaluationRequest,
    EvaluationResponse,
    PromotionRequest,
    RejectionRequest,
    StrategyResponse,
)
from app.services.strategy_registry.schemas import (
    StrategyListResponse,
    CandidateStats,
    RetirementRequest,
)

router = APIRouter(prefix="/api/strategies", tags=["Strategy Registry"])


# ============================================================================
# Registry Endpoints
# ============================================================================

@router.post("/seed", response_model=List[StrategyResponse])
def seed_built_in_strategies(
    db: Session = Depends(get_db)
):
    """
    Seed database with built-in SmartFlow strategies.

    Idempotent - only creates strategies that don't exist.

    Returns:
        List of created/existing built-in strategies
    """
    registry = StrategyRegistry(db)
    strategies = registry.seed_built_in_strategies()
    return [StrategyResponse.from_orm(s) for s in strategies]


@router.get("", response_model=StrategyListResponse)
def list_strategies(
    status: Optional[str] = Query(None, description="Filter by status (comma-separated)"),
    strategy_type: Optional[str] = Query(None, description="Filter by type"),
    parent_strategy_id: Optional[str] = Query(None, description="Filter by parent (variants only)"),
    db: Session = Depends(get_db)
):
    """
    List strategies with optional filters.

    Args:
        status: Filter by status (e.g., "built_in,approved_for_router")
        strategy_type: Filter by type (unified, deterministic, quick, flow, ai)
        parent_strategy_id: Filter by parent strategy (for variants)

    Returns:
        List of strategies matching filters
    """
    registry = StrategyRegistry(db)

    # Parse status filter
    status_list = status.split(',') if status else None

    strategies = registry.list_strategies(
        status=status_list,
        strategy_type=strategy_type,
        parent_strategy_id=parent_strategy_id
    )

    return StrategyListResponse(
        strategies=[StrategyResponse.from_orm(s) for s in strategies],
        total=len(strategies),
        status_filter=status,
        type_filter=strategy_type
    )


@router.get("/router-eligible", response_model=List[StrategyResponse])
def get_router_eligible_strategies(
    db: Session = Depends(get_db)
):
    """
    Get strategies eligible for router selection.

    Phase 7: Only built_in, approved_for_router, and active are eligible.
    Phase 8D: Excludes paused and unhealthy strategies.

    Returns:
        List of router-eligible strategies

    Raises:
        400: Database error
    """
    registry = StrategyRegistry(db)

    try:
        strategies = registry.get_router_eligible_strategies()
        return [StrategyResponse.from_orm(s) for s in strategies]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(
    strategy_id: str,
    db: Session = Depends(get_db)
):
    """
    Get strategy by ID.

    Args:
        strategy_id: Strategy ID (e.g., "deterministic_v1", "deterministic_v1.1")

    Returns:
        Strategy details

    Raises:
        404: Strategy not found
    """
    registry = StrategyRegistry(db)
    strategy = registry.get_strategy(strategy_id)

    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")

    return StrategyResponse.from_orm(strategy)


@router.get("/{strategy_id}/candidate-stats", response_model=CandidateStats)
def get_candidate_stats(
    strategy_id: str,
    db: Session = Depends(get_db)
):
    """
    Get candidate statistics for a base strategy.

    Args:
        strategy_id: Base strategy ID

    Returns:
        Candidate statistics (active count, max, can create more)
    """
    registry = StrategyRegistry(db)

    # Verify strategy exists
    strategy = registry.get_strategy(strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_id}")

    return registry.get_candidate_stats(strategy_id)


# ============================================================================
# Variant Generation Endpoints
# ============================================================================

@router.post("/variants/generate", response_model=VariantGenerateResponse)
def generate_variant(
    request: VariantGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a new strategy variant from a base strategy.

    Creates a parameterized variant with:
    - Auto-generated version (e.g., deterministic_v1 → deterministic_v1.1)
    - Merged parameters (parent + changes)
    - Candidate status
    - Hypothesis documentation

    Args:
        request: Variant generation request

    Returns:
        Generated variant details

    Raises:
        400: Invalid request (parent not found, candidate limit exceeded, etc.)
    """
    generator = VariantGenerator(StrategyRegistry(db))

    try:
        variant = generator.generate_variant(request)
        return variant
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Evaluation Endpoints
# ============================================================================

@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_strategy(
    request: EvaluationRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluate a strategy through backtest and criteria checks.

    Runs backtest and evaluates against Phase 6C criteria:
    - Sharpe Ratio >= 1.0
    - Win Rate >= 50%
    - Max Drawdown <= 20%
    - Total Trades >= 20
    - Net Profit > 0

    Creates evaluation record and updates strategy performance.

    Args:
        request: Evaluation request

    Returns:
        Evaluation results with APPROVE/REJECT recommendation

    Raises:
        400: Strategy not found or not eligible for evaluation
    """
    evaluator = StrategyEvaluator(StrategyRegistry(db))

    try:
        evaluation = await evaluator.evaluate_strategy(request)
        return evaluation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Promotion/Rejection Endpoints
# ============================================================================

@router.post("/promote", response_model=StrategyResponse)
def promote_strategy(
    request: PromotionRequest,
    db: Session = Depends(get_db)
):
    """
    Promote candidate to approved_for_router status.

    Requires:
    - Strategy is currently a candidate
    - Strategy has been evaluated
    - Human approval (approved_by + approval_notes)

    Args:
        request: Promotion request

    Returns:
        Promoted strategy

    Raises:
        400: Strategy not eligible for promotion
    """
    registry = StrategyRegistry(db)

    try:
        strategy = registry.promote_strategy(
            strategy_id=request.strategy_id,
            approved_by=request.approved_by,
            approval_notes=request.approval_notes
        )
        return StrategyResponse.from_orm(strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reject", response_model=StrategyResponse)
def reject_strategy(
    request: RejectionRequest,
    db: Session = Depends(get_db)
):
    """
    Reject a candidate strategy.

    Requires:
    - Strategy is currently a candidate
    - Rejection metadata (rejected_by + rejection_notes)

    Args:
        request: Rejection request

    Returns:
        Rejected strategy

    Raises:
        400: Strategy not eligible for rejection
    """
    registry = StrategyRegistry(db)

    try:
        strategy = registry.reject_strategy(
            strategy_id=request.strategy_id,
            rejected_by=request.rejected_by,
            rejection_notes=request.rejection_notes
        )
        return StrategyResponse.from_orm(strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retire", response_model=StrategyResponse)
def retire_strategy(
    request: RetirementRequest,
    db: Session = Depends(get_db)
):
    """
    Retire an approved strategy.

    Requires:
    - Strategy is currently approved_for_router
    - Cannot retire built-in strategies
    - Retirement metadata (retired_by + retirement_reason)

    Args:
        request: Retirement request

    Returns:
        Retired strategy

    Raises:
        400: Strategy not eligible for retirement
    """
    registry = StrategyRegistry(db)

    try:
        strategy = registry.retire_strategy(
            strategy_id=request.strategy_id,
            retired_by=request.retired_by,
            retirement_reason=request.retirement_reason
        )
        return StrategyResponse.from_orm(strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Phase 7: Forward-Test Gate Endpoints
# ============================================================================

from pydantic import BaseModel as PydanticBaseModel, Field as PydanticField
from app.services.strategy_registry.forward_test_gate import ForwardTestGate, get_forward_test_gate


class ApproveForForwardTestRequest(PydanticBaseModel):
    """Request to approve candidate for forward testing."""
    strategy_id: str
    approved_by: str = PydanticField(..., description="Admin who approves")
    approval_notes: str = PydanticField(..., description="Why this is being approved for forward test")


class StartForwardTestRequest(PydanticBaseModel):
    """Request to start forward testing."""
    strategy_id: str
    session_id: str = PydanticField(..., description="Forward-test session ID")


class EvaluateGateRequest(PydanticBaseModel):
    """Request to evaluate forward-test gate."""
    strategy_id: str
    session_id: str
    evaluated_by: str = PydanticField(..., description="Admin who evaluates")


class ApproveForRouterRequest(PydanticBaseModel):
    """Request to approve strategy for router after gate pass."""
    strategy_id: str
    approved_by: str = PydanticField(..., description="Admin who approves")


class FailForwardTestRequest(PydanticBaseModel):
    """Request to fail forward test."""
    strategy_id: str
    failed_by: str = PydanticField(..., description="Admin who fails")


@router.post("/approve-for-forward-test", response_model=StrategyResponse)
def approve_for_forward_test(
    request: ApproveForForwardTestRequest,
    db: Session = Depends(get_db)
):
    """
    Approve candidate for forward testing (after backtest evaluation).

    Phase 7: First gate - backtest passed, ready for forward test.

    Requires:
    - Strategy is currently a candidate
    - Strategy has been evaluated (backtest)
    - Human approval

    Args:
        request: Approval request

    Returns:
        Updated strategy with approved_for_forward_test status

    Raises:
        400: Strategy not eligible for forward test approval
    """
    registry = StrategyRegistry(db)

    try:
        strategy = registry.approve_for_forward_test(
            strategy_id=request.strategy_id,
            approved_by=request.approved_by,
            approval_notes=request.approval_notes
        )
        return StrategyResponse.from_orm(strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/start-forward-test", response_model=StrategyResponse)
def start_forward_test(
    request: StartForwardTestRequest,
    db: Session = Depends(get_db)
):
    """
    Mark strategy as forward_testing and link to session.

    Requires:
    - Strategy is approved_for_forward_test
    - Valid session_id

    Args:
        request: Start forward test request

    Returns:
        Updated strategy with forward_testing status

    Raises:
        400: Strategy not eligible to start forward test
    """
    registry = StrategyRegistry(db)

    try:
        strategy = registry.start_forward_testing(
            strategy_id=request.strategy_id,
            session_id=request.session_id
        )
        return StrategyResponse.from_orm(strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


from app.services.strategy_registry.forward_test_gate import ForwardTestGateDecision as GateDecisionModel


@router.post("/evaluate-forward-test-gate")
async def evaluate_forward_test_gate(
    request: EvaluateGateRequest,
    db: Session = Depends(get_db)
):
    """
    Evaluate forward-test session against gate criteria.

    Phase 7: Safety gate evaluation.

    Criteria:
    - Minimum 30 trades
    - Win rate >= 45%
    - Max drawdown <= 25%
    - Profit factor >= 1.2
    - No catastrophic degradation vs backtest

    Args:
        request: Evaluation request

    Returns:
        Gate decision with pass/fail and detailed criteria results

    Raises:
        400: Session or strategy not found
    """
    gate = ForwardTestGate(db)

    try:
        decision = gate.evaluate_gate(
            session_id=request.session_id,
            strategy_id=request.strategy_id,
            evaluated_by=request.evaluated_by
        )

        # Store gate decision in session
        from app.models.forward_test_models import ForwardTestSession
        session = db.query(ForwardTestSession).filter(
            ForwardTestSession.session_id == request.session_id
        ).first()

        if session:
            session.gate_status = 'passed' if decision.passed else 'failed'
            session.gate_evaluated_at = decision.evaluated_at
            session.gate_evaluated_by = decision.evaluated_by
            session.gate_decision_reason = decision.decision_reason
            session.gate_criteria_results = [cr.dict() for cr in decision.criteria_results]
            db.commit()

        return decision.dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/approve-for-router-after-gate", response_model=StrategyResponse)
async def approve_for_router_after_gate(
    request: ApproveForRouterRequest,
    db: Session = Depends(get_db)
):
    """
    Approve strategy for router after passing forward-test gate.

    Phase 7: Final gate - forward test passed, router-eligible.

    Requires:
    - Strategy is forward_testing
    - Gate has been evaluated and passed

    Args:
        request: Approval request

    Returns:
        Updated strategy with approved_for_router status

    Raises:
        400: Strategy not eligible or gate not passed
    """
    registry = StrategyRegistry(db)
    gate = ForwardTestGate(db)

    try:
        # Get strategy and session
        strategy = registry.get_strategy(request.strategy_id)
        if not strategy or not strategy.latest_forward_test_session_id:
            raise ValueError(f"Strategy or forward-test session not found")

        # Re-evaluate gate to get decision
        decision = gate.evaluate_gate(
            session_id=strategy.latest_forward_test_session_id,
            strategy_id=request.strategy_id,
            evaluated_by=request.approved_by
        )

        # Approve for router
        strategy = registry.approve_for_router_after_gate(
            strategy_id=request.strategy_id,
            approved_by=request.approved_by,
            gate_decision=decision
        )

        return StrategyResponse.from_orm(strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/fail-forward-test", response_model=StrategyResponse)
async def fail_forward_test(
    request: FailForwardTestRequest,
    db: Session = Depends(get_db)
):
    """
    Fail strategy at forward-test gate.

    Requires:
    - Strategy is forward_testing
    - Gate has been evaluated and failed

    Args:
        request: Failure request

    Returns:
        Updated strategy with rejected status

    Raises:
        400: Strategy not eligible
    """
    registry = StrategyRegistry(db)
    gate = ForwardTestGate(db)

    try:
        # Get strategy and session
        strategy = registry.get_strategy(request.strategy_id)
        if not strategy or not strategy.latest_forward_test_session_id:
            raise ValueError(f"Strategy or forward-test session not found")

        # Re-evaluate gate to get decision
        decision = gate.evaluate_gate(
            session_id=strategy.latest_forward_test_session_id,
            strategy_id=request.strategy_id,
            evaluated_by=request.failed_by
        )

        # Fail forward test
        strategy = registry.fail_forward_test(
            strategy_id=request.strategy_id,
            failed_by=request.failed_by,
            gate_decision=decision
        )

        return StrategyResponse.from_orm(strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Phase 8D: Operational Hardening Endpoints
# ============================================================================

class PauseStrategyRequest(PydanticBaseModel):
    """Request to pause a strategy."""
    strategy_id: str
    paused_by: str = PydanticField(..., description="Admin who pauses")
    pause_reason: str = PydanticField(..., description="Why this strategy is being paused")


class ResumeStrategyRequest(PydanticBaseModel):
    """Request to resume a paused strategy."""
    strategy_id: str
    resumed_by: str = PydanticField(..., description="Admin who resumes")


class UpdateHealthRequest(PydanticBaseModel):
    """Request to update strategy health status."""
    strategy_id: str
    health_status: str = PydanticField(..., description="Health status: healthy, degraded, unhealthy, unknown")
    health_notes: Optional[str] = PydanticField(None, description="Optional health notes")


@router.post("/pause", response_model=StrategyResponse)
def pause_strategy(
    request: PauseStrategyRequest,
    db: Session = Depends(get_db)
):
    """
    Pause a strategy without retiring it.

    Phase 8D: Operational control to temporarily disable strategy from router.

    Paused strategies:
    - Are excluded from router selection
    - Retain their status (built_in, approved_for_router, etc.)
    - Can be resumed at any time

    Args:
        request: Pause request

    Returns:
        Paused strategy

    Raises:
        400: Strategy not found or already paused
    """
    registry = StrategyRegistry(db)

    try:
        strategy = registry.pause_strategy(
            strategy_id=request.strategy_id,
            paused_by=request.paused_by,
            pause_reason=request.pause_reason
        )
        return StrategyResponse.from_orm(strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resume", response_model=StrategyResponse)
def resume_strategy(
    request: ResumeStrategyRequest,
    db: Session = Depends(get_db)
):
    """
    Resume a paused strategy.

    Phase 8D: Re-enable strategy for router selection.

    Args:
        request: Resume request

    Returns:
        Resumed strategy

    Raises:
        400: Strategy not found or not paused
    """
    registry = StrategyRegistry(db)

    try:
        strategy = registry.resume_strategy(
            strategy_id=request.strategy_id,
            resumed_by=request.resumed_by
        )
        return StrategyResponse.from_orm(strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/update-health", response_model=StrategyResponse)
def update_health_status(
    request: UpdateHealthRequest,
    db: Session = Depends(get_db)
):
    """
    Update strategy health status.

    Phase 8D: Track strategy health for operational monitoring.

    Health statuses:
    - healthy: Strategy performing normally, router-eligible
    - degraded: Minor issues detected, router-eligible but monitored
    - unhealthy: Serious issues, excluded from router
    - unknown: Health not yet determined

    Router excludes 'unhealthy' strategies.

    Args:
        request: Health update request

    Returns:
        Updated strategy

    Raises:
        400: Strategy not found or invalid health status
    """
    registry = StrategyRegistry(db)

    try:
        strategy = registry.update_health_status(
            strategy_id=request.strategy_id,
            health_status=request.health_status,
            health_notes=request.health_notes
        )
        return StrategyResponse.from_orm(strategy)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Phase 10: Drift Detection + Strategy Health Scoring
# ============================================================================

from app.services.strategy_registry.health import (
    StrategyHealthMonitor,
    get_health_monitor,
    HealthScore,
    HealthStatus as HealthStatusEnum,
    DriftMetrics
)
from app.models.strategy_registry_models import StrategyHealthSnapshot


class HealthScoreResponse(PydanticBaseModel):
    """Health score response."""
    strategy_id: str
    health_score: float
    health_status: str
    drift_metrics: dict
    health_factors: dict
    notes: List[str]
    timestamp: str
    auto_paused: bool = False

    class Config:
        from_attributes = True


class HealthHistoryResponse(PydanticBaseModel):
    """Health history response."""
    strategy_id: str
    snapshots: List[dict]
    total_snapshots: int


@router.post("/{strategy_id}/evaluate-health", response_model=HealthScoreResponse)
def evaluate_strategy_health(
    strategy_id: str,
    auto_pause_on_critical: bool = Query(True, description="Auto-pause if health is critical"),
    db: Session = Depends(get_db)
):
    """
    Evaluate strategy health by detecting performance drift.

    Phase 10: Compares current forward-test metrics against baseline backtest
    metrics and calculates a composite health score (0-100).

    Health Scoring:
    - 70-100: Healthy (no issues)
    - 40-69: Degraded (performance declining)
    - 0-39: Critical (severe degradation, auto-pause)

    Drift Detection:
    - Sharpe ratio drift: -20% triggers alert
    - Win rate drift: -10% triggers alert
    - Drawdown drift: +30% worse triggers alert

    Args:
        strategy_id: Strategy to evaluate
        auto_pause_on_critical: Auto-pause if health critical

    Returns:
        Health score with drift analysis

    Raises:
        404: Strategy not found
        400: Insufficient data for evaluation
    """
    # Check strategy exists
    strategy = db.query(SmartFlowStrategy).filter(
        SmartFlowStrategy.strategy_id == strategy_id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

    # Evaluate health
    monitor = get_health_monitor()
    health = monitor.evaluate_strategy_health(
        db=db,
        strategy_id=strategy_id,
        auto_pause_on_critical=auto_pause_on_critical
    )

    # Save snapshot
    snapshot = StrategyHealthSnapshot(
        strategy_id=strategy_id,
        health_score=health.score,
        health_status=health.status.value,
        baseline_sharpe=health.drift_metrics.baseline_sharpe,
        baseline_win_rate=health.drift_metrics.baseline_win_rate,
        baseline_max_dd=health.drift_metrics.baseline_max_dd,
        baseline_trades=health.drift_metrics.baseline_trades,
        current_sharpe=health.drift_metrics.current_sharpe,
        current_win_rate=health.drift_metrics.current_win_rate,
        current_max_dd=health.drift_metrics.current_max_dd,
        current_trades=health.drift_metrics.current_trades,
        sharpe_drift_pct=health.drift_metrics.sharpe_drift_pct,
        win_rate_drift_pct=health.drift_metrics.win_rate_drift_pct,
        drawdown_drift_pct=health.drift_metrics.drawdown_drift_pct,
        sharpe_drifted=health.drift_metrics.sharpe_drifted,
        win_rate_drifted=health.drift_metrics.win_rate_drifted,
        drawdown_drifted=health.drift_metrics.drawdown_drifted,
        insufficient_trades=health.drift_metrics.insufficient_trades,
        health_factors=health.health_factors,
        notes="; ".join(health.notes) if health.notes else None,
        auto_paused=(health.status == HealthStatusEnum.CRITICAL and auto_pause_on_critical)
    )
    db.add(snapshot)
    db.commit()

    return HealthScoreResponse(
        strategy_id=strategy_id,
        health_score=health.score,
        health_status=health.status.value,
        drift_metrics={
            "baseline_sharpe": health.drift_metrics.baseline_sharpe,
            "current_sharpe": health.drift_metrics.current_sharpe,
            "sharpe_drift_pct": health.drift_metrics.sharpe_drift_pct,
            "baseline_win_rate": health.drift_metrics.baseline_win_rate,
            "current_win_rate": health.drift_metrics.current_win_rate,
            "win_rate_drift_pct": health.drift_metrics.win_rate_drift_pct,
            "baseline_max_dd": health.drift_metrics.baseline_max_dd,
            "current_max_dd": health.drift_metrics.current_max_dd,
            "drawdown_drift_pct": health.drift_metrics.drawdown_drift_pct,
        },
        health_factors=health.health_factors,
        notes=health.notes,
        timestamp=health.timestamp.isoformat(),
        auto_paused=(health.status == HealthStatusEnum.CRITICAL and auto_pause_on_critical)
    )


@router.get("/{strategy_id}/health-history", response_model=HealthHistoryResponse)
def get_health_history(
    strategy_id: str,
    limit: int = Query(10, ge=1, le=100, description="Max snapshots to return"),
    db: Session = Depends(get_db)
):
    """
    Get health evaluation history for a strategy.

    Phase 10: Returns recent health snapshots showing drift over time.

    Args:
        strategy_id: Strategy to query
        limit: Max number of snapshots

    Returns:
        Health history with snapshots

    Raises:
        404: Strategy not found
    """
    # Check strategy exists
    strategy = db.query(SmartFlowStrategy).filter(
        SmartFlowStrategy.strategy_id == strategy_id
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

    # Get snapshots
    snapshots = db.query(StrategyHealthSnapshot).filter(
        StrategyHealthSnapshot.strategy_id == strategy_id
    ).order_by(StrategyHealthSnapshot.snapshot_at.desc()).limit(limit).all()

    return HealthHistoryResponse(
        strategy_id=strategy_id,
        snapshots=[
            {
                "snapshot_at": s.snapshot_at.isoformat(),
                "health_score": s.health_score,
                "health_status": s.health_status,
                "sharpe_drift_pct": s.sharpe_drift_pct,
                "win_rate_drift_pct": s.win_rate_drift_pct,
                "drawdown_drift_pct": s.drawdown_drift_pct,
                "notes": s.notes,
                "auto_paused": s.auto_paused
            }
            for s in snapshots
        ],
        total_snapshots=len(snapshots)
    )


# ============================================================================
# Phase 11: Portfolio Risk Engine
# ============================================================================

from app.services.strategy_registry.portfolio_risk import (
    PortfolioRiskEngine,
    get_portfolio_risk_engine,
    PortfolioRiskConfig
)
from app.models.strategy_registry_models import PortfolioRiskSnapshot as PortfolioRiskSnapshotModel


class PortfolioRiskResponse(PydanticBaseModel):
    """Portfolio risk response."""
    timestamp: str
    total_strategies: int
    active_strategies: int
    portfolio_var: Optional[float]
    portfolio_cvar: Optional[float]
    portfolio_volatility: Optional[float]
    risk_budget_used: float
    risk_budget_available: float
    current_leverage: float
    recommended_leverage: float
    is_halted: bool
    halt_reason: Optional[str]
    strategy_risks: List[dict]

    class Config:
        from_attributes = True


class PortfolioRiskHistoryResponse(PydanticBaseModel):
    """Portfolio risk history response."""
    snapshots: List[dict]
    total_snapshots: int


@router.get("/portfolio/risk", response_model=PortfolioRiskResponse)
def get_current_portfolio_risk(
    db: Session = Depends(get_db)
):
    """
    Get current portfolio risk metrics.

    Phase 11: Calculates aggregated risk across all active strategies including:
    - Portfolio VaR (Value at Risk)
    - Portfolio volatility
    - Risk budget utilization
    - Correlation-adjusted allocations

    Returns:
        Current portfolio risk snapshot

    Raises:
        500: Error calculating portfolio risk
    """
    try:
        # Get all active strategies with allocations
        from app.services.strategy_allocator import StrategyAllocator

        allocator = StrategyAllocator(db)
        allocation_decision = allocator.compute_allocation()

        if not allocation_decision.selected_strategies:
            # No active strategies
            return PortfolioRiskResponse(
                timestamp=datetime.now(timezone.utc).isoformat(),
                total_strategies=0,
                active_strategies=0,
                portfolio_var=None,
                portfolio_cvar=None,
                portfolio_volatility=None,
                risk_budget_used=0.0,
                risk_budget_available=100.0,
                current_leverage=1.0,
                recommended_leverage=1.0,
                is_halted=False,
                halt_reason=None,
                strategy_risks=[]
            )

        # Build allocation dict
        allocations = {
            s.strategy_id: s.allocation_weight
            for s in allocation_decision.selected_strategies
        }

        # Calculate portfolio risk
        risk_engine = get_portfolio_risk_engine()
        portfolio_risk = risk_engine.calculate_portfolio_risk(db, allocations)

        # Save snapshot to database
        db_snapshot = PortfolioRiskSnapshotModel(
            total_strategies=portfolio_risk.total_strategies,
            active_strategies=portfolio_risk.active_strategies,
            total_allocation_pct=portfolio_risk.total_allocation_pct,
            portfolio_var=portfolio_risk.portfolio_var,
            portfolio_cvar=portfolio_risk.portfolio_cvar,
            portfolio_volatility=portfolio_risk.portfolio_volatility,
            portfolio_sharpe=portfolio_risk.portfolio_sharpe,
            current_drawdown_pct=portfolio_risk.current_drawdown_pct,
            max_drawdown_pct=portfolio_risk.max_drawdown_pct,
            current_leverage=portfolio_risk.current_leverage,
            recommended_leverage=portfolio_risk.recommended_leverage,
            risk_budget_used=portfolio_risk.risk_budget_used,
            risk_budget_available=portfolio_risk.risk_budget_available,
            is_halted=portfolio_risk.is_halted,
            halt_reason=portfolio_risk.halt_reason,
            strategy_risks=[
                {
                    "strategy_id": sr.strategy_id,
                    "daily_vol": sr.daily_vol,
                    "var_95": sr.var_95,
                    "risk_budget_used": sr.risk_budget_used
                }
                for sr in portfolio_risk.strategy_risks
            ]
        )
        db.add(db_snapshot)
        db.commit()

        return PortfolioRiskResponse(
            timestamp=portfolio_risk.timestamp.isoformat(),
            total_strategies=portfolio_risk.total_strategies,
            active_strategies=portfolio_risk.active_strategies,
            portfolio_var=portfolio_risk.portfolio_var,
            portfolio_cvar=portfolio_risk.portfolio_cvar,
            portfolio_volatility=portfolio_risk.portfolio_volatility,
            risk_budget_used=portfolio_risk.risk_budget_used,
            risk_budget_available=portfolio_risk.risk_budget_available,
            current_leverage=portfolio_risk.current_leverage,
            recommended_leverage=portfolio_risk.recommended_leverage,
            is_halted=portfolio_risk.is_halted,
            halt_reason=portfolio_risk.halt_reason,
            strategy_risks=[
                {
                    "strategy_id": sr.strategy_id,
                    "daily_vol": sr.daily_vol,
                    "annual_vol": sr.annual_vol,
                    "var_95": sr.var_95,
                    "risk_budget_used": sr.risk_budget_used
                }
                for sr in portfolio_risk.strategy_risks
            ]
        )

    except Exception as e:
        logger.error(f"Portfolio risk calculation error: {e}")
        raise HTTPException(status_code=500, detail=f"Error calculating portfolio risk: {str(e)}")


@router.get("/portfolio/risk/history", response_model=PortfolioRiskHistoryResponse)
def get_portfolio_risk_history(
    limit: int = Query(10, ge=1, le=100, description="Max snapshots to return"),
    db: Session = Depends(get_db)
):
    """
    Get portfolio risk history.

    Phase 11: Returns recent portfolio risk snapshots showing risk evolution.

    Args:
        limit: Max number of snapshots

    Returns:
        Portfolio risk history

    Raises:
        500: Error retrieving history
    """
    try:
        snapshots = db.query(PortfolioRiskSnapshotModel).order_by(
            PortfolioRiskSnapshotModel.snapshot_at.desc()
        ).limit(limit).all()

        return PortfolioRiskHistoryResponse(
            snapshots=[
                {
                    "snapshot_at": s.snapshot_at.isoformat(),
                    "total_strategies": s.total_strategies,
                    "active_strategies": s.active_strategies,
                    "portfolio_var": s.portfolio_var,
                    "portfolio_volatility": s.portfolio_volatility,
                    "risk_budget_used": s.risk_budget_used,
                    "is_halted": s.is_halted,
                    "recommended_leverage": s.recommended_leverage
                }
                for s in snapshots
            ],
            total_snapshots=len(snapshots)
        )

    except Exception as e:
        logger.error(f"Portfolio risk history error: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving risk history: {str(e)}")
