"""
TopStep/ProjectX Broker Adapter

Implements BrokerPort interface for TopStep/ProjectX Gateway API integration.
Wraps ProjectXExecutor and converts between domain value objects and executor primitives.
"""

from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime

from app.domain.ports.broker_port import BrokerPort
from app.domain.entities.order import Order
from app.domain.entities.position import Position
from app.domain.entities.trade import Trade
from app.domain.value_objects import Symbol, Volume, Price, OrderId, PositionId
from app.domain.enums import OrderType, OrderStatus, BrokerType, PositionSide, TradeStatus
from app.domain.exceptions import BrokerConnectionError, OrderNotFoundError, PositionNotFoundError
from app.brokers.projectx_executor import ProjectXExecutor


class TopstepAdapter(BrokerPort):
    """
    TopStep/ProjectX broker adapter implementing domain BrokerPort.

    Wraps ProjectXExecutor and converts between domain value objects
    and executor primitives. Uses ProjectX Gateway API for TopStep accounts.
    """

    def __init__(self, executor: Optional[ProjectXExecutor] = None):
        """
        Initialize TopStep adapter.

        Args:
            executor: Optional ProjectXExecutor instance. If None, created on connect.
        """
        self._executor = executor

    @property
    def broker_type(self) -> BrokerType:
        """Return broker type"""
        return BrokerType.TOPSTEP

    async def connect(self) -> bool:
        """
        Establish connection to ProjectX Gateway.

        Returns:
            True if connection successful

        Raises:
            BrokerConnectionError: If connection fails
        """
        try:
            if self._executor is None:
                self._executor = ProjectXExecutor()

            success = await self._executor.initialize()
            if not success:
                raise BrokerConnectionError(
                    "Failed to connect to ProjectX Gateway",
                    context={"broker": "topstep"}
                )
            return True
        except Exception as e:
            raise BrokerConnectionError(
                f"TopStep connection error: {str(e)}",
                context={"broker": "topstep", "error": str(e)}
            )

    async def disconnect(self) -> None:
        """Close ProjectX Gateway connection"""
        if self._executor:
            await self._executor.disconnect()

    async def is_connected(self) -> bool:
        """Check if broker connection is active"""
        if self._executor is None:
            return False
        return self._executor.is_connected

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with ProjectX Gateway.

        Args:
            credentials: Dict with 'api_token' key

        Returns:
            True if authentication successful
        """
        # ProjectX authenticates during initialization with API token from config
        # This method validates the connection is authenticated
        return await self.is_connected()

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information from ProjectX.

        Returns:
            Dict with account balance, equity, margin, etc.

        Raises:
            BrokerConnectionError: If not connected
        """
        if not await self.is_connected():
            raise BrokerConnectionError(
                "Not connected to TopStep",
                context={"broker": "topstep"}
            )

        # ProjectX returns Account objects, get first one
        accounts = await self._executor.get_accounts()
        if not accounts:
            return {
                "balance": 0.0,
                "equity": 0.0,
                "margin": 0.0,
                "free_margin": 0.0,
                "leverage": 100,
                "currency": "USD"
            }

        account = accounts[0]
        return {
            "balance": account.balance,
            "equity": account.equity,
            "margin": account.margin,
            "free_margin": account.free_margin,
            "leverage": account.leverage,
            "currency": account.currency,
            "margin_level": account.margin_level,
        }

    async def get_positions(self) -> List[Position]:
        """
        Get all open positions from ProjectX.

        Returns:
            List of Position domain entities

        Raises:
            BrokerConnectionError: If not connected
        """
        if not await self.is_connected():
            raise BrokerConnectionError(
                "Not connected to TopStep",
                context={"broker": "topstep"}
            )

        executor_positions = await self._executor.get_positions()
        return [self._to_domain_position(p) for p in executor_positions]

    async def get_orders(self) -> List[Order]:
        """
        Get all pending orders from ProjectX.

        Returns:
            List of Order domain entities

        Raises:
            BrokerConnectionError: If not connected
        """
        if not await self.is_connected():
            raise BrokerConnectionError(
                "Not connected to TopStep",
                context={"broker": "topstep"}
            )

        # ProjectX executor returns empty list for get_orders
        executor_orders = await self._executor.get_orders()
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
        Place a new order via ProjectX Gateway.

        Args:
            symbol: Trading symbol
            order_type: Order type (BUY, SELL, BUY_LIMIT, etc.)
            volume: Order volume
            price: Limit/stop price (required for non-market orders)
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            comment: Optional order comment

        Returns:
            Created Order domain entity

        Raises:
            BrokerConnectionError: If not connected
            ValidationError: If order parameters invalid
        """
        if not await self.is_connected():
            raise BrokerConnectionError(
                "Not connected to TopStep",
                context={"broker": "topstep"}
            )

        # Convert domain OrderType to executor format
        order_type_str = self._map_order_type_to_executor(order_type)

        # Build OrderRequest for executor
        from app.models.pydantic_schemas import OrderRequest

        order_request = OrderRequest(
            account_id="",  # ProjectX uses first account
            symbol=symbol.value,
            order_type=order_type_str,
            quantity=float(volume.value),
            price=float(price.value) if price else None,
            stop_loss=float(stop_loss.value) if stop_loss else None,
            take_profit=float(take_profit.value) if take_profit else None,
            comment=comment or "",
            magic_number=0,
        )

        response = await self._executor.place_order(order_request)

        if not response.success:
            from app.domain.exceptions import InvalidOrderError
            raise InvalidOrderError(
                f"Order placement failed: {response.error}",
                context={"symbol": symbol.value, "type": order_type.value}
            )

        # Convert response to domain Order
        return Order(
            id=OrderId(response.order_id),
            broker_order_id=response.order_id,
            account_id="",  # Will be set by use case
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=self._map_order_status(response.status),
            filled_volume=Decimal(str(response.filled_quantity)) if hasattr(response, 'filled_quantity') else Decimal("0"),
            comment=comment,
            created_at=response.timestamp if hasattr(response, 'timestamp') else datetime.utcnow(),
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
            order_id: Order to modify
            price: New limit/stop price
            stop_loss: New stop loss
            take_profit: New take profit

        Returns:
            Updated Order domain entity

        Raises:
            OrderNotFoundError: If order not found
            BrokerConnectionError: If not connected
        """
        if not await self.is_connected():
            raise BrokerConnectionError(
                "Not connected to TopStep",
                context={"broker": "topstep"}
            )

        modifications = {}
        if price:
            modifications["price"] = float(price.value)
        if stop_loss:
            modifications["stop_loss"] = float(stop_loss.value)
        if take_profit:
            modifications["take_profit"] = float(take_profit.value)

        response = await self._executor.modify_order(str(order_id), modifications)

        if not response.success:
            raise OrderNotFoundError(
                order_id.value,
                context={"error": response.error}
            )

        # Return updated order (simplified - would need to fetch actual order)
        return Order(
            id=order_id,
            broker_order_id=str(order_id),
            account_id="",
            symbol=Symbol("UNKNOWN"),  # Would need to fetch
            order_type=OrderType.BUY,
            volume=Volume(Decimal("1.0")),
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow(),
        )

    async def cancel_order(self, order_id: OrderId) -> None:
        """
        Cancel a pending order.

        Args:
            order_id: Order to cancel

        Raises:
            OrderNotFoundError: If order not found
            BrokerConnectionError: If not connected
        """
        if not await self.is_connected():
            raise BrokerConnectionError(
                "Not connected to TopStep",
                context={"broker": "topstep"}
            )

        response = await self._executor.cancel_order(str(order_id))

        if not response.success:
            raise OrderNotFoundError(
                order_id.value,
                context={"error": response.error}
            )

    async def close_position(
        self,
        position_id: PositionId,
        volume: Optional[Volume] = None,
    ) -> Trade:
        """
        Close a position (fully or partially).

        Args:
            position_id: Position to close
            volume: Optional volume for partial close

        Returns:
            Resulting Trade domain entity

        Raises:
            PositionNotFoundError: If position not found
            BrokerConnectionError: If not connected
        """
        if not await self.is_connected():
            raise BrokerConnectionError(
                "Not connected to TopStep",
                context={"broker": "topstep"}
            )

        response = await self._executor.close_position(
            position_id=str(position_id),
            quantity=float(volume.value) if volume else None,
        )

        if not response.success:
            raise PositionNotFoundError(
                position_id.value,
                context={"error": response.error}
            )

        # Convert response to Trade domain entity
        return Trade(
            trade_id=response.trade_id,
            broker_trade_id=response.trade_id,
            account_id="",
            symbol=Symbol(response.symbol),
            order_type=OrderType.SELL if response.side.lower() == "sell" else OrderType.BUY,
            volume=Volume(Decimal(str(response.quantity))),
            open_price=Price(Decimal(str(response.price))),
            open_time=response.timestamp,
            close_price=Price(Decimal(str(response.price))),
            close_time=response.timestamp,
            status=TradeStatus.CLOSED,
        )

    async def modify_position(
        self,
        position_id: PositionId,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
    ) -> Position:
        """
        Modify position stop loss / take profit.

        Args:
            position_id: Position to modify
            stop_loss: New stop loss price
            take_profit: New take profit price

        Returns:
            Updated Position domain entity

        Raises:
            PositionNotFoundError: If position not found
            BrokerConnectionError: If not connected
        """
        if not await self.is_connected():
            raise BrokerConnectionError(
                "Not connected to TopStep",
                context={"broker": "topstep"}
            )

        result = await self._executor.modify_position(
            position_id=str(position_id),
            stop_loss=float(stop_loss.value) if stop_loss else None,
            take_profit=float(take_profit.value) if take_profit else None,
        )

        # ProjectX executor returns dict with error key
        if isinstance(result, dict) and "error" in result:
            raise PositionNotFoundError(
                position_id.value,
                context={"error": result["error"]}
            )

        # Return updated position (simplified - would need to fetch actual position)
        return Position(
            id=position_id,
            broker_position_id=str(position_id),
            account_id="",
            symbol=Symbol("UNKNOWN"),
            side=PositionSide.LONG,
            volume=Volume(Decimal("1.0")),
            open_price=Price(Decimal("1.0")),
            current_price=Price(Decimal("1.0")),
            open_time=datetime.utcnow(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            is_active=True,
        )

    async def get_quote(self, symbol: Symbol) -> Dict[str, Any]:
        """
        Get current market quote.

        Args:
            symbol: Symbol to get quote for

        Returns:
            Dict with symbol, bid, ask, timestamp

        Raises:
            BrokerConnectionError: If not connected
        """
        if not await self.is_connected():
            raise BrokerConnectionError(
                "Not connected to TopStep",
                context={"broker": "topstep"}
            )

        # ProjectX executor doesn't implement get_quote
        result = await self._executor.get_quote(symbol.value)

        if result is None:
            return {
                "symbol": symbol.value,
                "bid": 0.0,
                "ask": 0.0,
                "timestamp": datetime.utcnow(),
            }

        return result

    # Private conversion methods

    def _to_domain_position(self, executor_position) -> Position:
        """Convert ProjectX Position to domain Position"""
        return Position(
            id=PositionId(executor_position.id),
            broker_position_id=executor_position.id,
            account_id=executor_position.account_id,
            symbol=Symbol(executor_position.symbol),
            side=PositionSide.LONG if executor_position.side.lower() == "long" else PositionSide.SHORT,
            volume=Volume(Decimal(str(executor_position.size))),
            open_price=Price(Decimal(str(executor_position.entry_price))),
            current_price=Price(Decimal(str(executor_position.current_price))),
            open_time=executor_position.open_time,
            stop_loss=None,  # ProjectX Position doesn't include SL/TP
            take_profit=None,
            comment=executor_position.comment,
            magic_number=executor_position.magic_number,
            is_active=executor_position.is_active,
        )

    def _to_domain_order(self, executor_order: Dict) -> Order:
        """Convert ProjectX order dict to domain Order"""
        return Order(
            id=OrderId(executor_order.get("id", "")),
            broker_order_id=executor_order.get("id", ""),
            account_id=executor_order.get("account_id", ""),
            symbol=Symbol(executor_order.get("symbol", "")),
            order_type=self._map_executor_order_type(executor_order.get("type", "market")),
            volume=Volume(Decimal(str(executor_order.get("quantity", 0)))),
            price=Price(Decimal(str(executor_order["price"]))) if executor_order.get("price") else None,
            status=self._map_order_status(executor_order.get("status", "pending")),
            created_at=executor_order.get("created_at", datetime.utcnow()),
        )

    def _map_order_type_to_executor(self, order_type: OrderType) -> str:
        """Map domain OrderType to ProjectX executor format"""
        mapping = {
            OrderType.BUY: "market_buy",
            OrderType.SELL: "market_sell",
            OrderType.BUY_LIMIT: "buy_limit",
            OrderType.SELL_LIMIT: "sell_limit",
            OrderType.BUY_STOP: "buy_stop",
            OrderType.SELL_STOP: "sell_stop",
        }
        return mapping.get(order_type, "market_buy")

    def _map_executor_order_type(self, executor_type: str) -> OrderType:
        """Map ProjectX executor order type to domain OrderType"""
        mapping = {
            "market_buy": OrderType.BUY,
            "market_sell": OrderType.SELL,
            "buy_limit": OrderType.BUY_LIMIT,
            "sell_limit": OrderType.SELL_LIMIT,
            "buy_stop": OrderType.BUY_STOP,
            "sell_stop": OrderType.SELL_STOP,
        }
        return mapping.get(executor_type.lower(), OrderType.BUY)

    def _map_order_status(self, status: str) -> OrderStatus:
        """Map executor order status to domain OrderStatus"""
        status_lower = status.lower()
        if status_lower in ("submitted", "pending"):
            return OrderStatus.PENDING
        elif status_lower in ("filled", "executed"):
            return OrderStatus.EXECUTED
        elif status_lower == "cancelled":
            return OrderStatus.CANCELLED
        elif status_lower == "rejected":
            return OrderStatus.REJECTED
        elif status_lower == "partially_filled":
            return OrderStatus.PARTIALLY_FILLED
        else:
            return OrderStatus.PENDING
