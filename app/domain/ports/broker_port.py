"""
Broker Port Interface

Abstract interface for broker operations in hexagonal architecture.
Adapters (MT4Adapter, TradeLockerAdapter, etc.) implement this interface.
Domain services depend on this interface, not concrete implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from app.domain.entities.order import Order
from app.domain.entities.position import Position
from app.domain.entities.trade import Trade
from app.domain.value_objects import Symbol, Volume, Price, OrderId, PositionId
from app.domain.enums import OrderType, BrokerType


class BrokerPort(ABC):
    """
    Port interface for broker operations.

    Adapters (MT4Adapter, TradeLockerAdapter, etc.) implement this interface.
    Domain services depend on this interface, not concrete implementations.
    """

    @property
    @abstractmethod
    def broker_type(self) -> BrokerType:
        """Return the broker type this adapter handles"""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to broker.
        Returns True if connection successful.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close broker connection"""
        pass

    @abstractmethod
    async def is_connected(self) -> bool:
        """Check if broker connection is active"""
        pass

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with broker using provided credentials.
        Returns True if authentication successful.
        """
        pass

    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.
        Returns dict with: balance, equity, margin, free_margin, leverage, currency
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get all open positions.
        Returns list of Position domain entities.
        """
        pass

    @abstractmethod
    async def get_orders(self) -> List[Order]:
        """
        Get all pending orders.
        Returns list of Order domain entities.
        """
        pass

    @abstractmethod
    async def place_order(
        self,
        symbol: Symbol,
        order_type: OrderType,
        volume: Volume,
        price: Optional[Price] = None,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
        comment: Optional[str] = None,
    ) -> Order:
        """
        Place a new order.
        Returns the created Order domain entity.
        Raises: InvalidOrderError, InsufficientBalanceError, BrokerConnectionError
        """
        pass

    @abstractmethod
    async def modify_order(
        self,
        order_id: OrderId,
        price: Optional[Price] = None,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
    ) -> Order:
        """
        Modify an existing pending order.
        Returns updated Order domain entity.
        Raises: OrderNotFoundError, BusinessRuleViolation
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: OrderId) -> None:
        """
        Cancel a pending order.
        Raises: OrderNotFoundError, BusinessRuleViolation
        """
        pass

    @abstractmethod
    async def close_position(
        self,
        position_id: PositionId,
        volume: Optional[Volume] = None,
    ) -> Trade:
        """
        Close a position (fully or partially).
        Returns the resulting Trade domain entity.
        Raises: PositionNotFoundError, BusinessRuleViolation
        """
        pass

    @abstractmethod
    async def modify_position(
        self,
        position_id: PositionId,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
    ) -> Position:
        """
        Modify position stop loss / take profit.
        Returns updated Position domain entity.
        Raises: PositionNotFoundError, BusinessRuleViolation
        """
        pass

    @abstractmethod
    async def get_quote(self, symbol: Symbol) -> Dict[str, Any]:
        """
        Get current market quote.
        Returns dict with: symbol, bid, ask, timestamp
        """
        pass
