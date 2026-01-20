"""
AccountRepository Implementation - SQLAlchemy-based persistence.

Implements AccountRepository port interface using SQLAlchemy for database operations.
Handles CRUD operations and queries for Account entities.
"""

from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.repository_port import AccountRepository
from app.domain.entities.account import Account
from app.domain.value_objects import AccountId
from app.domain.enums import BrokerType
from app.models.database_models import TradingAccount as AccountORM
from app.infrastructure.mappers import AccountMapper


class SQLAlchemyAccountRepository(AccountRepository):
    """
    SQLAlchemy implementation of AccountRepository port.

    Provides persistence for Account entities using PostgreSQL.
    Uses AccountMapper for ORM ↔ domain conversion.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations
        """
        self._session = session
        self._mapper = AccountMapper()

    async def save(self, account: Account) -> Account:
        """
        Persist account entity (create or update).

        Args:
            account: Domain Account entity

        Returns:
            Persisted Account entity with updated ID
        """
        # Check if account exists
        stmt = select(AccountORM).where(AccountORM.id == int(account.id.value))
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing account
            orm_model = self._mapper.to_model(account, existing)
        else:
            # Create new account
            orm_model = self._mapper.to_model(account)
            self._session.add(orm_model)

        await self._session.flush()
        await self._session.refresh(orm_model)

        return self._mapper.to_entity(orm_model)

    async def delete(self, account: Account) -> None:
        """
        Delete account entity.

        Args:
            account: Domain Account entity to delete
        """
        stmt = select(AccountORM).where(AccountORM.id == int(account.id.value))
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            await self._session.delete(orm_model)
            await self._session.flush()

    async def get_by_id(self, account_id: AccountId) -> Optional[Account]:
        """
        Get account by ID.

        Args:
            account_id: Domain AccountId value object

        Returns:
            Account entity if found, None otherwise
        """
        stmt = select(AccountORM).where(AccountORM.id == int(account_id.value))
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            return self._mapper.to_entity(orm_model)
        return None

    async def get_by_user(self, user_id: int) -> List[Account]:
        """
        Get accounts for a user.

        Args:
            user_id: User ID

        Returns:
            List of Account entities for the user
        """
        stmt = (
            select(AccountORM)
            .where(AccountORM.user_id == user_id)
            .order_by(AccountORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]

    async def get_by_broker(self, broker: BrokerType) -> List[Account]:
        """
        Get accounts by broker type.

        Args:
            broker: Domain BrokerType enum

        Returns:
            List of Account entities for the broker
        """
        # Map domain broker to ORM broker
        orm_broker = self._mapper._map_broker_to_orm(broker)

        stmt = (
            select(AccountORM)
            .where(AccountORM.broker == orm_broker)
            .order_by(AccountORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]

    async def get_active(self) -> List[Account]:
        """
        Get all active accounts.

        Returns:
            List of active Account entities
        """
        stmt = (
            select(AccountORM)
            .where(AccountORM.is_active == True)
            .order_by(AccountORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]

    async def get_connected(self) -> List[Account]:
        """
        Get all connected accounts.

        Returns:
            List of connected Account entities
        """
        stmt = (
            select(AccountORM)
            .where(
                and_(
                    AccountORM.is_active == True,
                    AccountORM.is_connected == True
                )
            )
            .order_by(AccountORM.last_sync.desc())
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]
