"""
Trade Service - Domain Service

Manages trade execution business logic through port interfaces.
No direct infrastructure dependencies.
"""

import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal

from app.domain.entities.trade import Trade
from app.domain.entities.order import Order
from app.domain.entities.position import Position
from app.domain.entities.account import Account
from app.domain.ports.repository_port import TradeRepository, OrderRepository, PositionRepository, AccountRepository
from app.domain.ports.broker_port import BrokerPort
from app.domain.ports.event_port import EventPort, DomainEvent, EventType
from app.domain.value_objects import Symbol, Volume, Price, OrderId, PositionId, Money
from app.domain.enums import OrderType, BrokerType
from app.domain.exceptions import (
    InsufficientBalanceError, InvalidOrderError, PositionNotFoundError,
    OrderNotFoundError, BusinessRuleViolation
)

logger = logging.getLogger(__name__)


class TradeService:
    """
    Domain service for trade execution.

    Manages order placement, position management, and trade lifecycle
    through port interfaces.
    """

    def __init__(
        self,
        trade_repository: TradeRepository,
        order_repository: OrderRepository,
        position_repository: PositionRepository,
        account_repository: AccountRepository,
        brokers: Dict[BrokerType, BrokerPort],
        event_port: EventPort,
    ):
        self._trade_repo = trade_repository
        self._order_repo = order_repository
        self._position_repo = position_repository
        self._account_repo = account_repository
        self._brokers = brokers
        self._events = event_port

    async def place_order(
        self,
        account: Account,
        symbol: Symbol,
        order_type: OrderType,
        volume: Volume,
        price: Optional[Price] = None,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
        comment: Optional[str] = None,
    ) -> Order:
        """
        Place a new order.

        1. Validate account has sufficient margin
        2. Place order through broker
        3. Save order to repository
        4. Publish event
        """
        # Get broker adapter
        broker = self._brokers.get(account.broker)
        if not broker:
            raise InvalidOrderError(f"No broker adapter for {account.broker}")

        # Check margin (simplified - real calculation would need symbol specs)
        required_margin = self._estimate_required_margin(volume, price, account.leverage)
        if not account.check_margin_for_trade(required_margin):
            raise InsufficientBalanceError(
                required=float(required_margin.amount),
                available=float(account.free_margin),
                account_id=account.id.value
            )

        # Place order through broker
        order = await broker.place_order(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            comment=comment,
        )

        # Save to repository
        await self._order_repo.save(order)

        # Publish event
        await self._events.publish(DomainEvent.create(
            EventType.ORDER_PLACED,
            {
                "order_id": order.id.value,
                "symbol": symbol.value,
                "type": order_type.value,
                "volume": str(volume.value),
            },
            aggregate_id=order.id.value,
        ))

        return order

    async def cancel_order(self, account: Account, order_id: OrderId) -> None:
        """Cancel a pending order"""
        order = await self._order_repo.get_by_id(order_id)
        if not order:
            raise OrderNotFoundError(order_id.value)

        broker = self._brokers.get(account.broker)
        if not broker:
            raise BusinessRuleViolation("no_broker_adapter", f"No broker adapter for {account.broker}")

        await broker.cancel_order(order_id)
        order.cancel()
        await self._order_repo.save(order)

        await self._events.publish(DomainEvent.create(
            EventType.ORDER_CANCELLED,
            {"order_id": order_id.value},
            aggregate_id=order_id.value,
        ))

    async def close_position(
        self,
        account: Account,
        position_id: PositionId,
        volume: Optional[Volume] = None,
    ) -> Trade:
        """
        Close a position (fully or partially).

        1. Get position from broker
        2. Close through broker
        3. Update account balance with realized P&L
        4. Save trade and publish event
        """
        position = await self._position_repo.get_by_id(position_id)
        if not position:
            raise PositionNotFoundError(position_id.value)

        broker = self._brokers.get(account.broker)
        if not broker:
            raise BusinessRuleViolation("no_broker_adapter", f"No broker adapter for {account.broker}")

        # Close through broker
        trade = await broker.close_position(position_id, volume)

        # Apply P&L to account
        account.realize_pnl(trade.realized_pnl)
        account.release_margin(position.margin)
        await self._account_repo.save(account)

        # Save trade
        await self._trade_repo.save(trade)

        # Publish event
        await self._events.publish(DomainEvent.create(
            EventType.TRADE_CLOSED,
            {
                "trade_id": trade.trade_id,
                "symbol": trade.symbol.value,
                "pnl": str(trade.realized_pnl.amount),
            },
            aggregate_id=trade.trade_id,
        ))

        return trade

    async def modify_position(
        self,
        account: Account,
        position_id: PositionId,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
    ) -> Position:
        """Modify position stop loss / take profit"""
        position = await self._position_repo.get_by_id(position_id)
        if not position:
            raise PositionNotFoundError(position_id.value)

        broker = self._brokers.get(account.broker)
        if not broker:
            raise BusinessRuleViolation("no_broker_adapter", f"No broker adapter for {account.broker}")

        updated = await broker.modify_position(position_id, stop_loss, take_profit)
        await self._position_repo.save(updated)

        await self._events.publish(DomainEvent.create(
            EventType.POSITION_MODIFIED,
            {
                "position_id": position_id.value,
                "stop_loss": str(stop_loss.value) if stop_loss else None,
                "take_profit": str(take_profit.value) if take_profit else None,
            },
            aggregate_id=position_id.value,
        ))

        return updated

    async def get_open_positions(self, account_id: str) -> List[Position]:
        """Get open positions for account"""
        return await self._position_repo.get_open_by_account(account_id)

    async def get_trades(self, account_id: str, limit: int = 100) -> List[Trade]:
        """Get trades for account"""
        return await self._trade_repo.get_by_account(account_id, limit)

    def _estimate_required_margin(self, volume: Volume, price: Optional[Price], leverage: int) -> Money:
        """Estimate margin required for trade (simplified)"""
        # Real calculation would need symbol specs (contract size, currency)
        # This is a simplified estimate
        price_value = price.value if price else Decimal("1.0")
        margin = (volume.value * price_value * 100000) / leverage  # Assuming standard forex lot
        return Money(margin)
