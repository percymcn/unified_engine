"""
OrderRepository Implementation - SQLAlchemy-based persistence.

Implements OrderRepository port interface using SQLAlchemy for database operations.
Handles CRUD operations and queries for Order entities.
"""

from typing import Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.repository_port import OrderRepository
from app.domain.entities.order import Order
from app.domain.value_objects import OrderId
from app.domain.enums import OrderStatus
from app.models.database_models import Order as OrderORM, OrderStatus as ORMOrderStatus
from app.infrastructure.mappers import OrderMapper


class SQLAlchemyOrderRepository(OrderRepository):
    """
    SQLAlchemy implementation of OrderRepository port.

    Provides persistence for Order entities using PostgreSQL.
    Uses OrderMapper for ORM ↔ domain conversion.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async database session.

        Args:
            session: SQLAlchemy AsyncSession for database operations
        """
        self._session = session
        self._mapper = OrderMapper()

    async def save(self, order: Order) -> Order:
        """
        Persist order entity (create or update).

        Args:
            order: Domain Order entity

        Returns:
            Persisted Order entity with updated ID
        """
        # Check if order exists
        stmt = select(OrderORM).where(OrderORM.id == int(order.id.value))
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing order
            orm_model = self._mapper.to_model(order, existing)
        else:
            # Create new order
            orm_model = self._mapper.to_model(order)
            self._session.add(orm_model)

        await self._session.flush()
        await self._session.refresh(orm_model)

        return self._mapper.to_entity(orm_model)

    async def delete(self, order: Order) -> None:
        """
        Delete order entity.

        Args:
            order: Domain Order entity to delete
        """
        stmt = select(OrderORM).where(OrderORM.id == int(order.id.value))
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            await self._session.delete(orm_model)
            await self._session.flush()

    async def get_by_id(self, order_id: OrderId) -> Optional[Order]:
        """
        Get order by ID.

        Args:
            order_id: Domain OrderId value object

        Returns:
            Order entity if found, None otherwise
        """
        stmt = select(OrderORM).where(OrderORM.id == int(order_id.value))
        result = await self._session.execute(stmt)
        orm_model = result.scalar_one_or_none()

        if orm_model:
            return self._mapper.to_entity(orm_model)
        return None

    async def get_pending_by_account(self, account_id: str) -> List[Order]:
        """
        Get pending orders for an account.

        Args:
            account_id: Account ID as string

        Returns:
            List of pending Order entities
        """
        stmt = (
            select(OrderORM)
            .where(
                and_(
                    OrderORM.account_id == int(account_id),
                    OrderORM.status.in_([ORMOrderStatus.PENDING, ORMOrderStatus.OPEN])
                )
            )
            .order_by(OrderORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]

    async def get_by_status(self, account_id: str, status: OrderStatus) -> List[Order]:
        """
        Get orders by status for an account.

        Args:
            account_id: Account ID as string
            status: Domain OrderStatus enum

        Returns:
            List of Order entities with given status
        """
        # Map domain status to ORM status
        orm_status = self._mapper._map_status_to_orm(status)

        stmt = (
            select(OrderORM)
            .where(
                and_(
                    OrderORM.account_id == int(account_id),
                    OrderORM.status == orm_status
                )
            )
            .order_by(OrderORM.created_at.desc())
        )
        result = await self._session.execute(stmt)
        orm_models = result.scalars().all()

        return [self._mapper.to_entity(orm) for orm in orm_models]
