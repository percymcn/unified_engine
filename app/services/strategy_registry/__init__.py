"""
Strategy Registry - Phase 6
============================

Core strategy registry system for SmartFlow.

This module provides:
1. Strategy registry (CRUD for strategies and variants)
2. Variant generator (create parameterized variants)
3. Strategy evaluator (backtest-based evaluation)
4. Promotion engine (approval/rejection workflow)

Phase 6 MVP Scope: 6A-6D (core system, no router integration or UI yet)
"""

from app.services.strategy_registry.registry import StrategyRegistry, get_strategy_registry
from app.services.strategy_registry.variant_generator import VariantGenerator, get_variant_generator
from app.services.strategy_registry.evaluator import StrategyEvaluator, get_strategy_evaluator
from app.services.strategy_registry.forward_test_gate import ForwardTestGate, get_forward_test_gate, ForwardTestGateDecision, GateCriteriaResult
from app.services.strategy_registry.health import StrategyHealthMonitor, get_health_monitor, HealthScore, HealthStatus, DriftMetrics, should_exclude_from_allocation
from app.services.strategy_registry.portfolio_risk import PortfolioRiskEngine, get_portfolio_risk_engine, PortfolioRiskConfig, PortfolioRiskSnapshot, StrategyRiskMetrics
from app.services.strategy_registry.execution_quality import ExecutionQualityTracker, get_execution_tracker, ExecutionMetrics, StrategyExecutionQuality, ExecutionStatus
from app.services.strategy_registry.walk_forward import WalkForwardLab, get_walk_forward_lab, WalkForwardResults, WalkForwardWindow
from app.services.strategy_registry.schemas import (
    StrategyStatus,
    StrategyType,
    StrategyCreate,
    VariantGenerateRequest,
    VariantGenerateResponse,
    EvaluationRequest,
    EvaluationResponse,
    PromotionRequest,
    RejectionRequest,
    StrategyResponse,
)

__all__ = [
    "StrategyRegistry",
    "get_strategy_registry",
    "VariantGenerator",
    "get_variant_generator",
    "StrategyEvaluator",
    "get_strategy_evaluator",
    "ForwardTestGate",
    "get_forward_test_gate",
    "ForwardTestGateDecision",
    "GateCriteriaResult",
    "StrategyHealthMonitor",
    "get_health_monitor",
    "HealthScore",
    "HealthStatus",
    "DriftMetrics",
    "should_exclude_from_allocation",
    "PortfolioRiskEngine",
    "get_portfolio_risk_engine",
    "PortfolioRiskConfig",
    "PortfolioRiskSnapshot",
    "StrategyRiskMetrics",
    "ExecutionQualityTracker",
    "get_execution_tracker",
    "ExecutionMetrics",
    "StrategyExecutionQuality",
    "ExecutionStatus",
    "WalkForwardLab",
    "get_walk_forward_lab",
    "WalkForwardResults",
    "WalkForwardWindow",
    "StrategyStatus",
    "StrategyType",
    "StrategyCreate",
    "VariantGenerateRequest",
    "VariantGenerateResponse",
    "EvaluationRequest",
    "EvaluationResponse",
    "PromotionRequest",
    "RejectionRequest",
    "StrategyResponse",
]
