"""
Domain Exceptions

This module defines the exception hierarchy for the domain layer.
All exceptions are framework-independent and contain only pure Python.

Exception Hierarchy:
- DomainException (base)
  - ValidationError: Invalid domain state or input
  - EntityNotFoundError: Entity lookup failed
  - BusinessRuleViolation: Business rule constraint violated

Signal Exceptions:
- SignalValidationError: Invalid signal data
- SignalProcessingError: Signal processing failed
- DuplicateSignalError: Signal already processed

Trading Exceptions:
- InsufficientBalanceError: Not enough funds
- InvalidOrderError: Order validation failed
- PositionNotFoundError: Position doesn't exist
- OrderNotFoundError: Order doesn't exist

Account Exceptions:
- AccountNotFoundError: Account doesn't exist
- AccountDisabledError: Account is inactive
- BrokerConnectionError: Broker communication failed
"""

from typing import Any, Dict, Optional


class DomainException(Exception):
    """Base exception for all domain layer errors"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        self.message = message
        self.context = context or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} ({context_str})"
        return self.message


class ValidationError(DomainException):
    """Raised when domain state or input validation fails"""

    def __init__(self, message: str, field: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        if field:
            ctx["field"] = field
        super().__init__(message, ctx)


class EntityNotFoundError(DomainException):
    """Raised when an entity lookup fails"""

    def __init__(self, entity_type: str, identifier: Any, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx["entity_type"] = entity_type
        ctx["identifier"] = identifier
        message = f"{entity_type} not found: {identifier}"
        super().__init__(message, ctx)


class BusinessRuleViolation(DomainException):
    """Raised when a business rule constraint is violated"""

    def __init__(self, rule: str, message: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx["rule"] = rule
        super().__init__(message, ctx)


# Signal Exceptions


class SignalValidationError(ValidationError):
    """Raised when signal data validation fails"""

    def __init__(self, message: str, signal_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        if signal_id:
            ctx["signal_id"] = signal_id
        super().__init__(message, context=ctx)


class SignalProcessingError(DomainException):
    """Raised when signal processing fails"""

    def __init__(self, message: str, signal_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        if signal_id:
            ctx["signal_id"] = signal_id
        super().__init__(message, ctx)


class DuplicateSignalError(BusinessRuleViolation):
    """Raised when attempting to process a duplicate signal"""

    def __init__(self, signal_id: str, context: Optional[Dict[str, Any]] = None):
        message = f"Signal already processed: {signal_id}"
        super().__init__("duplicate_signal", message, context)


# Trading Exceptions


class InsufficientBalanceError(BusinessRuleViolation):
    """Raised when account has insufficient funds for an operation"""

    def __init__(
        self,
        required: float,
        available: float,
        account_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        ctx = context or {}
        ctx["required"] = required
        ctx["available"] = available
        if account_id:
            ctx["account_id"] = account_id
        message = f"Insufficient balance: required {required}, available {available}"
        super().__init__("insufficient_balance", message, ctx)


class InvalidOrderError(ValidationError):
    """Raised when order validation fails"""

    def __init__(self, message: str, order_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        if order_id:
            ctx["order_id"] = order_id
        super().__init__(message, context=ctx)


class PositionNotFoundError(EntityNotFoundError):
    """Raised when a position is not found"""

    def __init__(self, position_id: str, context: Optional[Dict[str, Any]] = None):
        super().__init__("Position", position_id, context)


class OrderNotFoundError(EntityNotFoundError):
    """Raised when an order is not found"""

    def __init__(self, order_id: str, context: Optional[Dict[str, Any]] = None):
        super().__init__("Order", order_id, context)


# Account Exceptions


class AccountNotFoundError(EntityNotFoundError):
    """Raised when an account is not found"""

    def __init__(self, account_id: str, context: Optional[Dict[str, Any]] = None):
        super().__init__("Account", account_id, context)


class AccountDisabledError(BusinessRuleViolation):
    """Raised when attempting to use a disabled account"""

    def __init__(self, account_id: str, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        ctx["account_id"] = account_id
        message = f"Account is disabled: {account_id}"
        super().__init__("account_disabled", message, ctx)


class BrokerConnectionError(DomainException):
    """Raised when broker communication fails"""

    def __init__(
        self, broker: str, message: str, account_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None
    ):
        ctx = context or {}
        ctx["broker"] = broker
        if account_id:
            ctx["account_id"] = account_id
        full_message = f"Broker connection error ({broker}): {message}"
        super().__init__(full_message, ctx)
