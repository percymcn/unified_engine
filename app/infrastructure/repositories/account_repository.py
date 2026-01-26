"""
AccountRepository Implementation - SQLAlchemy-based persistence.

Implements AccountRepository port interface using SQLAlchemy for database operations.
Handles CRUD operations and queries for Account entities.
"""

from typing import Optional, List
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.repository_port import AccountRepository
from app.domain.entities.account import Account
from app.domain.value_objects import AccountId
from app.domain.enums import BrokerType
from app.models.database_models import TradingAccount as AccountORM
from app.models.database_models import WebhookConfig
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
        # For new accounts (UUID domain ID), check by account_number instead of database ID
        # For existing accounts (integer ID as string), check by database ID
        existing = None
        
        # Try to parse account.id.value as integer to determine if it's a database ID
        try:
            db_id = int(account.id.value)
            # It's a database ID (existing account)
            stmt = select(AccountORM).where(AccountORM.id == db_id)
            result = await self._session.execute(stmt)
            existing = result.scalar_one_or_none()
        except (ValueError, TypeError):
            # It's a UUID or other string (new account) - check by account_number instead
            # We need to get the account_number from the mapper's to_model logic
            # For now, check if account_number matches (from server field which contains broker account ID)
            if account.server:
                stmt = select(AccountORM).where(
                    AccountORM.account_number == account.server,
                    AccountORM.user_id == account.user_id
                )
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

    async def delete(self, account) -> None:
        """
        Delete account entity.

        Args:
            account: Domain Account entity or AccountId value object to delete
        """
        account_value = None
        user_id = None
        
        # Handle Account entity
        if hasattr(account, "id"):
            account_value = account.id.value
            user_id = getattr(account, "user_id", None)
        # Handle AccountId value object
        elif hasattr(account, "value"):
            account_value = account.value
        # Handle raw string/int (account_id)
        elif isinstance(account, (str, int)):
            account_value = str(account)

        if account_value is None:
            return

        # Try to parse as integer (database ID) first
        try:
            db_id = int(account_value)
            stmt = select(AccountORM).where(AccountORM.id == db_id)
        except (ValueError, TypeError):
            # Not an integer - try account_number (broker account ID) and user_id
            stmt = select(AccountORM).where(
                AccountORM.account_number == account_value
            )
            if user_id is not None:
                stmt = stmt.where(AccountORM.user_id == user_id)
        
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            await self._session.execute(
                update(WebhookConfig)
                .where(WebhookConfig.default_account_id == orm_model.id)
                .values(default_account_id=None)
            )

            result = await self._session.execute(
                select(WebhookConfig).where(WebhookConfig.user_id == orm_model.user_id)
            )
            configs = result.scalars().all()
            account_id_str = str(orm_model.id)

            for config in configs:
                changed = False
                specific_ids = config.specific_account_ids or []
                filtered_ids = [aid for aid in specific_ids if str(aid) != account_id_str]
                if filtered_ids != specific_ids:
                    config.specific_account_ids = filtered_ids
                    changed = True

                if config.routing_rules:
                    filtered_rules = [
                        rule for rule in config.routing_rules
                        if str(rule.get("target_account_id")) != account_id_str
                    ]
                    if filtered_rules != config.routing_rules:
                        config.routing_rules = filtered_rules
                        changed = True

                if changed:
                    self._session.add(config)

            orm_model.is_active = False
            orm_model.is_connected = False
            orm_model.is_signal_enabled = False
            orm_model.webhook_key = None
            orm_model.enabled_broker_account_ids = None
            orm_model.default_broker_account_id = None
            await self._session.flush()

    async def get_by_id(self, account_id: AccountId) -> Optional[Account]:
        """
        Get account by ID.

        Args:
            account_id: Domain AccountId value object

        Returns:
            Account entity if found, None otherwise
        """
        # Try to parse as integer (database ID) first
        try:
            db_id = int(account_id.value)
            stmt = select(AccountORM).where(AccountORM.id == db_id)
        except (ValueError, TypeError):
            # Not an integer - try account_number (broker account ID)
            stmt = select(AccountORM).where(AccountORM.account_number == account_id.value)
        
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
