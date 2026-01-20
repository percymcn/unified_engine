"""
Domain Value Objects

Immutable value objects for the domain layer using frozen dataclasses.
All validation uses only domain exceptions - no framework dependencies.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.domain.exceptions import ValidationError


@dataclass(frozen=True)
class Money:
    """
    Represents monetary value with currency.

    Immutable value object that ensures currency consistency in operations.
    Uses Decimal for precise financial calculations.
    """
    amount: Decimal
    currency: str = "USD"

    def __post_init__(self):
        if self.amount < 0:
            raise ValidationError(
                "Money amount cannot be negative",
                field="amount",
                context={"amount": self.amount}
            )
        if len(self.currency) != 3:
            raise ValidationError(
                "Currency must be 3-letter ISO code",
                field="currency",
                context={"currency": self.currency}
            )
        # Normalize currency to uppercase
        object.__setattr__(self, 'currency', self.currency.upper())

    def __add__(self, other: "Money") -> "Money":
        """Add two Money values (must be same currency)"""
        if self.currency != other.currency:
            raise ValidationError(
                f"Cannot add different currencies: {self.currency} + {other.currency}",
                context={"self_currency": self.currency, "other_currency": other.currency}
            )
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        """Subtract two Money values (must be same currency)"""
        if self.currency != other.currency:
            raise ValidationError(
                f"Cannot subtract different currencies: {self.currency} - {other.currency}",
                context={"self_currency": self.currency, "other_currency": other.currency}
            )
        return Money(self.amount - other.amount, self.currency)


@dataclass(frozen=True)
class Volume:
    """
    Trading volume/quantity.

    Represents the size of a position or order.
    Must be positive (cannot trade zero or negative volume).
    """
    value: Decimal

    def __post_init__(self):
        if self.value <= 0:
            raise ValidationError(
                "Volume must be positive",
                field="value",
                context={"value": self.value}
            )


@dataclass(frozen=True)
class Price:
    """
    Market price for an instrument.

    Cannot be negative. Uses Decimal for precision.
    """
    value: Decimal

    def __post_init__(self):
        if self.value < 0:
            raise ValidationError(
                "Price cannot be negative",
                field="value",
                context={"value": self.value}
            )


@dataclass(frozen=True)
class Symbol:
    """
    Trading symbol/instrument identifier.

    Normalized to uppercase for consistency.
    Examples: EURUSD, NQ, BTCUSD
    """
    value: str

    def __post_init__(self):
        if not self.value or len(self.value) > 20:
            raise ValidationError(
                "Symbol must be between 1 and 20 characters",
                field="value",
                context={"value": self.value, "length": len(self.value) if self.value else 0}
            )
        # Normalize to uppercase
        object.__setattr__(self, 'value', self.value.upper())


@dataclass(frozen=True)
class AccountId:
    """
    Unique account identifier.

    Identifies a specific trading account within the system.
    """
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValidationError(
                "Account ID cannot be empty",
                field="value"
            )


@dataclass(frozen=True)
class SignalId:
    """
    Unique signal identifier.

    Identifies a specific trading signal within the system.
    """
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValidationError(
                "Signal ID cannot be empty",
                field="value"
            )


@dataclass(frozen=True)
class OrderId:
    """
    Unique order identifier.

    Identifies a specific order within the system.
    """
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValidationError(
                "Order ID cannot be empty",
                field="value"
            )


@dataclass(frozen=True)
class PositionId:
    """
    Unique position identifier.

    Identifies a specific position within the system.
    """
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValidationError(
                "Position ID cannot be empty",
                field="value"
            )


@dataclass(frozen=True)
class StopLoss:
    """
    Stop loss price level.

    Defines the price at which a position should be closed to limit losses.
    """
    price: Price


@dataclass(frozen=True)
class TakeProfit:
    """
    Take profit price level.

    Defines the price at which a position should be closed to lock in profits.
    """
    price: Price
