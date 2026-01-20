"""
Order Mapper - bidirectional conversion between ORM and domain.

Handles conversion of Order entities between persistence (SQLAlchemy)
and domain layers, including order type/status mapping.
"""

from typing import Optional
from decimal import Decimal

from app.models.database_models import Order as OrderORM
from app.models.database_models import OrderType as ORMOrderType, OrderSide, OrderStatus as ORMOrderStatus
from app.domain.entities.order import Order
from app.domain.enums import OrderType, OrderStatus
from app.domain.value_objects import OrderId, Symbol, Volume, Price


class OrderMapper:
    """
    Maps between Order ORM model and Order domain entity.

    Handles:
    - OrderType conversion (ORM has MARKET/LIMIT/STOP vs domain has BUY/SELL/BUY_LIMIT etc.)
    - OrderStatus mapping
    - OrderSide integration with OrderType
    - Value objects (Symbol, Volume, Price)
    - Filled volume tracking
    """

    @staticmethod
    def to_entity(orm_model: OrderORM) -> Order:
        """
        Convert ORM model to domain entity.

        Args:
            orm_model: SQLAlchemy Order model

        Returns:
            Domain Order entity
        """
        # Map ORM OrderType + OrderSide to domain OrderType
        order_type = OrderMapper._map_order_type_to_domain(orm_model.order_type, orm_model.side)

        # Build value objects
        symbol = Symbol(orm_model.symbol)
        volume = Volume(Decimal(str(orm_model.quantity)))

        # Optional price (for limit/stop orders)
        price = Price(Decimal(str(orm_model.price))) if orm_model.price else None

        # Optional SL/TP
        stop_loss = Price(Decimal(str(orm_model.stop_loss))) if orm_model.stop_loss else None
        take_profit = Price(Decimal(str(orm_model.take_profit))) if orm_model.take_profit else None

        # Map status
        status = OrderMapper._map_status_to_domain(orm_model.status)

        # Filled volume
        filled_volume = Decimal(str(orm_model.filled_quantity or 0.0))

        return Order(
            id=OrderId(str(orm_model.id)),
            broker_order_id=orm_model.broker_order_id,
            account_id=str(orm_model.account_id),
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            status=status,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            filled_volume=filled_volume,
            expire_time=None,  # ORM doesn't have expire_time
            comment=None,  # ORM uses error_message instead
            magic_number=None,  # ORM doesn't have magic_number
            created_at=orm_model.created_at,
            updated_at=orm_model.updated_at,
        )

    @staticmethod
    def to_model(entity: Order, orm_model: Optional[OrderORM] = None) -> OrderORM:
        """
        Convert domain entity to ORM model.

        Args:
            entity: Domain Order entity
            orm_model: Existing ORM model to update (optional)

        Returns:
            SQLAlchemy Order model
        """
        if orm_model is None:
            orm_model = OrderORM()

        # Map domain OrderType to ORM OrderType + OrderSide
        orm_type, orm_side = OrderMapper._map_order_type_to_orm(entity.order_type)
        orm_model.order_type = orm_type
        orm_model.side = orm_side

        # Basic fields
        orm_model.broker_order_id = entity.broker_order_id
        orm_model.account_id = int(entity.account_id)
        orm_model.symbol = entity.symbol.value
        orm_model.quantity = float(entity.volume.value)

        # Optional price
        orm_model.price = float(entity.price.value) if entity.price else None

        # SL/TP
        orm_model.stop_loss = float(entity.stop_loss.value) if entity.stop_loss else None
        orm_model.take_profit = float(entity.take_profit.value) if entity.take_profit else None

        # Status
        orm_model.status = OrderMapper._map_status_to_orm(entity.status)

        # Filled volume and average fill price
        orm_model.filled_quantity = float(entity.filled_volume)
        if entity.filled_volume > 0 and entity.price:
            orm_model.average_fill_price = float(entity.price.value)

        # Timestamps
        orm_model.created_at = entity.created_at
        orm_model.updated_at = entity.updated_at

        # Set filled_at if fully executed
        if entity.status == OrderStatus.EXECUTED:
            orm_model.filled_at = entity.updated_at

        # Set cancelled_at if cancelled
        if entity.status == OrderStatus.CANCELLED:
            orm_model.cancelled_at = entity.updated_at

        return orm_model

    @staticmethod
    def _map_order_type_to_domain(orm_type: ORMOrderType, orm_side: OrderSide) -> OrderType:
        """
        Map ORM OrderType + OrderSide to domain OrderType.

        ORM has MARKET/LIMIT/STOP + BUY/SELL
        Domain has BUY/SELL/BUY_LIMIT/SELL_LIMIT/BUY_STOP/SELL_STOP
        """
        if orm_type == ORMOrderType.MARKET:
            return OrderType.BUY if orm_side == OrderSide.BUY else OrderType.SELL
        elif orm_type == ORMOrderType.LIMIT:
            return OrderType.BUY_LIMIT if orm_side == OrderSide.BUY else OrderType.SELL_LIMIT
        elif orm_type == ORMOrderType.STOP:
            return OrderType.BUY_STOP if orm_side == OrderSide.BUY else OrderType.SELL_STOP
        else:
            # Default to market order
            return OrderType.BUY if orm_side == OrderSide.BUY else OrderType.SELL

    @staticmethod
    def _map_order_type_to_orm(domain_type: OrderType) -> tuple[ORMOrderType, OrderSide]:
        """
        Map domain OrderType to ORM OrderType + OrderSide.

        Returns:
            Tuple of (ORMOrderType, OrderSide)
        """
        mapping = {
            OrderType.BUY: (ORMOrderType.MARKET, OrderSide.BUY),
            OrderType.SELL: (ORMOrderType.MARKET, OrderSide.SELL),
            OrderType.BUY_LIMIT: (ORMOrderType.LIMIT, OrderSide.BUY),
            OrderType.SELL_LIMIT: (ORMOrderType.LIMIT, OrderSide.SELL),
            OrderType.BUY_STOP: (ORMOrderType.STOP, OrderSide.BUY),
            OrderType.SELL_STOP: (ORMOrderType.STOP, OrderSide.SELL),
        }
        return mapping.get(domain_type, (ORMOrderType.MARKET, OrderSide.BUY))

    @staticmethod
    def _map_status_to_domain(orm_status: ORMOrderStatus) -> OrderStatus:
        """Map ORM OrderStatus to domain OrderStatus"""
        mapping = {
            ORMOrderStatus.PENDING: OrderStatus.PENDING,
            ORMOrderStatus.OPEN: OrderStatus.PENDING,  # OPEN in ORM is like PENDING in domain
            ORMOrderStatus.FILLED: OrderStatus.EXECUTED,
            ORMOrderStatus.PARTIALLY_FILLED: OrderStatus.PARTIALLY_FILLED,
            ORMOrderStatus.CANCELLED: OrderStatus.CANCELLED,
            ORMOrderStatus.REJECTED: OrderStatus.REJECTED,
            ORMOrderStatus.EXPIRED: OrderStatus.CANCELLED,  # Map EXPIRED to CANCELLED
        }
        return mapping.get(orm_status, OrderStatus.PENDING)

    @staticmethod
    def _map_status_to_orm(domain_status: OrderStatus) -> ORMOrderStatus:
        """Map domain OrderStatus to ORM OrderStatus"""
        mapping = {
            OrderStatus.PENDING: ORMOrderStatus.PENDING,
            OrderStatus.EXECUTED: ORMOrderStatus.FILLED,
            OrderStatus.PARTIALLY_FILLED: ORMOrderStatus.PARTIALLY_FILLED,
            OrderStatus.CANCELLED: ORMOrderStatus.CANCELLED,
            OrderStatus.REJECTED: ORMOrderStatus.REJECTED,
        }
        return mapping.get(domain_status, ORMOrderStatus.PENDING)
