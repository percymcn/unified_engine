"""
PositionRepository Implementation - SQLAlchemy-based persistence.

Implements PositionRepository port interface using SQLAlchemy for database operations.
Handles CRUD operations and queries for Position entities.
"""

from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.repository_port import PositionRepository
from app.domain.entities.position import Position
from app.domain.value_objects import PositionId, Symbol
from app.models.database_models import Position as PositionORM, PositionStatus
from app.infrastructure.mappers import PositionMapper


class SQLAlchemyPositionRepository(PositionRepository):
    """
    SQLAlchemy implementation of PositionRepository port.

    Provides persistence for Position entities using PostgreSQL.
    Uses PositionMapper for ORM ↔ domain conversion.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations
        """
        self._session = session
        self._mapper = PositionMapper()

    async def save(self, position: Position) -> Position:
        """
        Persist position entity (create or update).

        Args:
            position: Domain Position entity

        Returns:
            Persisted Position entity with updated ID
        """
        # Check if position exists
        stmt = select(PositionORM).where(PositionORM.id == int(position.id.value))
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing position
            orm_model = self._mapper.to_model(position, existing)
        else:
            # Create new position
            orm_model = self._mapper.to_model(position)
            self._session.add(orm_model)

        await self._session.flush()
        await self._session.refresh(orm_model)

        return self._mapper.to_entity(orm_model)

    async def delete(self, position: Position) -> None:
        """
        Delete position entity.

        Args:
            position: Domain Position entity to delete
        """
        stmt = select(PositionORM).where(PositionORM.id == int(position.id.value))
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            await self._session.delete(orm_model)
            await self._session.flush()

    async def get_by_id(self, position_id: PositionId) -> Optional[Position]:
        """
        Get position by ID.

        Args:
            position_id: Domain PositionId value object

        Returns:
            Position entity if found, None otherwise
        """
        stmt = select(PositionORM).where(PositionORM.id == int(position_id.value))
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            return self._mapper.to_entity(orm_model)
        return None

    async def get_open_by_account(self, account_id: str) -> List[Position]:
        """
        Get open positions for an account.

        Args:
            account_id: Account ID as string

        Returns:
            List of open Position entities
        """
        stmt = (
            select(PositionORM)
            .where(
                and_(
                    PositionORM.account_id == int(account_id),
                    PositionORM.status == PositionStatus.OPEN
                )
            )
            .order_by(PositionORM.opened_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]

    async def get_by_symbol(self, account_id: str, symbol: str) -> List[Position]:
        """
        Get positions by symbol for an account.

        Args:
            account_id: Account ID as string
            symbol: Trading symbol

        Returns:
            List of Position entities for the symbol
        """
        stmt = (
            select(PositionORM)
            .where(
                and_(
                    PositionORM.account_id == int(account_id),
                    PositionORM.symbol == symbol
                )
            )
            .order_by(PositionORM.opened_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]
