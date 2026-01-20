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

__all__ = []
