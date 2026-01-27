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
            await self._session.commit()
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
        await self._session.commit()
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
            await self._session.commit()
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
        await self._session.commit()
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

    async def bulk_create_auto_aliases(
        self,
        user_id: int,
        broker_type: str,
        symbol_map: dict[str, str]
    ) -> int:
        """
        Bulk create auto-detected aliases from a symbol map.

        Skips aliases that already exist (user-defined take priority).
        Only creates aliases where source != target.

        Args:
            user_id: User ID for the aliases
            broker_type: Broker type (tradelocker, mt5, etc.)
            symbol_map: Dict mapping source symbols to target symbols

        Returns:
            Number of aliases created
        """
        broker = broker_type.lower()
        created = 0

        for source, target in symbol_map.items():
            source_upper = source.upper()

            # Skip if source equals target (no mapping needed)
            if source_upper == target.upper():
                continue

            # Check if alias already exists
            existing = await self.get_alias(user_id, source_upper, broker)
            if existing:
                # User-defined or already auto-detected - skip
                continue

            # Create new auto-detected alias
            alias = SymbolAlias(
                user_id=user_id,
                source_symbol=source_upper,
                broker_type=broker,
                target_symbol=target,
                is_auto_detected=True
            )

            orm = self._to_orm(alias)
            self._session.add(orm)
            created += 1

        # Commit all at once
        if created > 0:
            try:
                await self._session.commit()
            except IntegrityError:
                # Some duplicates slipped through - that's ok
                await self._session.rollback()
                # Retry one by one
                created = 0
                for source, target in symbol_map.items():
                    source_upper = source.upper()
                    if source_upper == target.upper():
                        continue
                    existing = await self.get_alias(user_id, source_upper, broker)
                    if existing:
                        continue
                    try:
                        alias = SymbolAlias(
                            user_id=user_id,
                            source_symbol=source_upper,
                            broker_type=broker,
                            target_symbol=target,
                            is_auto_detected=True
                        )
                        orm = self._to_orm(alias)
                        self._session.add(orm)
                        await self._session.commit()
                        created += 1
                    except IntegrityError:
                        await self._session.rollback()
                        continue

        return created

    async def delete_auto_detected(
        self,
        user_id: int,
        broker_type: str
    ) -> int:
        """
        Delete all auto-detected aliases for a user and broker.

        Used when re-detecting symbols on re-connection.
        Does NOT delete user-defined aliases.

        Returns:
            Number of aliases deleted
        """
        stmt = delete(SymbolAliasORM).where(
            and_(
                SymbolAliasORM.user_id == user_id,
                SymbolAliasORM.broker_type == broker_type.lower(),
                SymbolAliasORM.is_auto_detected == True
            )
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount
