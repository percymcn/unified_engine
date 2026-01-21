"""
SymbolAliasRepository Implementation - SQLAlchemy-based persistence.

Implements SymbolAliasRepository port interface using SQLAlchemy for database operations.
Handles CRUD operations and queries for SymbolAlias entities.
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.domain.ports.symbol_alias_repository_port import SymbolAliasRepository
from app.domain.entities.symbol_alias import SymbolAlias
from app.models.models import SymbolAlias as SymbolAliasORM


class SQLAlchemySymbolAliasRepository(SymbolAliasRepository):
    """
    SQLAlchemy implementation of SymbolAliasRepository port.

    Provides persistence for SymbolAlias entities using PostgreSQL.
    Handles ORM-to-domain conversion.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations
        """
        self._session = session

    def _to_entity(self, orm: SymbolAliasORM) -> SymbolAlias:
        """Convert ORM model to domain entity."""
        return SymbolAlias(
            id=orm.id,
            user_id=orm.user_id,
            source_symbol=orm.source_symbol,
            broker_type=orm.broker_type,
            target_symbol=orm.target_symbol,
            is_auto_detected=orm.is_auto_detected or False,
            created_at=orm.created_at or datetime.utcnow(),
            updated_at=orm.updated_at
        )

    def _to_orm(self, entity: SymbolAlias, existing: Optional[SymbolAliasORM] = None) -> SymbolAliasORM:
        """Convert domain entity to ORM model."""
        if existing:
            existing.source_symbol = entity.source_symbol
            existing.broker_type = entity.broker_type
            existing.target_symbol = entity.target_symbol
            existing.is_auto_detected = entity.is_auto_detected
            existing.updated_at = datetime.utcnow()
            return existing
        else:
            return SymbolAliasORM(
                user_id=entity.user_id,
                source_symbol=entity.source_symbol,
                broker_type=entity.broker_type,
                target_symbol=entity.target_symbol,
                is_auto_detected=entity.is_auto_detected
            )

    async def get_by_user_and_broker(
        self,
        user_id: int,
        broker_type: str
    ) -> List[SymbolAlias]:
        """Get all aliases for a user and broker."""
        stmt = (
            select(SymbolAliasORM)
            .where(
                and_(
                    SymbolAliasORM.user_id == user_id,
                    SymbolAliasORM.broker_type == broker_type.lower()
                )
            )
            .order_by(SymbolAliasORM.source_symbol)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(orm) for orm in result.scalars().all()]

    async def get_alias(
        self,
        user_id: int,
        source_symbol: str,
        broker_type: str
    ) -> Optional[SymbolAlias]:
        """Get specific alias by user, source symbol, and broker."""
        stmt = select(SymbolAliasORM).where(
            and_(
                SymbolAliasORM.user_id == user_id,
                SymbolAliasORM.source_symbol == source_symbol.upper(),
                SymbolAliasORM.broker_type == broker_type.lower()
            )
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_entity(orm) if orm else None

    async def get_by_user(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[SymbolAlias]:
        """Get all aliases for a user."""
        stmt = (
            select(SymbolAliasORM)
            .where(SymbolAliasORM.user_id == user_id)
            .order_by(SymbolAliasORM.broker_type, SymbolAliasORM.source_symbol)
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(orm) for orm in result.scalars().all()]

    async def create(self, alias: SymbolAlias) -> SymbolAlias:
        """Create a new alias."""
        orm = self._to_orm(alias)
        self._session.add(orm)

        try:
            await self._session.flush()
            await self._session.refresh(orm)
        except IntegrityError:
            await self._session.rollback()
            raise ValueError(
                f"Alias already exists for {alias.source_symbol} -> {alias.broker_type}"
            )

        return self._to_entity(orm)

    async def update(self, alias: SymbolAlias) -> SymbolAlias:
        """Update an existing alias."""
        if alias.id is None:
            raise ValueError("Cannot update alias without ID")

        stmt = select(SymbolAliasORM).where(
            and_(
                SymbolAliasORM.id == alias.id,
                SymbolAliasORM.user_id == alias.user_id
            )
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if not existing:
            raise ValueError(f"Alias {alias.id} not found for user {alias.user_id}")

        orm = self._to_orm(alias, existing)
        await self._session.flush()
        await self._session.refresh(orm)

        return self._to_entity(orm)

    async def delete(self, alias_id: int, user_id: int) -> bool:
        """Delete an alias by ID."""
        stmt = select(SymbolAliasORM).where(
            and_(
                SymbolAliasORM.id == alias_id,
                SymbolAliasORM.user_id == user_id
            )
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            await self._session.delete(orm)
            await self._session.flush()
            return True

        return False

    async def delete_by_user_and_broker(
        self,
        user_id: int,
        broker_type: str
    ) -> int:
        """Delete all aliases for a user and broker."""
        stmt = delete(SymbolAliasORM).where(
            and_(
                SymbolAliasORM.user_id == user_id,
                SymbolAliasORM.broker_type == broker_type.lower()
            )
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def get_auto_detected(
        self,
        user_id: int,
        broker_type: Optional[str] = None
    ) -> List[SymbolAlias]:
        """Get auto-detected aliases."""
        conditions = [
            SymbolAliasORM.user_id == user_id,
            SymbolAliasORM.is_auto_detected == True
        ]

        if broker_type:
            conditions.append(SymbolAliasORM.broker_type == broker_type.lower())

        stmt = (
            select(SymbolAliasORM)
            .where(and_(*conditions))
            .order_by(SymbolAliasORM.broker_type, SymbolAliasORM.source_symbol)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(orm) for orm in result.scalars().all()]

    async def get_user_defined(
        self,
        user_id: int,
        broker_type: Optional[str] = None
    ) -> List[SymbolAlias]:
        """Get user-defined aliases (not auto-detected)."""
        conditions = [
            SymbolAliasORM.user_id == user_id,
            SymbolAliasORM.is_auto_detected == False
        ]

        if broker_type:
            conditions.append(SymbolAliasORM.broker_type == broker_type.lower())

        stmt = (
            select(SymbolAliasORM)
            .where(and_(*conditions))
            .order_by(SymbolAliasORM.broker_type, SymbolAliasORM.source_symbol)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(orm) for orm in result.scalars().all()]
