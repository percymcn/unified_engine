"""
Tradovate Broker Adapter

Implements BrokerPort interface by wrapping TradovateExecutor.
Converts between domain value objects and executor primitives.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

from app.domain.ports.broker_port import BrokerPort
from app.domain.entities.order import Order
from app.domain.entities.position import Position
from app.domain.entities.trade import Trade
from app.domain.value_objects import (
    Symbol, Volume, Price, OrderId, PositionId, Money, AccountId
)
from app.domain.enums import (
    OrderType, OrderStatus, BrokerType, PositionSide, TradeStatus
)
from app.domain.exceptions import (
    BrokerConnectionError, OrderNotFoundError, PositionNotFoundError,
    InvalidOrderError, BusinessRuleViolation
)
from app.brokers.tradovate_executor import TradovateExecutor


class TradovateAdapter(BrokerPort):
    """
    Tradovate broker adapter implementing domain BrokerPort.

    Wraps TradovateExecutor and converts between domain value objects
    and executor primitives. Uses Tradovate REST/WebSocket API.
    """

    def __init__(
        self,
        executor: Optional[TradovateExecutor] = None,
        account_id: Optional[int] = None,
        access_token: Optional[str] = None,
        environment: Optional[str] = None,
    ):
        """
        Initialize Tradovate adapter.

        Args:
            executor: Optional pre-configured TradovateExecutor instance.
                     If None, creates new instance with OAuth or password auth.
            account_id: Database account ID (for OAuth mode token refresh)
            access_token: OAuth access token (enables OAuth mode)
            environment: "demo" or "live" (for OAuth mode API URL selection)
        """
        if executor:
            self._executor = executor
        else:
            self._executor = TradovateExecutor(
                account_id=account_id,
                access_token=access_token,
                environment=environment,
            )

    @property
    def is_using_oauth(self) -> bool:
        """Check if adapter is using OAuth authentication."""
        return self._executor._use_oauth

    @property
    def broker_type(self) -> BrokerType:
        """Return broker type"""
        return BrokerType.TRADOVATE

    async def connect(self) -> bool:
        """
        Connect to Tradovate API.

        Returns:
            True if connection successful

        Raises:
            BrokerConnectionError: If connection fails
        """
        try:
            success = await self._executor.initialize()
            if not success:
                raise BrokerConnectionError(
                    "Failed to connect to Tradovate",
                    context={"broker": "tradovate"}
                )
            return True
        except Exception as e:
            raise BrokerConnectionError(
                f"Tradovate connection error: {e}",
                context={"broker": "tradovate", "error": str(e)}
            )

    async def disconnect(self) -> None:
        """Close Tradovate connection"""
        await self._executor.disconnect()

    async def is_connected(self) -> bool:
        """Check if connected to Tradovate"""
        return self._executor.is_connected()

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with Tradovate API.

        Args:
            credentials: Dict containing username, password, app_id, etc.

        Returns:
            True if authentication successful
        """
        # TradovateExecutor handles authentication in initialize()
        # which reads from config. For now, just check connection.
        return await self.is_connected()

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get Tradovate account information.

        Returns:
            Dict with balance, equity, margin, free_margin, leverage, currency
        """
        accounts = await self._executor.get_accounts()
        if not accounts:
            raise BrokerConnectionError(
                "No Tradovate accounts found",
                context={"broker": "tradovate"}
            )

        # Return first account info
        account = accounts[0]
        return {
            "balance": float(account.balance),
            "equity": float(account.equity),
            "margin": float(account.margin),
            "free_margin": float(account.free_margin),
            "leverage": int(account.leverage),
            "currency": account.currency,
        }

    async def get_positions(self) -> List[Position]:
        """
        Get all open positions.

        Returns:
            List of Position domain entities
        """
        positions_data = await self._executor.get_positions()
        return [self._to_domain_position(p) for p in positions_data]

    async def get_orders(self) -> List[Order]:
        """
        Get all pending orders.

        Returns:
            List of Order domain entities
        """
        orders_data = await self._executor.get_orders()
        return [self._to_domain_order(o) for o in orders_data]

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
        Place a new order on Tradovate.

        Args:
            symbol: Trading symbol
            order_type: Type of order (BUY, SELL, BUY_LIMIT, etc.)
            volume: Order volume
            price: Limit/stop price (required for limit/stop orders)
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            comment: Optional order comment

        Returns:
            Created Order domain entity

        Raises:
            InvalidOrderError: If order validation fails
            BrokerConnectionError: If placement fails
        """
        from app.models.pydantic_schemas import OrderRequest

        # Map domain OrderType to executor order_type string
        order_type_map = {
            OrderType.BUY: "market_buy",
            OrderType.SELL: "market_sell",
            OrderType.BUY_LIMIT: "buy_limit",
            OrderType.SELL_LIMIT: "sell_limit",
            OrderType.BUY_STOP: "buy_stop",
            OrderType.SELL_STOP: "sell_stop",
        }

        executor_order_type = order_type_map.get(order_type)
        if not executor_order_type:
            raise InvalidOrderError(
                f"Unsupported order type: {order_type}",
                context={"order_type": order_type.value}
            )

        # Get first account ID (Tradovate executor needs account_id)
        accounts = await self._executor.get_accounts()
        if not accounts:
            raise BrokerConnectionError("No Tradovate accounts available")

        order_request = OrderRequest(
            account_id=accounts[0].id,
            symbol=symbol.value,
            order_type=executor_order_type,
            quantity=float(volume.value),
            price=float(price.value) if price else None,
            stop_loss=float(stop_loss.value) if stop_loss else None,
            take_profit=float(take_profit.value) if take_profit else None,
        )

        response = await self._executor.place_order(order_request)

        if not response.success:
            raise InvalidOrderError(
                f"Order placement failed: {response.error}",
                context={"symbol": symbol.value, "error": response.error}
            )

        # Create domain Order from response
        return Order(
            id=OrderId(response.order_id or ""),
            broker_order_id=response.order_id,
            account_id=order_request.account_id,
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            status=self._map_order_status(response.status),
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            filled_volume=Decimal(str(response.filled_quantity or 0)),
            comment=comment,
            created_at=response.timestamp or datetime.utcnow(),
        )

    async def modify_order(
        self,
        order_id: OrderId,
        price: Optional[Price] = None,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
    ) -> Order:
        """
        Modify an existing pending order.

        Args:
            order_id: ID of order to modify
            price: New limit/stop price
            stop_loss: New stop loss
            take_profit: New take profit

        Returns:
            Updated Order domain entity

        Raises:
            OrderNotFoundError: If order doesn't exist
            BusinessRuleViolation: If order cannot be modified
        """
        modifications = {}
        if price:
            modifications["price"] = float(price.value)
        if stop_loss:
            modifications["stop_loss"] = float(stop_loss.value)
        if take_profit:
            modifications["take_profit"] = float(take_profit.value)

        response = await self._executor.modify_order(
            order_id.value,
            modifications
        )

        if not response.success:
            if "not found" in response.error.lower():
                raise OrderNotFoundError(
                    f"Order {order_id.value} not found",
                    context={"order_id": order_id.value}
                )
            raise BusinessRuleViolation(
                "order_modification_failed",
                f"Failed to modify order: {response.error}",
                context={"order_id": order_id.value, "error": response.error}
            )

        # Get updated order details
        orders = await self.get_orders()
        for order in orders:
            if order.id.value == order_id.value:
                return order

        # If order not found in list, create minimal response
        return Order(
            id=order_id,
            broker_order_id=order_id.value,
            account_id="",
            symbol=Symbol("UNKNOWN"),
            order_type=OrderType.BUY,
            volume=Volume(Decimal("0")),
            status=OrderStatus.PENDING,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

    async def cancel_order(self, order_id: OrderId) -> None:
        """
        Cancel a pending order.

        Args:
            order_id: ID of order to cancel

        Raises:
            OrderNotFoundError: If order doesn't exist
            BusinessRuleViolation: If order cannot be cancelled
        """
        response = await self._executor.cancel_order(order_id.value)

        if not response.success:
            if "not found" in response.error.lower():
                raise OrderNotFoundError(
                    f"Order {order_id.value} not found",
                    context={"order_id": order_id.value}
                )
            raise BusinessRuleViolation(
                "order_cancellation_failed",
                f"Failed to cancel order: {response.error}",
                context={"order_id": order_id.value, "error": response.error}
            )

    async def close_position(
        self,
        position_id: PositionId,
        volume: Optional[Volume] = None,
    ) -> Trade:
        """
        Close a position (fully or partially).

        Args:
            position_id: ID of position to close
            volume: Optional volume to close (None = close fully)

        Returns:
            Trade domain entity representing the close

        Raises:
            PositionNotFoundError: If position doesn't exist
            BusinessRuleViolation: If position cannot be closed
        """
        quantity = float(volume.value) if volume else None

        response = await self._executor.close_position(
            position_id.value,
            quantity
        )

        if not response.success:
            if "not found" in response.error.lower():
                raise PositionNotFoundError(
                    f"Position {position_id.value} not found",
                    context={"position_id": position_id.value}
                )
            raise BusinessRuleViolation(
                "position_close_failed",
                f"Failed to close position: {response.error}",
                context={"position_id": position_id.value, "error": response.error}
            )

        # Map response to Trade domain entity
        return self._to_domain_trade(response)

    async def modify_position(
        self,
        position_id: PositionId,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
    ) -> Position:
        """
        Modify position stop loss / take profit.

        Args:
            position_id: ID of position to modify
            stop_loss: New stop loss price
            take_profit: New take profit price

        Returns:
            Updated Position domain entity

        Raises:
            PositionNotFoundError: If position doesn't exist
            BusinessRuleViolation: If modification fails
        """
        sl = float(stop_loss.value) if stop_loss else None
        tp = float(take_profit.value) if take_profit else None

        result = await self._executor.modify_position(
            position_id.value,
            stop_loss=sl,
            take_profit=tp
        )

        if result.get("error"):
            if "not found" in result["error"].lower():
                raise PositionNotFoundError(
                    f"Position {position_id.value} not found",
                    context={"position_id": position_id.value}
                )
            raise BusinessRuleViolation(
                "position_modification_failed",
                f"Failed to modify position: {result['error']}",
                context={"position_id": position_id.value, "error": result["error"]}
            )

        # Get updated position
        positions = await self.get_positions()
        for position in positions:
            if position.id.value == position_id.value:
                return position

        # Fallback: create minimal position response
        raise PositionNotFoundError(
            f"Position {position_id.value} not found after modification",
            context={"position_id": position_id.value}
        )

    async def get_quote(self, symbol: Symbol) -> Dict[str, Any]:
        """
        Get current market quote for symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Dict with: symbol, bid, ask, timestamp
        """
        quote = await self._executor.get_quote(symbol.value)

        if not quote:
            return {
                "symbol": symbol.value,
                "bid": 0.0,
                "ask": 0.0,
                "timestamp": datetime.utcnow(),
            }

        return quote

    # Private conversion methods

    def _to_domain_position(self, pos_data: Any) -> Position:
        """Convert executor Position to domain Position"""
        return Position(
            id=PositionId(pos_data.id),
            broker_position_id=pos_data.id,
            account_id=pos_data.account_id,
            symbol=Symbol(pos_data.symbol),
            side=PositionSide.LONG if pos_data.side == "long" else PositionSide.SHORT,
            volume=Volume(Decimal(str(pos_data.size))),
            open_price=Price(Decimal(str(pos_data.entry_price))),
            current_price=Price(Decimal(str(pos_data.current_price))),
            open_time=pos_data.open_time,
            stop_loss=Price(Decimal(str(pos_data.stop_loss))) if hasattr(pos_data, 'stop_loss') and pos_data.stop_loss else None,
            take_profit=Price(Decimal(str(pos_data.take_profit))) if hasattr(pos_data, 'take_profit') and pos_data.take_profit else None,
            margin=Money(abs(Decimal(str(pos_data.margin)))),
            commission=Money(abs(Decimal(str(pos_data.commission or 0)))),
            comment=pos_data.comment or "",
            is_active=pos_data.is_active,
        )

    def _to_domain_order(self, order_data: Any) -> Order:
        """Convert executor order data to domain Order"""
        # This is a placeholder since TradovateExecutor.get_orders()
        # currently returns empty list. Implementation would depend
        # on actual order data structure from Tradovate API.
        return Order(
            id=OrderId(str(order_data.get("id", ""))),
            broker_order_id=str(order_data.get("id", "")),
            account_id=str(order_data.get("account_id", "")),
            symbol=Symbol(order_data.get("symbol", "UNKNOWN")),
            order_type=OrderType.BUY,
            volume=Volume(Decimal(str(order_data.get("quantity", 0)))),
            status=OrderStatus.PENDING,
        )

    def _to_domain_trade(self, trade_response: Any) -> Trade:
        """Convert executor TradeResponse to domain Trade"""
        # Map response side to OrderType
        order_type = OrderType.SELL if trade_response.side == "sell" else OrderType.BUY

        return Trade(
            trade_id=trade_response.trade_id or "",
            broker_trade_id=trade_response.trade_id,
            account_id="",  # Not in response
            symbol=Symbol(trade_response.symbol),
            order_type=order_type,
            volume=Volume(Decimal(str(trade_response.quantity))),
            open_price=Price(Decimal(str(trade_response.price))),
            open_time=trade_response.timestamp or datetime.utcnow(),
            status=TradeStatus.CLOSED,
            close_price=Price(Decimal(str(trade_response.price))),
            close_time=trade_response.timestamp,
            commission=Money(abs(Decimal(str(trade_response.commission)))),
            realized_pnl=Money(abs(Decimal(str(trade_response.pnl)))),
        )

    def _map_order_status(self, status: str) -> OrderStatus:
        """Map executor order status to domain OrderStatus"""
        status_map = {
            "submitted": OrderStatus.PENDING,
            "pending": OrderStatus.PENDING,
            "filled": OrderStatus.EXECUTED,
            "executed": OrderStatus.EXECUTED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "modified": OrderStatus.PENDING,
        }
        return status_map.get(status.lower(), OrderStatus.PENDING)
