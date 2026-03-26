"""
Strategy Registry Models - Phase 6
===================================

Database models for SmartFlow strategy registry, variant tracking,
and evaluation pipeline.

This registry manages:
1. Built-in SmartFlow engines (unified, deterministic, quick, flow, ai)
2. User-generated strategy variants
3. Evaluation results
4. Approval workflow
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base


class SmartFlowStrategy(Base):
    """
    SmartFlow Strategy Registry.

    Stores built-in engines and their variants with full lifecycle tracking.
    """
    __tablename__ = "smartflow_strategies"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, unique=True, index=True, nullable=False)  # e.g., "deterministic_v1.2"
    strategy_type = Column(String, index=True, nullable=False)  # unified, deterministic, quick, flow, ai
    version = Column(String, nullable=False)  # e.g., "1.2.0"
    status = Column(String, index=True, nullable=False)  # built_in, candidate, approved_for_router, rejected, retired

    # Configuration
    parameters = Column(JSON, nullable=False)  # Strategy-specific parameters
    parent_strategy_id = Column(String, nullable=True)  # For variants (null for built-ins)
    parameter_changes = Column(JSON, nullable=True)  # What changed from parent
    hypothesis = Column(Text, nullable=True)  # Why this variant was created

    # Performance metrics (from latest evaluation)
    sharpe_ratio = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    total_return_pct = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    backtest_days = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, nullable=True)  # User who created variant

    # Evaluation tracking
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    latest_evaluation_id = Column(Integer, nullable=True)
    latest_comparison_id = Column(String, nullable=True)

    # Approval tracking
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String, nullable=True)  # Admin who approved
    approval_notes = Column(Text, nullable=True)

    # Rejection tracking
    rejected_at = Column(DateTime(timezone=True), nullable=True)
    rejected_by = Column(String, nullable=True)
    rejection_notes = Column(Text, nullable=True)

    # Retirement tracking
    retired_at = Column(DateTime(timezone=True), nullable=True)
    retired_by = Column(String, nullable=True)
    retirement_reason = Column(Text, nullable=True)

    # Phase 7: Forward-Test Gate Tracking
    approved_for_forward_test_at = Column(DateTime(timezone=True), nullable=True)
    approved_for_forward_test_by = Column(String, nullable=True)
    forward_testing_started_at = Column(DateTime(timezone=True), nullable=True)
    latest_forward_test_session_id = Column(String, nullable=True)  # Links to ForwardTestSession.session_id
    forward_test_gate_passed_at = Column(DateTime(timezone=True), nullable=True)
    forward_test_gate_passed_by = Column(String, nullable=True)
    forward_test_gate_failed_at = Column(DateTime(timezone=True), nullable=True)
    forward_test_gate_failed_by = Column(String, nullable=True)
    forward_test_gate_failure_reason = Column(Text, nullable=True)
    approved_for_router_at = Column(DateTime(timezone=True), nullable=True)
    approved_for_router_by = Column(String, nullable=True)
    active_at = Column(DateTime(timezone=True), nullable=True)  # When router first selected it
    archived_at = Column(DateTime(timezone=True), nullable=True)

    # Phase 8C: Canonical Identity & Lineage
    family_id = Column(String, index=True, nullable=True)
        # Root strategy family (e.g., "deterministic", "quick")
        # Built-ins: family_id = strategy_type
        # Variants: family_id = parent's family_id
    variant_hash = Column(String(64), unique=True, nullable=True)
        # SHA256 of (parent_strategy_id + parameter_changes)
        # Prevents duplicate variants
        # NULL for built-ins
    generation = Column(Integer, default=0, nullable=False)
        # 0 = built-in
        # 1 = first-generation variant
        # 2 = variant of variant, etc.
    lineage_path = Column(String, nullable=True)
        # Full ancestry path: "deterministic_v1 > deterministic_v1.1 > deterministic_v1.1.1"

    # Phase 8C: Snapshot Links
    latest_backtest_snapshot_id = Column(Integer, nullable=True)
    latest_forward_test_snapshot_id = Column(Integer, nullable=True)

    # Phase 8C: Tags for filtering/organization
    tags = Column(JSON, nullable=True, default=list)
        # Examples: ["engine:deterministic", "source:built_in", "router:eligible"]

    # Phase 8D: Operational Hardening
    is_paused = Column(Boolean, default=False, index=True, nullable=False)
        # Admin can pause strategy without retiring it
    paused_at = Column(DateTime(timezone=True), nullable=True)
    paused_by = Column(String, nullable=True)
    pause_reason = Column(Text, nullable=True)

    health_status = Column(String, default="healthy", index=True, nullable=False)
        # "healthy", "degraded", "unhealthy", "unknown"
    health_checked_at = Column(DateTime(timezone=True), nullable=True)
    health_notes = Column(Text, nullable=True)

    rollback_target_strategy_id = Column(String, nullable=True)
        # If this strategy fails, router can rollback to this strategy
    last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    last_reviewed_by = Column(String, nullable=True)

    # Relationships
    evaluations = relationship("StrategyEvaluation", back_populates="strategy", cascade="all, delete-orphan")


class StrategyEvaluation(Base):
    """
    Strategy Evaluation Results.

    Records backtest evaluation for a strategy variant.
    """
    __tablename__ = "strategy_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, ForeignKey("smartflow_strategies.strategy_id"), nullable=False)
    comparison_id = Column(String, nullable=False)  # Links to comparison_store

    # Evaluation configuration
    ticker = Column(String, nullable=False)
    backtest_days = Column(Integer, nullable=False)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)

    # Performance results
    sharpe_ratio = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    total_return_pct = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    net_profit = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)

    # Evaluation criteria
    criteria_checked = Column(JSON, nullable=False)  # Which criteria were evaluated
    criteria_results = Column(JSON, nullable=False)  # Which passed/failed
    passed = Column(Boolean, nullable=False)  # Overall pass/fail
    recommendation = Column(String, nullable=False)  # APPROVE or REJECT

    # Metadata
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
    evaluated_by = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    strategy = relationship("SmartFlowStrategy", back_populates="evaluations")


class StrategyCandidate(Base):
    """
    Active candidate tracking with generation metadata.

    Separate table for easier querying and candidate limits enforcement.
    """
    __tablename__ = "strategy_candidates"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, ForeignKey("smartflow_strategies.strategy_id"), unique=True, nullable=False)
    parent_strategy_id = Column(String, nullable=False)  # Base strategy this is variant of

    # Generation metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, nullable=True)

    # Limits enforcement
    is_active = Column(Boolean, default=True)  # Can be deactivated to enforce limits


# Phase 8C: Performance Snapshot Models
# ======================================

class StrategyBacktestSnapshot(Base):
    """
    Backtest performance snapshot for a strategy.

    Phase 8C: Separates time-varying metrics from strategy identity.
    """
    __tablename__ = "strategy_backtest_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, ForeignKey("smartflow_strategies.strategy_id"), nullable=False, index=True)
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Backtest configuration
    ticker = Column(String, nullable=False)
    backtest_days = Column(Integer, nullable=False)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)

    # Performance metrics
    sharpe_ratio = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    total_return_pct = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    net_profit = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)

    # Links
    comparison_id = Column(String, nullable=True)  # Links to comparison_store
    evaluation_id = Column(Integer, ForeignKey("strategy_evaluations.id"), nullable=True)


class StrategyForwardTestSnapshot(Base):
    """
    Forward-test performance snapshot for a strategy.

    Phase 8C: Tracks forward-test results over time.
    """
    __tablename__ = "strategy_forward_test_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, ForeignKey("smartflow_strategies.strategy_id"), nullable=False, index=True)
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Forward-test session
    session_id = Column(String, nullable=False)
        # Links to forward_test_sessions.session_id

    # Performance metrics
    total_trades = Column(Integer, nullable=False)
    winning_trades = Column(Integer, nullable=True)
    losing_trades = Column(Integer, nullable=True)
    win_rate = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    total_pnl = Column(Float, nullable=True)

    # Gate results
    gate_status = Column(String, nullable=True)  # "passed", "failed", "in_progress"
    gate_evaluated_at = Column(DateTime(timezone=True), nullable=True)
    gate_evaluated_by = Column(String, nullable=True)
    gate_criteria_results = Column(JSON, nullable=True)


class StrategyHealthSnapshot(Base):
    """
    Health evaluation snapshot for a strategy.

    Phase 10: Drift Detection + Strategy Health Scoring
    Stores health checks over time to track strategy degradation.
    """
    __tablename__ = "strategy_health_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, ForeignKey("smartflow_strategies.strategy_id"), nullable=False, index=True)
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Health score
    health_score = Column(Float, nullable=False)
    health_status = Column(String, nullable=False)  # healthy, degraded, critical, unknown

    # Drift metrics - Baseline (from backtest)
    baseline_sharpe = Column(Float, nullable=True)
    baseline_win_rate = Column(Float, nullable=True)
    baseline_max_dd = Column(Float, nullable=True)
    baseline_trades = Column(Integer, nullable=True)

    # Drift metrics - Current (from forward test)
    current_sharpe = Column(Float, nullable=True)
    current_win_rate = Column(Float, nullable=True)
    current_max_dd = Column(Float, nullable=True)
    current_trades = Column(Integer, nullable=True)

    # Drift percentages
    sharpe_drift_pct = Column(Float, nullable=True)
    win_rate_drift_pct = Column(Float, nullable=True)
    drawdown_drift_pct = Column(Float, nullable=True)

    # Flags
    sharpe_drifted = Column(Boolean, default=False)
    win_rate_drifted = Column(Boolean, default=False)
    drawdown_drifted = Column(Boolean, default=False)
    insufficient_trades = Column(Boolean, default=False)

    # Component scores
    health_factors = Column(JSON, nullable=True)  # {"sharpe": 85, "win_rate": 90, "drawdown": 80}

    # Notes
    notes = Column(String, nullable=True)
    auto_paused = Column(Boolean, default=False)


class PortfolioRiskSnapshot(Base):
    """
    Portfolio-level risk snapshot.

    Phase 11: Portfolio Risk Engine
    Stores aggregated risk metrics across all active strategies.
    """
    __tablename__ = "portfolio_risk_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Portfolio composition
    total_strategies = Column(Integer, nullable=False)
    active_strategies = Column(Integer, nullable=False)
    total_allocation_pct = Column(Float, nullable=False)

    # Risk metrics
    portfolio_var = Column(Float, nullable=True)  # Portfolio Value at Risk
    portfolio_cvar = Column(Float, nullable=True)  # Conditional VaR
    portfolio_volatility = Column(Float, nullable=True)  # Portfolio volatility
    portfolio_sharpe = Column(Float, nullable=True)  # Portfolio Sharpe ratio

    # Drawdown
    current_drawdown_pct = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)

    # Leverage
    current_leverage = Column(Float, default=1.0)
    recommended_leverage = Column(Float, default=1.0)

    # Risk budget
    risk_budget_used = Column(Float, default=0.0)  # 0-100
    risk_budget_available = Column(Float, default=100.0)

    # Flags
    is_halted = Column(Boolean, default=False)
    halt_reason = Column(String, nullable=True)

    # Strategy contributions (JSON array)
    strategy_risks = Column(JSON, nullable=True)  # List of strategy risk metrics
