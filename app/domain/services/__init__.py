"""
Domain Services

Domain services implement complex business logic that doesn't naturally belong
to a single entity. Services orchestrate multiple entities and use port interfaces
to interact with infrastructure.

Services in this package:
- SignalProcessingService: Signal validation, routing, and execution orchestration
- RiskManagementService: Position sizing, exposure limits, margin calculations
- TradingService: Order lifecycle management, position tracking
- AccountService: Balance management, account state validation

Design Principles:
- Services operate on multiple entities or perform complex workflows
- Services depend only on ports (interfaces), never concrete infrastructure
- Services enforce cross-entity business rules
- Services are stateless (state lives in entities or is persisted via repositories)
- Services can call other domain services
"""

from app.domain.services.symbol_normalization_service import SymbolNormalizationService
from app.domain.services.futures_contract_service import FuturesContractService
from app.domain.services.contract_tracker import ContractTracker
from app.domain.services.routing_service import (
    RoutingEngine,
    RoutingConfig,
    RoutingRule,
    RoutingCondition,
    RoutingStrategy,
    RoutingOperator,
    build_signal_data,
)
from app.domain.services.daily_counter_service import (
    DailyCounters,
    DailyCounterService,
    DailyCounterRepository,
)
from app.domain.services.risk_enforcement_service import (
    RiskEnforcementService,
    RiskEvaluation,
    RiskViolation,
    RiskCheckResult,
    AccountRiskSettings,
)
from app.domain.services.position_sizing_service import (
    PositionSizingService,
    PositionSizingConfig,
    PositionSizingMode,
    SymbolSpecs,
    PositionSizeResult,
)
from app.domain.services.symbol_specs_service import SymbolSpecsService

__all__ = [
    "SymbolNormalizationService",
    "FuturesContractService",
    "ContractTracker",
    "RoutingEngine",
    "RoutingConfig",
    "RoutingRule",
    "RoutingCondition",
    "RoutingStrategy",
    "RoutingOperator",
    "build_signal_data",
    # Risk management
    "DailyCounters",
    "DailyCounterService",
    "DailyCounterRepository",
    "RiskEnforcementService",
    "RiskEvaluation",
    "RiskViolation",
    "RiskCheckResult",
    "AccountRiskSettings",
    # Position sizing
    "PositionSizingService",
    "PositionSizingConfig",
    "PositionSizingMode",
    "SymbolSpecs",
    "PositionSizeResult",
    "SymbolSpecsService",
]
