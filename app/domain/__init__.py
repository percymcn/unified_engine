"""
Domain Layer - Hexagonal Architecture

This package contains the pure business logic of the Unified Trading Engine.
The domain layer is completely isolated from infrastructure concerns.

Design Principles:
- No FastAPI, SQLAlchemy, or infrastructure framework imports allowed
- Contains only pure Python business logic
- Defines port interfaces for infrastructure adapters
- Implements domain entities with rich behavior
- Enforces business rules and invariants

Structure:
- entities/: Domain entities (Signal, Trade, Account, Position, Order)
- ports/: Port interfaces (abstract base classes for adapters)
- services/: Domain services for complex business logic
- exceptions.py: Domain-specific exception hierarchy

The domain layer is the heart of the application and must remain
framework-independent to ensure testability and maintainability.
"""

from app.domain.exceptions import (
    DomainException,
    ValidationError,
    EntityNotFoundError,
    BusinessRuleViolation,
    SignalValidationError,
    SignalProcessingError,
    DuplicateSignalError,
    InsufficientBalanceError,
    InvalidOrderError,
    PositionNotFoundError,
    OrderNotFoundError,
    AccountNotFoundError,
    AccountDisabledError,
    BrokerConnectionError,
)

__all__ = [
    # Base exceptions
    "DomainException",
    "ValidationError",
    "EntityNotFoundError",
    "BusinessRuleViolation",
    # Signal exceptions
    "SignalValidationError",
    "SignalProcessingError",
    "DuplicateSignalError",
    # Trading exceptions
    "InsufficientBalanceError",
    "InvalidOrderError",
    "PositionNotFoundError",
    "OrderNotFoundError",
    # Account exceptions
    "AccountNotFoundError",
    "AccountDisabledError",
    "BrokerConnectionError",
]
