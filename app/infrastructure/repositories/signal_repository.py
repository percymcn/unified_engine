"""
SignalRepository Implementation - SQLAlchemy-based persistence.

Implements SignalRepository port interface using SQLAlchemy for database operations.
Handles CRUD operations and queries for Signal entities.
"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.repository_port import SignalRepository
from app.domain.entities.signal import Signal
from app.domain.value_objects import SignalId
from app.domain.enums import SignalStatus
from app.models.database_models import Signal as SignalORM
from app.infrastructure.mappers import SignalMapper


class SQLAlchemySignalRepository(SignalRepository):
    """
    SQLAlchemy implementation of SignalRepository port.

    Provides persistence for Signal entities using PostgreSQL.
    Uses SignalMapper for ORM ↔ domain conversion.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations
        """
        self._session = session
        self._mapper = SignalMapper()

    def _is_new_signal(self, signal_id: SignalId) -> bool:
        """Check if signal ID is a new UUID (not yet persisted) vs existing integer."""
        try:
            int(signal_id.value)
            return False  # Valid integer = existing signal
        except ValueError:
            return True  # UUID string = new signal

    async def save(self, signal: Signal) -> Signal:
        """
        Persist signal entity (create or update).

        Args:
            signal: Domain Signal entity

        Returns:
            Persisted Signal entity with updated ID
        """
        if self._is_new_signal(signal.id):
            # New signal - create without lookup
            orm_model = self._mapper.to_model(signal)
            self._session.add(orm_model)
        else:
            # Existing signal - lookup by integer ID
            stmt = select(SignalORM).where(SignalORM.id == int(signal.id.value))
            result = await self._session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                orm_model = self._mapper.to_model(signal, existing)
            else:
                # ID looks like integer but not found - treat as new
                orm_model = self._mapper.to_model(signal)
                self._session.add(orm_model)

        await self._session.flush()
        await self._session.commit()  # Persist signal to database
        await self._session.refresh(orm_model)

        return self._mapper.to_entity(orm_model)

    async def delete(self, signal: Signal) -> None:
        """
        Delete signal entity.

        Args:
            signal: Domain Signal entity to delete
        """
        if self._is_new_signal(signal.id):
            return  # New signals don't exist in DB yet

        stmt = select(SignalORM).where(SignalORM.id == int(signal.id.value))
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            await self._session.delete(orm_model)
            await self._session.flush()

    async def get_by_id(self, signal_id: SignalId) -> Optional[Signal]:
        """
        Get signal by ID.

        Args:
            signal_id: Domain SignalId value object

        Returns:
            Signal entity if found, None otherwise
        """
        # Check if ID is valid integer (persisted signal)
        try:
            int_id = int(signal_id.value)
        except ValueError:
            return None  # UUID = not yet persisted

        stmt = select(SignalORM).where(SignalORM.id == int_id)
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            return self._mapper.to_entity(orm_model)
        return None

    async def get_pending(self, limit: int = 100) -> List[Signal]:
        """
        Get pending signals for processing.

        Args:
            limit: Maximum number of signals to return

        Returns:
            List of pending Signal entities
        """
        from app.models.database_models import SignalStatus as ORMSignalStatus

        stmt = (
            select(SignalORM)
            .where(SignalORM.status == ORMSignalStatus.RECEIVED)
            .order_by(SignalORM.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]

    async def get_by_status(self, status: SignalStatus, limit: int = 100) -> List[Signal]:
        """
        Get signals by status.

        Args:
            status: Domain SignalStatus enum
            limit: Maximum number of signals to return

        Returns:
            List of Signal entities with given status
        """
        # Map domain status to ORM status
        orm_status = self._mapper._map_status_to_orm(status)

        stmt = (
            select(SignalORM)
            .where(SignalORM.status == orm_status)
            .order_by(SignalORM.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]

    async def get_by_user(self, user_id: int, limit: int = 100, offset: int = 0) -> List[Signal]:
        """
        Get signals for a user.

        Args:
            user_id: User ID
            limit: Maximum number of signals to return
            offset: Number of signals to skip

        Returns:
            List of Signal entities for the user
        """
        stmt = (
            select(SignalORM)
            .where(SignalORM.user_id == user_id)
            .order_by(SignalORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]

    async def get_recent(self, since: datetime, limit: int = 100) -> List[Signal]:
        """
        Get signals since a datetime.

        Args:
            since: Datetime threshold
            limit: Maximum number of signals to return

        Returns:
            List of Signal entities created after the given datetime
        """
        stmt = (
            select(SignalORM)
            .where(SignalORM.created_at >= since)
            .order_by(SignalORM.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]
