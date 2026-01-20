"""
Order Domain Entity

Represents pending and executed orders with validation,
fill tracking, and lifecycle management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal

from app.domain.enums import OrderType, OrderStatus
from app.domain.value_objects import OrderId, Symbol, Volume, Price
from app.domain.exceptions import ValidationError, BusinessRuleViolation


@dataclass
class Order:
    """
    Domain entity representing a trading order.

    An order is an instruction to buy/sell at market or a specific price.
    """
    id: OrderId
    broker_order_id: Optional[str]
    account_id: str
    symbol: Symbol
    order_type: OrderType
    volume: Volume
    status: OrderStatus = OrderStatus.PENDING
    price: Optional[Price] = None  # For limit/stop orders
    stop_loss: Optional[Price] = None
    take_profit: Optional[Price] = None
    filled_volume: Decimal = field(default_factory=lambda: Decimal("0"))
    expire_time: Optional[datetime] = None
    comment: Optional[str] = None
    magic_number: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate order invariants"""
        # Limit/Stop orders require price
        if self.order_type in (OrderType.BUY_LIMIT, OrderType.SELL_LIMIT,
                                OrderType.BUY_STOP, OrderType.SELL_STOP):
            if self.price is None:
                raise ValidationError(f"{self.order_type} order requires price")

    def fill(self, filled_volume: Volume, fill_price: Price) -> None:
        """Record order fill"""
        if self.status not in (OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED):
            raise BusinessRuleViolation(
                "cannot_fill_order",
                f"Cannot fill order in {self.status} status"
            )

        new_filled = self.filled_volume + filled_volume.value

        if new_filled > self.volume.value:
            raise ValidationError("Fill volume exceeds order volume")

        self.filled_volume = new_filled
        self.updated_at = datetime.utcnow()

        if new_filled >= self.volume.value:
            self.status = OrderStatus.EXECUTED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> None:
        """Cancel the order"""
        if self.status == OrderStatus.EXECUTED:
            raise BusinessRuleViolation(
                "cannot_cancel_executed_order",
                "Cannot cancel executed order"
            )
        if self.status == OrderStatus.CANCELLED:
            raise BusinessRuleViolation(
                "order_already_cancelled",
                "Order already cancelled"
            )

        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.utcnow()

    def reject(self, reason: str) -> None:
        """Reject the order"""
        if self.status != OrderStatus.PENDING:
            raise BusinessRuleViolation(
                "cannot_reject_order",
                f"Cannot reject order in {self.status} status"
            )

        self.status = OrderStatus.REJECTED
        self.comment = reason
        self.updated_at = datetime.utcnow()

    def modify(self, price: Optional[Price] = None,
               stop_loss: Optional[Price] = None,
               take_profit: Optional[Price] = None) -> None:
        """Modify pending order"""
        if self.status != OrderStatus.PENDING:
            raise BusinessRuleViolation(
                "cannot_modify_non_pending_order",
                "Can only modify pending orders"
            )

        if price:
            self.price = price
        if stop_loss:
            self.stop_loss = stop_loss
        if take_profit:
            self.take_profit = take_profit
        self.updated_at = datetime.utcnow()

    @property
    def remaining_volume(self) -> Decimal:
        remaining = self.volume.value - self.filled_volume
        return remaining if remaining > 0 else Decimal("0")

    @property
    def is_pending(self) -> bool:
        return self.status == OrderStatus.PENDING

    @property
    def is_filled(self) -> bool:
        return self.status == OrderStatus.EXECUTED

    @property
    def is_market_order(self) -> bool:
        return self.order_type in (OrderType.BUY, OrderType.SELL)
