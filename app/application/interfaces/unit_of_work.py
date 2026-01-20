"""
Unit of Work Interface

Provides transaction management abstraction for the application layer.
Infrastructure layer will implement this with SQLAlchemy sessions.
"""
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.ports.repository_port import (
    SignalRepository,
    TradeRepository,
    OrderRepository,
    AccountRepository,
    PositionRepository,
)


class UnitOfWork(ABC):
    """
    Unit of Work pattern for transaction management.

    Provides:
    - Access to repositories within a transaction
    - Commit/rollback semantics
    - Context manager for automatic cleanup

    Usage:
        async with unit_of_work:
            signal = await unit_of_work.signals.get_by_id(signal_id)
            signal.mark_processed()
            await unit_of_work.signals.save(signal)
            await unit_of_work.commit()
    """

    signals: SignalRepository
    trades: TradeRepository
    orders: OrderRepository
    accounts: AccountRepository
    positions: PositionRepository

    async def __aenter__(self) -> "UnitOfWork":
        """Enter transaction context"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit transaction context, rollback on exception"""
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction"""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction"""
        pass


class UnitOfWorkFactory(ABC):
    """
    Factory for creating Unit of Work instances.

    Allows use cases to obtain new UoW instances without
    knowing the concrete implementation.
    """

    @abstractmethod
    def create(self) -> UnitOfWork:
        """Create a new Unit of Work instance"""
        pass
