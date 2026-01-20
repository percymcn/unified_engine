"""
TradeRepository Implementation - SQLAlchemy-based persistence.

Implements TradeRepository port interface using SQLAlchemy for database operations.
Handles CRUD operations and queries for Trade entities.
"""

from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.repository_port import TradeRepository
from app.domain.entities.trade import Trade
from app.models.database_models import Trade as TradeORM
from app.infrastructure.mappers import TradeMapper


class SQLAlchemyTradeRepository(TradeRepository):
    """
    SQLAlchemy implementation of TradeRepository port.

    Provides persistence for Trade entities using PostgreSQL.
    Uses TradeMapper for ORM ↔ domain conversion.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations
        """
        self._session = session
        self._mapper = TradeMapper()

    async def save(self, trade: Trade) -> Trade:
        """
        Persist trade entity (create or update).

        Args:
            trade: Domain Trade entity

        Returns:
            Persisted Trade entity with updated ID
        """
        # Check if trade exists
        stmt = select(TradeORM).where(TradeORM.id == int(trade.trade_id))
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing trade
            orm_model = self._mapper.to_model(trade, existing)
        else:
            # Create new trade
            orm_model = self._mapper.to_model(trade)
            self._session.add(orm_model)

        await self._session.flush()
        await self._session.refresh(orm_model)

        return self._mapper.to_entity(orm_model)

    async def delete(self, trade: Trade) -> None:
        """
        Delete trade entity.

        Args:
            trade: Domain Trade entity to delete
        """
        stmt = select(TradeORM).where(TradeORM.id == int(trade.trade_id))
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            await self._session.delete(orm_model)
            await self._session.flush()

    async def get_by_id(self, trade_id: str) -> Optional[Trade]:
        """
        Get trade by ID.

        Args:
            trade_id: Trade ID as string

        Returns:
            Trade entity if found, None otherwise
        """
        stmt = select(TradeORM).where(TradeORM.id == int(trade_id))
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            return self._mapper.to_entity(orm_model)
        return None

    async def get_by_account(self, account_id: str, limit: int = 100, offset: int = 0) -> List[Trade]:
        """
        Get trades for an account.

        Args:
            account_id: Account ID as string
            limit: Maximum number of trades to return
            offset: Number of trades to skip

        Returns:
            List of Trade entities for the account
        """
        stmt = (
            select(TradeORM)
            .where(TradeORM.account_id == int(account_id))
            .order_by(TradeORM.opened_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]

    async def get_open_by_account(self, account_id: str) -> List[Trade]:
        """
        Get open trades for an account.

        Args:
            account_id: Account ID as string

        Returns:
            List of open Trade entities
        """
        stmt = (
            select(TradeORM)
            .where(
                and_(
                    TradeORM.account_id == int(account_id),
                    TradeORM.closed_at.is_(None)
                )
            )
            .order_by(TradeORM.opened_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]

    async def get_by_symbol(self, account_id: str, symbol: str) -> List[Trade]:
        """
        Get trades by symbol for an account.

        Args:
            account_id: Account ID as string
            symbol: Trading symbol

        Returns:
            List of Trade entities for the symbol
        """
        stmt = (
            select(TradeORM)
            .where(
                and_(
                    TradeORM.account_id == int(account_id),
                    TradeORM.symbol == symbol
                )
            )
            .order_by(TradeORM.opened_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]
