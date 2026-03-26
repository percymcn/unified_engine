"""
Strategy Registry Schemas - Phase 6
====================================

Pydantic schemas for strategy registry API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum


class StrategyStatus(str, Enum):
    """
    Strategy lifecycle status.

    Phase 7 lifecycle flow:
    candidate → approved_for_forward_test → forward_testing → approved_for_router → active

    Router-eligible statuses: built_in, approved_for_router, active
    """
    BUILT_IN = "built_in"
    CANDIDATE = "candidate"
    APPROVED_FOR_FORWARD_TEST = "approved_for_forward_test"  # Phase 7: Passed backtest, ready for forward test
    FORWARD_TESTING = "forward_testing"  # Phase 7: Currently in forward test
    APPROVED_FOR_ROUTER = "approved_for_router"  # Phase 7: Passed forward-test gate
    ACTIVE = "active"  # Phase 7: Router-eligible and actively selected
    REJECTED = "rejected"
    RETIRED = "retired"
    ARCHIVED = "archived"  # Phase 7: Historical record


class StrategyType(str, Enum):
    """SmartFlow engine types."""
    UNIFIED = "unified"
    DETERMINISTIC = "deterministic"
    QUICK = "quick"
    FLOW = "flow"
    AI = "ai"


class StrategyCreate(BaseModel):
    """Create a new strategy (built-in or variant)."""
    strategy_id: str
    strategy_type: StrategyType
    version: str
    status: StrategyStatus
    parameters: Dict[str, Any]
    parent_strategy_id: Optional[str] = None
    parameter_changes: Optional[Dict[str, Any]] = None
    hypothesis: Optional[str] = None
    created_by: Optional[str] = None


class VariantGenerateRequest(BaseModel):
    """Request to generate a strategy variant."""
    parent_strategy_id: str
    parameter_changes: Dict[str, Any] = Field(..., description="Parameters to change from parent")
    hypothesis: Optional[str] = Field(None, description="Why this variant is being created")
    created_by: Optional[str] = None


class VariantGenerateResponse(BaseModel):
    """Response after generating a variant."""
    strategy_id: str
    strategy_type: str
    version: str
    status: str
    parameters: Dict[str, Any]
    parent_strategy_id: str
    parameter_changes: Dict[str, Any]
    hypothesis: Optional[str]
    created_at: datetime


class EvaluationRequest(BaseModel):
    """Request to evaluate a strategy."""
    strategy_id: str
    ticker: str = "MES"
    backtest_days: int = 90
    notes: Optional[str] = None
    evaluated_by: Optional[str] = None


class EvaluationCriteriaResult(BaseModel):
    """Result for a single evaluation criterion."""
    criterion: str
    passed: bool
    value: Optional[float] = None
    threshold: Optional[float] = None
    details: Optional[str] = None


class EvaluationResponse(BaseModel):
    """Response after evaluation."""
    evaluation_id: int
    strategy_id: str
    comparison_id: str
    ticker: str
    backtest_days: int

    # Performance
    sharpe_ratio: Optional[float]
    win_rate: Optional[float]
    max_drawdown: Optional[float]
    total_return_pct: Optional[float]
    total_trades: Optional[int]
    net_profit: Optional[float]

    # Criteria
    criteria_results: List[EvaluationCriteriaResult]
    passed: bool
    recommendation: str  # APPROVE or REJECT

    # Metadata
    evaluated_at: datetime
    notes: Optional[str]


class PromotionRequest(BaseModel):
    """Request to promote a candidate to approved status."""
    strategy_id: str
    approved_by: str = Field(..., description="Admin who approves")
    approval_notes: str = Field(..., description="Why this is being approved")


class RejectionRequest(BaseModel):
    """Request to reject a candidate."""
    strategy_id: str
    rejected_by: str = Field(..., description="Admin who rejects")
    rejection_notes: str = Field(..., description="Why this is being rejected")


class RetirementRequest(BaseModel):
    """Request to retire an approved strategy."""
    strategy_id: str
    retired_by: str
    retirement_reason: str


class StrategyResponse(BaseModel):
    """Strategy detail response."""
    id: int
    strategy_id: str
    strategy_type: str
    version: str
    status: str

    # Configuration
    parameters: Dict[str, Any]
    parent_strategy_id: Optional[str]
    parameter_changes: Optional[Dict[str, Any]]
    hypothesis: Optional[str]

    # Performance
    sharpe_ratio: Optional[float]
    win_rate: Optional[float]
    max_drawdown: Optional[float]
    total_return_pct: Optional[float]
    total_trades: Optional[int]
    backtest_days: Optional[int]

    # Metadata
    created_at: datetime
    created_by: Optional[str]
    evaluated_at: Optional[datetime]
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    approval_notes: Optional[str]
    rejected_at: Optional[datetime]
    rejected_by: Optional[str]
    rejection_notes: Optional[str]

    class Config:
        from_attributes = True


class StrategyListResponse(BaseModel):
    """List of strategies response."""
    strategies: List[StrategyResponse]
    total: int
    status_filter: Optional[str]
    type_filter: Optional[str]


class CandidateStats(BaseModel):
    """Statistics for candidates per base strategy."""
    parent_strategy_id: str
    active_candidates: int
    max_candidates: int
    can_create_more: bool
