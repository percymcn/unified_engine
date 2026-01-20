"""
SQLAlchemy Unit of Work Implementation

Provides transactional repository access for use cases.
All repositories share the same database session.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.unit_of_work import UnitOfWork, UnitOfWorkFactory
from app.domain.ports.repository_port import (
    SignalRepository,
    TradeRepository,
    OrderRepository,
    AccountRepository,
    PositionRepository,
)
from app.infrastructure.repositories.signal_repository import SQLAlchemySignalRepository
from app.infrastructure.repositories.trade_repository import SQLAlchemyTradeRepository
from app.infrastructure.repositories.order_repository import SQLAlchemyOrderRepository
from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository
from app.infrastructure.repositories.position_repository import SQLAlchemyPositionRepository
from app.infrastructure.persistence.session_factory import SessionFactory


class SQLAlchemyUnitOfWork(UnitOfWork):
    """
    SQLAlchemy implementation of Unit of Work pattern.

    Manages database session lifecycle and provides access to repositories
    within a transactional context. All repositories share the same session,
    ensuring operations are atomic.

    Usage:
        async with unit_of_work:
            signal = await unit_of_work.signals.get_by_id(signal_id)
            signal.mark_processed()
            await unit_of_work.signals.save(signal)
            await unit_of_work.commit()
    """

    def __init__(self, session_factory: SessionFactory):
        """
        Initialize Unit of Work with session factory.

        Args:
            session_factory: Factory for creating database sessions
        """
        self._session_factory = session_factory
        self._session: Optional[AsyncSession] = None

        # Repository instances (lazy-initialized)
        self._signals: Optional[SignalRepository] = None
        self._trades: Optional[TradeRepository] = None
        self._orders: Optional[OrderRepository] = None
        self._accounts: Optional[AccountRepository] = None
        self._positions: Optional[PositionRepository] = None

    async def __aenter__(self) -> "SQLAlchemyUnitOfWork":
        """
        Enter transaction context - create session and repositories.

        Returns:
            Self for context manager protocol
        """
        self._session = self._session_factory.create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit transaction context - cleanup on exception.

        Automatically rolls back if exception occurred, then closes session.

        Args:
            exc_type: Exception type if raised
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised
        """
        if exc_type is not None:
            await self.rollback()
        await self._session.close()

    @property
    def signals(self) -> SignalRepository:
        """
        Get signal repository (lazy-initialized).

        Returns:
            SignalRepository instance sharing this unit's session
        """
        if self._signals is None:
            self._signals = SQLAlchemySignalRepository(self._session)
        return self._signals

    @property
    def trades(self) -> TradeRepository:
        """
        Get trade repository (lazy-initialized).

        Returns:
            TradeRepository instance sharing this unit's session
        """
        if self._trades is None:
            self._trades = SQLAlchemyTradeRepository(self._session)
        return self._trades

    @property
    def orders(self) -> OrderRepository:
        """
        Get order repository (lazy-initialized).

        Returns:
            OrderRepository instance sharing this unit's session
        """
        if self._orders is None:
            self._orders = SQLAlchemyOrderRepository(self._session)
        return self._orders

    @property
    def accounts(self) -> AccountRepository:
        """
        Get account repository (lazy-initialized).

        Returns:
            AccountRepository instance sharing this unit's session
        """
        if self._accounts is None:
            self._accounts = SQLAlchemyAccountRepository(self._session)
        return self._accounts

    @property
    def positions(self) -> PositionRepository:
        """
        Get position repository (lazy-initialized).

        Returns:
            PositionRepository instance sharing this unit's session
        """
        if self._positions is None:
            self._positions = SQLAlchemyPositionRepository(self._session)
        return self._positions

    async def commit(self) -> None:
        """
        Commit all changes made in this transaction.

        Persists all modifications across all repositories.
        """
        await self._session.commit()

    async def rollback(self) -> None:
        """
        Rollback all changes made in this transaction.

        Reverts all modifications across all repositories.
        """
        await self._session.rollback()


class SQLAlchemyUnitOfWorkFactory(UnitOfWorkFactory):
    """
    Factory for creating SQLAlchemy Unit of Work instances.

    Allows use cases to obtain new UoW instances without knowing
    the concrete SQLAlchemy implementation details.
    """

    def __init__(self, session_factory: SessionFactory = None):
        """
        Initialize factory with session factory.

        Args:
            session_factory: Optional session factory. Defaults to new SessionFactory()
        """
        self._session_factory = session_factory or SessionFactory()

    def create(self) -> UnitOfWork:
        """
        Create a new Unit of Work instance.

        Returns:
            New SQLAlchemyUnitOfWork instance
        """
        return SQLAlchemyUnitOfWork(self._session_factory)
