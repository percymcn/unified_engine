"""
Trade Domain Entity

Tracks trade lifecycle including opening, closing, partial closes,
and profit/loss calculations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal

from app.domain.enums import OrderType, TradeStatus
from app.domain.value_objects import Symbol, Volume, Price, Money
from app.domain.exceptions import ValidationError, BusinessRuleViolation


@dataclass
class Trade:
    """
    Domain entity representing an executed trade.

    A trade is created when an order is filled.
    Tracks P&L and lifecycle.
    """
    trade_id: str
    broker_trade_id: Optional[str]
    account_id: str
    symbol: Symbol
    order_type: OrderType
    volume: Volume
    open_price: Price
    open_time: datetime
    status: TradeStatus = TradeStatus.OPEN
    close_price: Optional[Price] = None
    close_time: Optional[datetime] = None
    stop_loss: Optional[Price] = None
    take_profit: Optional[Price] = None
    commission: Money = field(default_factory=lambda: Money(Decimal("0")))
    swap: Money = field(default_factory=lambda: Money(Decimal("0")))
    realized_pnl: Money = field(default_factory=lambda: Money(Decimal("0")))
    comment: Optional[str] = None
    magic_number: Optional[int] = None

    def close(self, close_price: Price, close_time: Optional[datetime] = None) -> None:
        """Close the trade at given price"""
        if self.status != TradeStatus.OPEN:
            raise BusinessRuleViolation(
                "cannot_close_trade",
                f"Cannot close trade in {self.status} status"
            )

        self.close_price = close_price
        self.close_time = close_time or datetime.utcnow()
        self.status = TradeStatus.CLOSED
        self._calculate_pnl()

    def partial_close(self, close_volume: Volume, close_price: Price) -> "Trade":
        """
        Partially close the trade.
        Returns a new Trade representing the closed portion.
        """
        if self.status != TradeStatus.OPEN:
            raise BusinessRuleViolation(
                "cannot_partial_close_trade",
                f"Cannot partial close trade in {self.status} status"
            )

        if close_volume.value >= self.volume.value:
            raise ValidationError("Partial close volume must be less than trade volume")

        # Create closed portion
        closed_trade = Trade(
            trade_id=f"{self.trade_id}-partial",
            broker_trade_id=self.broker_trade_id,
            account_id=self.account_id,
            symbol=self.symbol,
            order_type=self.order_type,
            volume=close_volume,
            open_price=self.open_price,
            open_time=self.open_time,
            close_price=close_price,
            close_time=datetime.utcnow(),
            status=TradeStatus.CLOSED,
        )
        closed_trade._calculate_pnl()

        # Update remaining volume
        remaining = Decimal(str(self.volume.value)) - Decimal(str(close_volume.value))
        self.volume = Volume(remaining)
        self.status = TradeStatus.PARTIALLY_CLOSED

        return closed_trade

    def update_sl_tp(self, stop_loss: Optional[Price] = None, take_profit: Optional[Price] = None) -> None:
        """Update stop loss and/or take profit levels"""
        if self.status != TradeStatus.OPEN:
            raise BusinessRuleViolation(
                "cannot_modify_closed_trade",
                "Cannot modify closed trade"
            )

        if stop_loss:
            self.stop_loss = stop_loss
        if take_profit:
            self.take_profit = take_profit

    def _calculate_pnl(self) -> None:
        """Calculate realized P&L"""
        if not self.close_price:
            return

        price_diff = self.close_price.value - self.open_price.value
        if self.order_type == OrderType.SELL:
            price_diff = -price_diff

        # Simplified P&L (actual would need pip value, lot size)
        pnl = price_diff * self.volume.value
        self.realized_pnl = Money(pnl - self.commission.amount - self.swap.amount)

    @property
    def is_open(self) -> bool:
        return self.status == TradeStatus.OPEN

    @property
    def is_closed(self) -> bool:
        return self.status == TradeStatus.CLOSED

    @property
    def is_profitable(self) -> bool:
        return self.realized_pnl.amount > 0
