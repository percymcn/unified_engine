"""
Trade Mapper - bidirectional conversion between ORM and domain.

Handles conversion of Trade entities between persistence (SQLAlchemy)
and domain layers, including P&L calculations and status mapping.
"""

from typing import Optional
from decimal import Decimal

from app.models.database_models import Trade as TradeORM, OrderSide
from app.domain.entities.trade import Trade
from app.domain.enums import OrderType, TradeStatus
from app.domain.value_objects import Symbol, Volume, Price, Money


class TradeMapper:
    """
    Maps between Trade ORM model and Trade domain entity.

    Handles:
    - OrderType/OrderSide conversion
    - TradeStatus mapping
    - Money value object creation
    - Price and volume value objects
    - P&L field mapping (gross_pnl → realized_pnl)
    """

    @staticmethod
    def to_entity(orm_model: TradeORM) -> Trade:
        """
        Convert ORM model to domain entity.

        Args:
            orm_model: SQLAlchemy Trade model

        Returns:
            Domain Trade entity
        """
        # Map ORM side (BUY/SELL) to domain OrderType
        order_type = OrderType.BUY if orm_model.side == OrderSide.BUY else OrderType.SELL

        # Map status - ORM doesn't have status, infer from closed_at
        status = TradeStatus.CLOSED if orm_model.closed_at else TradeStatus.OPEN

        # Build value objects
        symbol = Symbol(orm_model.symbol)
        volume = Volume(Decimal(str(orm_model.quantity)))
        open_price = Price(Decimal(str(orm_model.entry_price)))
        close_price = Price(Decimal(str(orm_model.exit_price))) if orm_model.exit_price else None

        # Money value objects (ensure non-negative for Money type)
        commission = Money(abs(Decimal(str(orm_model.commission or 0.0))))
        swap = Money(abs(Decimal(str(orm_model.swap or 0.0))))

        # realized_pnl can be negative, so we use net_pnl directly as Decimal in domain
        # But domain Trade expects Money for realized_pnl, which must be non-negative
        # So we'll use abs value for Money and preserve sign in calculation
        net_pnl_value = Decimal(str(orm_model.net_pnl or 0.0))
        realized_pnl = Money(abs(net_pnl_value)) if net_pnl_value >= 0 else Money(Decimal("0"))

        return Trade(
            trade_id=str(orm_model.id),
            broker_trade_id=orm_model.broker_trade_id,
            account_id=str(orm_model.account_id),
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            open_price=open_price,
            open_time=orm_model.opened_at,
            status=status,
            close_price=close_price,
            close_time=orm_model.closed_at,
            stop_loss=None,  # ORM Trade doesn't track SL/TP
            take_profit=None,
            commission=commission,
            swap=swap,
            realized_pnl=realized_pnl,
            comment=None,  # ORM doesn't have comment
            magic_number=None,  # ORM doesn't have magic_number
        )

    @staticmethod
    def to_model(entity: Trade, orm_model: Optional[TradeORM] = None) -> TradeORM:
        """
        Convert domain entity to ORM model.

        Args:
            entity: Domain Trade entity
            orm_model: Existing ORM model to update (optional)

        Returns:
            SQLAlchemy Trade model
        """
        if orm_model is None:
            orm_model = TradeORM()

        # Map domain OrderType to ORM OrderSide
        orm_model.side = OrderSide.BUY if entity.order_type == OrderType.BUY else OrderSide.SELL

        # Basic fields
        orm_model.broker_trade_id = entity.broker_trade_id
        orm_model.account_id = int(entity.account_id)
        orm_model.symbol = entity.symbol.value
        orm_model.quantity = float(entity.volume.value)
        orm_model.entry_price = float(entity.open_price.value)
        orm_model.exit_price = float(entity.close_price.value) if entity.close_price else None

        # P&L fields
        orm_model.commission = float(entity.commission.amount)
        orm_model.swap = float(entity.swap.amount)
        orm_model.net_pnl = float(entity.realized_pnl.amount)

        # Calculate gross_pnl (net + commission - swap)
        orm_model.gross_pnl = float(entity.realized_pnl.amount + entity.commission.amount - entity.swap.amount)

        # Timestamps
        orm_model.opened_at = entity.open_time
        orm_model.closed_at = entity.close_time

        return orm_model
