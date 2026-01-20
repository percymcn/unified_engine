"""
Position Mapper - bidirectional conversion between ORM and domain.

Handles conversion of Position entities between persistence (SQLAlchemy)
and domain layers, including value objects and side mapping.
"""

from typing import Optional
from decimal import Decimal

from app.models.database_models import Position as PositionORM, OrderSide, PositionStatus
from app.domain.entities.position import Position
from app.domain.enums import PositionSide
from app.domain.value_objects import PositionId, Symbol, Volume, Price, Money


class PositionMapper:
    """
    Maps between Position ORM model and Position domain entity.

    Handles:
    - PositionSide/OrderSide conversion
    - Value objects (Symbol, Volume, Price)
    - Money value objects (margin, swap, commission)
    - Optional price fields (stop_loss, take_profit)
    - Status mapping (is_active based on PositionStatus)
    """

    @staticmethod
    def to_entity(orm_model: PositionORM) -> Position:
        """
        Convert ORM model to domain entity.

        Args:
            orm_model: SQLAlchemy Position model

        Returns:
            Domain Position entity
        """
        # Map ORM side to domain side
        side = PositionSide.LONG if orm_model.side == OrderSide.BUY else PositionSide.SHORT

        # Build value objects
        symbol = Symbol(orm_model.symbol)
        volume = Volume(Decimal(str(orm_model.quantity)))
        open_price = Price(Decimal(str(orm_model.entry_price)))
        current_price = Price(Decimal(str(orm_model.current_price or orm_model.entry_price)))

        # Optional prices
        stop_loss = Price(Decimal(str(orm_model.stop_loss))) if orm_model.stop_loss else None
        take_profit = Price(Decimal(str(orm_model.take_profit))) if orm_model.take_profit else None

        # Money value objects
        margin = Money(abs(Decimal(str(orm_model.commission or 0.0))))  # ORM doesn't have margin field, using commission placeholder
        swap = Money(abs(Decimal(str(orm_model.swap or 0.0))))
        commission = Money(abs(Decimal(str(orm_model.commission or 0.0))))

        # Status - is_active based on PositionStatus.OPEN
        is_active = orm_model.status == PositionStatus.OPEN

        return Position(
            id=PositionId(str(orm_model.id)),
            broker_position_id=orm_model.broker_position_id,
            account_id=str(orm_model.account_id),
            symbol=symbol,
            side=side,
            volume=volume,
            open_price=open_price,
            current_price=current_price,
            open_time=orm_model.opened_at,
            stop_loss=stop_loss,
            take_profit=take_profit,
            margin=margin,
            swap=swap,
            commission=commission,
            comment=None,  # ORM doesn't have comment
            magic_number=None,  # ORM doesn't have magic_number
            is_active=is_active,
        )

    @staticmethod
    def to_model(entity: Position, orm_model: Optional[PositionORM] = None) -> PositionORM:
        """
        Convert domain entity to ORM model.

        Args:
            entity: Domain Position entity
            orm_model: Existing ORM model to update (optional)

        Returns:
            SQLAlchemy Position model
        """
        if orm_model is None:
            orm_model = PositionORM()

        # Map domain side to ORM side
        orm_model.side = OrderSide.BUY if entity.side == PositionSide.LONG else OrderSide.SELL

        # Basic fields
        orm_model.broker_position_id = entity.broker_position_id
        orm_model.account_id = int(entity.account_id)
        orm_model.symbol = entity.symbol.value
        orm_model.quantity = float(entity.volume.value)
        orm_model.entry_price = float(entity.open_price.value)
        orm_model.current_price = float(entity.current_price.value)

        # Optional prices
        orm_model.stop_loss = float(entity.stop_loss.value) if entity.stop_loss else None
        orm_model.take_profit = float(entity.take_profit.value) if entity.take_profit else None

        # P&L fields
        orm_model.commission = float(entity.commission.amount)
        orm_model.swap = float(entity.swap.amount)
        orm_model.unrealized_pnl = float(entity.unrealized_pnl)

        # Status
        if entity.is_active:
            orm_model.status = PositionStatus.OPEN
        else:
            orm_model.status = PositionStatus.CLOSED
            orm_model.closed_at = entity.open_time  # Use open_time as placeholder since domain doesn't track close time

        # Timestamps
        orm_model.opened_at = entity.open_time

        return orm_model
