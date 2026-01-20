"""
TradeLocker Broker Adapter

Implements BrokerPort interface by wrapping TradeLockerExecutor.
Converts between domain value objects and executor primitives.
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime

from app.domain.ports.broker_port import BrokerPort
from app.domain.entities.order import Order
from app.domain.entities.position import Position
from app.domain.entities.trade import Trade
from app.domain.value_objects import (
    Symbol, Volume, Price, OrderId, PositionId, Money
)
from app.domain.enums import (
    BrokerType, OrderType, OrderStatus, PositionSide, TradeStatus
)
from app.domain.exceptions import (
    BrokerConnectionError, OrderNotFoundError, PositionNotFoundError
)
from app.brokers.tradelocker_executor import TradeLockerExecutor


class TradeLockerAdapter(BrokerPort):
    """
    TradeLocker broker adapter implementing domain BrokerPort.

    Wraps TradeLockerExecutor and converts between domain value objects
    and executor primitives.
    """

    def __init__(self, executor: Optional[TradeLockerExecutor] = None):
        """
        Initialize adapter with optional executor instance.

        Args:
            executor: Optional pre-configured TradeLockerExecutor instance
        """
        self._executor = executor
        self._account_id: Optional[str] = None

    @property
    def broker_type(self) -> BrokerType:
        """Return the broker type this adapter handles"""
        return BrokerType.TRADELOCKER

    async def connect(self) -> bool:
        """
        Establish connection to TradeLocker.
        Returns True if connection successful.
        """
        try:
            if self._executor is None:
                self._executor = TradeLockerExecutor()

            success = await self._executor.initialize()
            return success
        except Exception as e:
            raise BrokerConnectionError(
                f"Failed to connect to TradeLocker: {e}",
                context={"broker": "tradelocker", "error": str(e)}
            )

    async def disconnect(self) -> None:
        """Close TradeLocker connection"""
        if self._executor:
            await self._executor.disconnect()

    async def is_connected(self) -> bool:
        """Check if TradeLocker connection is active"""
        if not self._executor:
            return False
        return self._executor.is_connected()

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with TradeLocker using provided credentials.
        TradeLocker authenticates during connection setup.

        Args:
            credentials: Dict with authentication details (not used for TradeLocker)

        Returns:
            True if authenticated (connection is active)
        """
        # TradeLocker authenticates on connect via API key
        # Store account_id if provided for tracking
        if "account_id" in credentials:
            self._account_id = credentials["account_id"]

        return await self.is_connected()

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.
        Returns dict with: balance, equity, margin, free_margin, leverage, currency
        """
        if not self._executor:
            raise BrokerConnectionError(
                "Not connected to TradeLocker",
                context={"broker": "tradelocker"}
            )

        # TradeLocker returns account info
        account_info = await self._executor.get_account_info(self._account_id)

        if account_info is None:
            raise BrokerConnectionError(
                "Failed to retrieve account info",
                context={"broker": "tradelocker", "account_id": self._account_id}
            )

        # Convert to dict format expected by domain
        return {
            "balance": float(account_info.balance),
            "equity": float(account_info.equity),
            "margin": float(account_info.margin),
            "free_margin": float(account_info.free_margin),
            "leverage": account_info.leverage,
            "currency": account_info.currency,
        }

    async def get_positions(self) -> List[Position]:
        """
        Get all open positions.
        Returns list of Position domain entities.
        """
        if not self._executor:
            raise BrokerConnectionError(
                "Not connected to TradeLocker",
                context={"broker": "tradelocker"}
            )

        # Get positions from executor
        executor_positions = await self._executor.get_positions(self._account_id)

        # Convert to domain entities
        return [self._to_domain_position(p) for p in executor_positions]

    async def get_orders(self) -> List[Order]:
        """
        Get all pending orders.
        Returns list of Order domain entities.
        """
        if not self._executor:
            raise BrokerConnectionError(
                "Not connected to TradeLocker",
                context={"broker": "tradelocker"}
            )

        # Get orders from executor
        executor_orders = await self._executor.get_orders()

        # Convert to domain entities
        return [self._to_domain_order(o) for o in executor_orders]

    async def place_order(
        self,
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
        Returns the created Order domain entity.
        Raises: InvalidOrderError, InsufficientBalanceError, BrokerConnectionError
        """
        if not self._executor:
            raise BrokerConnectionError(
                "Not connected to TradeLocker",
                context={"broker": "tradelocker"}
            )

        # Import OrderRequest to construct request
        from app.models.pydantic_schemas import OrderRequest

        # Map domain OrderType to executor order_type string
        executor_order_type = self._map_order_type_to_executor(order_type)

        # Create order request
        order_request = OrderRequest(
            account_id=self._account_id,
            symbol=symbol.value,
            order_type=executor_order_type,
            quantity=float(volume.value),
            price=float(price.value) if price else None,
            stop_loss=float(stop_loss.value) if stop_loss else None,
            take_profit=float(take_profit.value) if take_profit else None,
            comment=comment,
        )

        # Place order via executor
        response = await self._executor.place_order(order_request)

        if not response.success:
            raise BrokerConnectionError(
                f"Order placement failed: {response.error}",
                context={"broker": "tradelocker", "symbol": symbol.value}
            )

        # Convert response to domain Order
        return self._order_response_to_domain(response, symbol, order_type, volume, price, stop_loss, take_profit, comment)

    async def modify_order(
        self,
        order_id: OrderId,
        price: Optional[Price] = None,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
    ) -> Order:
        """
        Modify an existing pending order.
        Returns updated Order domain entity.
        Raises: OrderNotFoundError, BusinessRuleViolation
        """
        if not self._executor:
            raise BrokerConnectionError(
                "Not connected to TradeLocker",
                context={"broker": "tradelocker"}
            )

        modifications = {}
        if price:
            modifications["price"] = float(price.value)
        if stop_loss:
            modifications["stop_loss"] = float(stop_loss.value)
        if take_profit:
            modifications["take_profit"] = float(take_profit.value)

        response = await self._executor.modify_order(order_id.value, modifications)

        if not response.success:
            if "not found" in str(response.error).lower():
                raise OrderNotFoundError(
                    f"Order {order_id.value} not found",
                    context={"order_id": order_id.value}
                )
            raise BrokerConnectionError(
                f"Order modification failed: {response.error}",
                context={"broker": "tradelocker", "order_id": order_id.value}
            )

        # Get updated order
        orders = await self.get_orders()
        for order in orders:
            if order.broker_order_id == order_id.value:
                return order

        raise OrderNotFoundError(
            f"Order {order_id.value} not found after modification",
            context={"order_id": order_id.value}
        )

    async def cancel_order(self, order_id: OrderId) -> None:
        """
        Cancel a pending order.
        Raises: OrderNotFoundError, BusinessRuleViolation
        """
        if not self._executor:
            raise BrokerConnectionError(
                "Not connected to TradeLocker",
                context={"broker": "tradelocker"}
            )

        response = await self._executor.cancel_order(order_id.value)

        if not response.success:
            if "not found" in str(response.error).lower():
                raise OrderNotFoundError(
                    f"Order {order_id.value} not found",
                    context={"order_id": order_id.value}
                )
            raise BrokerConnectionError(
                f"Order cancellation failed: {response.error}",
                context={"broker": "tradelocker", "order_id": order_id.value}
            )

    async def close_position(
        self,
        position_id: PositionId,
        volume: Optional[Volume] = None,
    ) -> Trade:
        """
        Close a position (fully or partially).
        Returns the resulting Trade domain entity.
        Raises: PositionNotFoundError, BusinessRuleViolation
        """
        if not self._executor:
            raise BrokerConnectionError(
                "Not connected to TradeLocker",
                context={"broker": "tradelocker"}
            )

        response = await self._executor.close_position(
            position_id.value,
            float(volume.value) if volume else None
        )

        if not response.success:
            if "not found" in str(response.error).lower():
                raise PositionNotFoundError(
                    f"Position {position_id.value} not found",
                    context={"position_id": position_id.value}
                )
            raise BrokerConnectionError(
                f"Position close failed: {response.error}",
                context={"broker": "tradelocker", "position_id": position_id.value}
            )

        # Convert response to domain Trade
        return self._trade_response_to_domain(response)

    async def modify_position(
        self,
        position_id: PositionId,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
    ) -> Position:
        """
        Modify position stop loss / take profit.
        Returns updated Position domain entity.
        Raises: PositionNotFoundError, BusinessRuleViolation
        """
        if not self._executor:
            raise BrokerConnectionError(
                "Not connected to TradeLocker",
                context={"broker": "tradelocker"}
            )

        result = await self._executor.modify_position(
            position_id.value,
            float(stop_loss.value) if stop_loss else None,
            float(take_profit.value) if take_profit else None
        )

        if "error" in result:
            if "not found" in str(result["error"]).lower():
                raise PositionNotFoundError(
                    f"Position {position_id.value} not found",
                    context={"position_id": position_id.value}
                )
            raise BrokerConnectionError(
                f"Position modification failed: {result['error']}",
                context={"broker": "tradelocker", "position_id": position_id.value}
            )

        # Get updated position
        positions = await self.get_positions()
        for position in positions:
            if position.broker_position_id == position_id.value:
                return position

        raise PositionNotFoundError(
            f"Position {position_id.value} not found after modification",
            context={"position_id": position_id.value}
        )

    async def get_quote(self, symbol: Symbol) -> Dict[str, Any]:
        """
        Get current market quote.
        Returns dict with: symbol, bid, ask, timestamp
        """
        if not self._executor:
            raise BrokerConnectionError(
                "Not connected to TradeLocker",
                context={"broker": "tradelocker"}
            )

        quote = await self._executor.get_quote(symbol.value)

        if not quote:
            raise BrokerConnectionError(
                f"Failed to get quote for {symbol.value}",
                context={"broker": "tradelocker", "symbol": symbol.value}
            )

        return quote

    # Private conversion methods

    def _to_domain_position(self, executor_position) -> Position:
        """Convert executor Position to domain Position entity"""
        return Position(
            id=PositionId(executor_position.id),
            broker_position_id=executor_position.id,
            account_id=executor_position.account_id,
            symbol=Symbol(executor_position.symbol),
            side=PositionSide.LONG if executor_position.side.lower() == "buy" else PositionSide.SHORT,
            volume=Volume(Decimal(str(executor_position.size))),
            open_price=Price(Decimal(str(executor_position.entry_price))),
            current_price=Price(Decimal(str(executor_position.current_price))),
            open_time=executor_position.open_time,
            stop_loss=Price(Decimal(str(executor_position.stop_loss))) if hasattr(executor_position, 'stop_loss') and executor_position.stop_loss else None,
            take_profit=Price(Decimal(str(executor_position.take_profit))) if hasattr(executor_position, 'take_profit') and executor_position.take_profit else None,
            margin=Money(Decimal(str(executor_position.margin))),
            swap=Money(Decimal("0")),  # TradeLocker doesn't provide swap separately
            commission=Money(Decimal("0")),  # Commission tracked separately
            comment=executor_position.comment if hasattr(executor_position, 'comment') else None,
            magic_number=executor_position.magic_number if hasattr(executor_position, 'magic_number') else None,
            is_active=executor_position.is_active,
        )

    def _to_domain_order(self, executor_order: Dict[str, Any]) -> Order:
        """Convert executor order dict to domain Order entity"""
        # Extract order details
        order_id = executor_order.get("id", executor_order.get("order_id"))

        return Order(
            id=OrderId(str(order_id)),
            broker_order_id=str(order_id),
            account_id=executor_order.get("account_id", self._account_id),
            symbol=Symbol(executor_order["symbol"]),
            order_type=self._map_executor_to_order_type(executor_order["type"]),
            volume=Volume(Decimal(str(executor_order["quantity"]))),
            status=self._map_executor_to_order_status(executor_order.get("status", "pending")),
            price=Price(Decimal(str(executor_order["price"]))) if executor_order.get("price") else None,
            stop_loss=Price(Decimal(str(executor_order["stop_loss"]))) if executor_order.get("stop_loss") else None,
            take_profit=Price(Decimal(str(executor_order["take_profit"]))) if executor_order.get("take_profit") else None,
            comment=executor_order.get("comment"),
            magic_number=executor_order.get("magic_number"),
        )

    def _order_response_to_domain(
        self,
        response,
        symbol: Symbol,
        order_type: OrderType,
        volume: Volume,
        price: Optional[Price],
        stop_loss: Optional[Price],
        take_profit: Optional[Price],
        comment: Optional[str],
    ) -> Order:
        """Convert OrderResponse to domain Order entity"""
        return Order(
            id=OrderId(response.order_id),
            broker_order_id=response.order_id,
            account_id=self._account_id,
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            status=self._map_executor_to_order_status(response.status),
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            filled_volume=Decimal(str(response.filled_quantity)) if hasattr(response, 'filled_quantity') else Decimal("0"),
            comment=comment,
            created_at=response.timestamp,
        )

    def _trade_response_to_domain(self, response) -> Trade:
        """Convert TradeResponse to domain Trade entity"""
        # Determine order type from side
        if response.side.lower() in ["buy", "long"]:
            order_type = OrderType.BUY
        else:
            order_type = OrderType.SELL

        return Trade(
            trade_id=response.trade_id,
            broker_trade_id=response.trade_id,
            account_id=self._account_id,
            symbol=Symbol(response.symbol),
            order_type=order_type,
            volume=Volume(Decimal(str(response.quantity))),
            open_price=Price(Decimal(str(response.price))),
            open_time=response.timestamp,
            status=TradeStatus.CLOSED,
            close_price=Price(Decimal(str(response.price))),
            close_time=response.timestamp,
            commission=Money(Decimal(str(abs(response.commission)))),
            realized_pnl=Money(Decimal(str(abs(response.pnl)))),
        )

    def _map_order_type_to_executor(self, order_type: OrderType) -> str:
        """Map domain OrderType to executor order_type string"""
        mapping = {
            OrderType.BUY: "market_buy",
            OrderType.SELL: "market_sell",
            OrderType.BUY_LIMIT: "buy_limit",
            OrderType.SELL_LIMIT: "sell_limit",
            OrderType.BUY_STOP: "buy_stop",
            OrderType.SELL_STOP: "sell_stop",
        }
        return mapping.get(order_type, "market_buy")

    def _map_executor_to_order_type(self, executor_type: str) -> OrderType:
        """Map executor order type string to domain OrderType"""
        mapping = {
            "market_buy": OrderType.BUY,
            "market_sell": OrderType.SELL,
            "buy_limit": OrderType.BUY_LIMIT,
            "sell_limit": OrderType.SELL_LIMIT,
            "buy_stop": OrderType.BUY_STOP,
            "sell_stop": OrderType.SELL_STOP,
            "MARKET_BUY": OrderType.BUY,
            "MARKET_SELL": OrderType.SELL,
            "BUY_LIMIT": OrderType.BUY_LIMIT,
            "SELL_LIMIT": OrderType.SELL_LIMIT,
            "BUY_STOP": OrderType.BUY_STOP,
            "SELL_STOP": OrderType.SELL_STOP,
        }
        return mapping.get(executor_type, OrderType.BUY)

    def _map_executor_to_order_status(self, executor_status: str) -> OrderStatus:
        """Map executor status string to domain OrderStatus"""
        mapping = {
            "pending": OrderStatus.PENDING,
            "executed": OrderStatus.EXECUTED,
            "filled": OrderStatus.EXECUTED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
        }
        return mapping.get(executor_status.lower(), OrderStatus.PENDING)
