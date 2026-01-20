"""
Repository Port Interfaces

Abstract repository interfaces for domain entities.
Adapters (SQLAlchemy implementations) will implement these in Phase 5.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Generic, TypeVar
from datetime import datetime

from app.domain.entities.signal import Signal
from app.domain.entities.trade import Trade
from app.domain.entities.order import Order
from app.domain.entities.account import Account
from app.domain.entities.position import Position
from app.domain.value_objects import SignalId, OrderId, PositionId, AccountId
from app.domain.enums import SignalStatus, OrderStatus, BrokerType


T = TypeVar('T')


class Repository(ABC, Generic[T]):
    """Base repository interface with common CRUD operations"""

    @abstractmethod
    async def save(self, entity: T) -> T:
        """Persist entity (create or update)"""
        pass

    @abstractmethod
    async def delete(self, entity: T) -> None:
        """Delete entity"""
        pass


class SignalRepository(Repository[Signal]):
    """Repository interface for Signal entities"""

    @abstractmethod
    async def get_by_id(self, signal_id: SignalId) -> Optional[Signal]:
        """Get signal by ID"""
        pass

    @abstractmethod
    async def get_pending(self, limit: int = 100) -> List[Signal]:
        """Get pending signals for processing"""
        pass

    @abstractmethod
    async def get_by_status(self, status: SignalStatus, limit: int = 100) -> List[Signal]:
        """Get signals by status"""
        pass

    @abstractmethod
    async def get_by_user(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Signal]:
        """Get signals for a user"""
        pass

    @abstractmethod
    async def get_recent(self, since: datetime, limit: int = 100) -> List[Signal]:
        """Get signals since a datetime"""
        pass


class TradeRepository(Repository[Trade]):
    """Repository interface for Trade entities"""

    @abstractmethod
    async def get_by_id(self, trade_id: str) -> Optional[Trade]:
        """Get trade by ID"""
        pass

    @abstractmethod
    async def get_by_account(self, account_id: str, limit: int = 100, offset: int = 0) -> List[Trade]:
        """Get trades for an account"""
        pass

    @abstractmethod
    async def get_open_by_account(self, account_id: str) -> List[Trade]:
        """Get open trades for an account"""
        pass

    @abstractmethod
    async def get_by_symbol(self, account_id: str, symbol: str) -> List[Trade]:
        """Get trades by symbol for an account"""
        pass


class OrderRepository(Repository[Order]):
    """Repository interface for Order entities"""

    @abstractmethod
    async def get_by_id(self, order_id: OrderId) -> Optional[Order]:
        """Get order by ID"""
        pass

    @abstractmethod
    async def get_pending_by_account(self, account_id: str) -> List[Order]:
        """Get pending orders for an account"""
        pass

    @abstractmethod
    async def get_by_status(self, account_id: str, status: OrderStatus) -> List[Order]:
        """Get orders by status for an account"""
        pass


class AccountRepository(Repository[Account]):
    """Repository interface for Account entities"""

    @abstractmethod
    async def get_by_id(self, account_id: AccountId) -> Optional[Account]:
        """Get account by ID"""
        pass

    @abstractmethod
    async def get_by_user(self, user_id: int) -> List[Account]:
        """Get accounts for a user"""
        pass

    @abstractmethod
    async def get_by_broker(self, broker: BrokerType) -> List[Account]:
        """Get accounts by broker type"""
        pass

    @abstractmethod
    async def get_active(self) -> List[Account]:
        """Get all active accounts"""
        pass

    @abstractmethod
    async def get_connected(self) -> List[Account]:
        """Get all connected accounts"""
        pass


class PositionRepository(Repository[Position]):
    """Repository interface for Position entities"""

    @abstractmethod
    async def get_by_id(self, position_id: PositionId) -> Optional[Position]:
        """Get position by ID"""
        pass

    @abstractmethod
    async def get_open_by_account(self, account_id: str) -> List[Position]:
        """Get open positions for an account"""
        pass

    @abstractmethod
    async def get_by_symbol(self, account_id: str, symbol: str) -> List[Position]:
        """Get positions by symbol for an account"""
        pass
