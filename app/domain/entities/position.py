"""
Position Domain Entity

Tracks open trading positions with unrealized P&L and risk management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal

from app.domain.enums import OrderType, PositionSide
from app.domain.value_objects import PositionId, Symbol, Volume, Price, Money
from app.domain.exceptions import ValidationError, BusinessRuleViolation


@dataclass
class Position:
    """
    Domain entity representing an open position.

    Tracks unrealized P&L, manages position modifications.
    """
    id: PositionId
    broker_position_id: Optional[str]
    account_id: str
    symbol: Symbol
    side: PositionSide
    volume: Volume
    open_price: Price
    current_price: Price
    open_time: datetime
    stop_loss: Optional[Price] = None
    take_profit: Optional[Price] = None
    margin: Money = field(default_factory=lambda: Money(Decimal("0")))
    swap: Money = field(default_factory=lambda: Money(Decimal("0")))
    commission: Money = field(default_factory=lambda: Money(Decimal("0")))
    comment: Optional[str] = None
    magic_number: Optional[int] = None
    is_active: bool = True

    @property
    def unrealized_pnl(self) -> Decimal:
        """Calculate unrealized P&L based on current price (can be negative for losses)"""
        price_diff = self.current_price.value - self.open_price.value
        if self.side == PositionSide.SHORT:
            price_diff = -price_diff

        # Simplified P&L calculation
        pnl = price_diff * self.volume.value
        total = pnl - self.commission.amount + self.swap.amount
        return total

    def update_price(self, new_price: Price) -> None:
        """Update current market price"""
        object.__setattr__(self, 'current_price', new_price)

    def update_sl_tp(self, stop_loss: Optional[Price] = None, take_profit: Optional[Price] = None) -> None:
        """Modify stop loss and/or take profit"""
        if not self.is_active:
            raise BusinessRuleViolation("cannot_modify_closed_position", "Cannot modify closed position")

        if stop_loss:
            self._validate_stop_loss(stop_loss)
            object.__setattr__(self, 'stop_loss', stop_loss)
        if take_profit:
            self._validate_take_profit(take_profit)
            object.__setattr__(self, 'take_profit', take_profit)

    def _validate_stop_loss(self, sl: Price) -> None:
        """Validate stop loss is on correct side"""
        if self.side == PositionSide.LONG:
            if sl.value >= self.current_price.value:
                raise ValidationError("Stop loss must be below current price for LONG")
        else:
            if sl.value <= self.current_price.value:
                raise ValidationError("Stop loss must be above current price for SHORT")

    def _validate_take_profit(self, tp: Price) -> None:
        """Validate take profit is on correct side"""
        if self.side == PositionSide.LONG:
            if tp.value <= self.current_price.value:
                raise ValidationError("Take profit must be above current price for LONG")
        else:
            if tp.value >= self.current_price.value:
                raise ValidationError("Take profit must be below current price for SHORT")

    def partial_close(self, close_volume: Volume) -> Volume:
        """
        Reduce position size.
        Returns the remaining volume.
        """
        if not self.is_active:
            raise BusinessRuleViolation("cannot_close_inactive", "Cannot close inactive position")

        if close_volume.value >= self.volume.value:
            raise ValidationError("Close volume must be less than position volume")

        remaining = self.volume.value - close_volume.value
        object.__setattr__(self, 'volume', Volume(remaining))
        return Volume(remaining)

    def close(self) -> None:
        """Close the position completely"""
        if not self.is_active:
            raise BusinessRuleViolation("position_already_closed", "Position already closed")
        object.__setattr__(self, 'is_active', False)

    def add_to_position(self, additional_volume: Volume, price: Price) -> None:
        """
        Add to existing position (average price recalculated).
        """
        if not self.is_active:
            raise BusinessRuleViolation("cannot_add_to_closed", "Cannot add to closed position")

        # Calculate new average price
        total_value = (self.open_price.value * self.volume.value) + (price.value * additional_volume.value)
        new_volume = self.volume.value + additional_volume.value
        new_avg_price = total_value / new_volume

        object.__setattr__(self, 'volume', Volume(new_volume))
        object.__setattr__(self, 'open_price', Price(new_avg_price))

    @property
    def is_profitable(self) -> bool:
        return self.unrealized_pnl > 0

    @property
    def is_at_stop_loss(self) -> bool:
        if not self.stop_loss:
            return False
        if self.side == PositionSide.LONG:
            return self.current_price.value <= self.stop_loss.value
        return self.current_price.value >= self.stop_loss.value

    @property
    def is_at_take_profit(self) -> bool:
        if not self.take_profit:
            return False
        if self.side == PositionSide.LONG:
            return self.current_price.value >= self.take_profit.value
        return self.current_price.value <= self.take_profit.value
