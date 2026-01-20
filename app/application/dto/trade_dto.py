"""
Trade DTOs - Input/Output contracts for trade use cases.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.domain.enums import OrderType, OrderStatus, TradeStatus


@dataclass(frozen=True)
class PlaceOrderRequest:
    """Input DTO for placing an order"""
    account_id: str
    symbol: str
    order_type: OrderType
    volume: Decimal
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    comment: Optional[str] = None

    def __post_init__(self):
        if not self.account_id:
            raise ValueError("Account ID is required")
        if not self.symbol:
            raise ValueError("Symbol is required")
        if self.volume <= 0:
            raise ValueError("Volume must be positive")
        # Limit/Stop orders require price
        if self.order_type in (OrderType.BUY_LIMIT, OrderType.SELL_LIMIT,
                                OrderType.BUY_STOP, OrderType.SELL_STOP):
            if self.price is None:
                raise ValueError(f"{self.order_type} order requires price")


@dataclass(frozen=True)
class PlaceOrderResponse:
    """Output DTO for order placement result"""
    order_id: str
    status: OrderStatus
    broker_order_id: Optional[str] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class ClosePositionRequest:
    """Input DTO for closing a position"""
    account_id: str
    position_id: str
    volume: Optional[Decimal] = None  # None = close full position


@dataclass(frozen=True)
class ClosePositionResponse:
    """Output DTO for position close result"""
    trade_id: str
    realized_pnl: Decimal
    status: TradeStatus
    error: Optional[str] = None


@dataclass(frozen=True)
class ModifyPositionRequest:
    """Input DTO for modifying position SL/TP"""
    account_id: str
    position_id: str
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None


@dataclass(frozen=True)
class PositionDTO:
    """Read-only position representation"""
    id: str
    account_id: str
    symbol: str
    side: str  # LONG or SHORT
    volume: Decimal
    open_price: Decimal
    current_price: Decimal
    unrealized_pnl: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    open_time: Optional[datetime] = None


@dataclass(frozen=True)
class TradeDTO:
    """Read-only trade representation"""
    trade_id: str
    account_id: str
    symbol: str
    order_type: OrderType
    volume: Decimal
    open_price: Decimal
    close_price: Optional[Decimal] = None
    realized_pnl: Decimal = Decimal("0")
    status: TradeStatus = TradeStatus.OPEN
    open_time: Optional[datetime] = None
    close_time: Optional[datetime] = None


@dataclass(frozen=True)
class TradeListRequest:
    """Request for listing trades"""
    account_id: str
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class TradeListResponse:
    """Response containing trade list"""
    trades: List[TradeDTO]
    total: int
