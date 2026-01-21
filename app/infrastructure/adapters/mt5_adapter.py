"""
MT5 Broker Adapter

Implements BrokerPort interface for MetaTrader 5 broker integration.
Wraps MT5Executor and converts between domain value objects and executor primitives.
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime

from app.domain.ports.broker_port import BrokerPort
from app.domain.entities.order import Order
from app.domain.entities.position import Position
from app.domain.entities.trade import Trade
from app.domain.value_objects import Symbol, Volume, Price, OrderId, PositionId
from app.domain.enums import OrderType, OrderStatus, BrokerType, PositionSide, TradeStatus
from app.domain.exceptions import (
    BrokerConnectionError,
    InvalidOrderError,
    OrderNotFoundError,
    PositionNotFoundError,
)
from app.brokers.mt5_executor import MT5Executor

logger = logging.getLogger(__name__)


class MT5Adapter(BrokerPort):
    """
    MT5 broker adapter implementing domain BrokerPort.

    Wraps MT5Executor and converts between domain value objects
    and executor primitives. Supports both MetaAPI SDK and Manager API.
    """

    def __init__(
        self,
        executor: Optional[MT5Executor] = None,
        metaapi_token: Optional[str] = None,
        metaapi_account_id: Optional[str] = None,
    ):
        """
        Initialize MT5 adapter.

        Args:
            executor: Optional pre-configured MT5Executor instance.
                     If None, creates new executor on connect().
            metaapi_token: Optional MetaAPI token for SDK mode.
            metaapi_account_id: Optional MetaAPI account ID for SDK mode.
        """
        self._executor = executor
        self._account_id: Optional[str] = None
        self._metaapi_token = metaapi_token
        self._metaapi_account_id = metaapi_account_id

    @property
    def broker_type(self) -> BrokerType:
        """Return MT5 broker type"""
        return BrokerType.MT5

    @property
    def is_using_sdk(self) -> bool:
        """Check if using MetaAPI SDK mode."""
        return self._executor is not None and self._executor.is_using_sdk

    async def connect(self) -> bool:
        """
        Establish connection to MT5 (via MetaAPI SDK or Manager API).
        Returns True if connection successful.
        """
        try:
            if self._executor is None:
                self._executor = MT5Executor(
                    metaapi_token=self._metaapi_token,
                    metaapi_account_id=self._metaapi_account_id,
                )

            success = await self._executor.initialize()
            if not success:
                logger.warning("MT5 connection failed during initialization")
            else:
                mode = "MetaAPI SDK" if self._executor.is_using_sdk else "Manager API"
                logger.info(f"MT5 adapter connected via {mode}")
            return success
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            raise BrokerConnectionError(f"Failed to connect to MT5: {e}")

    async def disconnect(self) -> None:
        """Close MT5 broker connection"""
        if self._executor:
            await self._executor.disconnect()
            self._executor = None

    async def is_connected(self) -> bool:
        """Check if MT5 broker connection is active"""
        if self._executor is None:
            return False
        return self._executor.is_connected

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with MT5 broker using provided credentials.

        Credentials dict should contain:
        For MetaAPI SDK mode:
        - metaapi_token: MetaAPI API token
        - metaapi_account_id: MetaAPI account ID

        For Manager API mode (fallback):
        - account_id: MT5 account ID
        - login: MT5 account login (optional)
        - password: MT5 account password (optional)

        Returns:
            True if authentication successful
        """
        try:
            # Check for MetaAPI credentials
            if credentials.get("metaapi_token") and credentials.get("metaapi_account_id"):
                self._metaapi_token = credentials["metaapi_token"]
                self._metaapi_account_id = credentials["metaapi_account_id"]
                self._account_id = credentials["metaapi_account_id"]
            else:
                # Store account_id for later use (Manager API mode)
                self._account_id = credentials.get("account_id")

            # (Re)create executor with new credentials if needed
            if self._executor is None or (self._metaapi_token and not self._executor.is_using_sdk):
                self._executor = MT5Executor(
                    metaapi_token=self._metaapi_token,
                    metaapi_account_id=self._metaapi_account_id,
                )

            # Connect if not already connected
            if not await self.is_connected():
                return await self.connect()
            return True
        except Exception as e:
            logger.error(f"MT5 authentication error: {e}")
            return False

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information from MT5.

        Returns:
            Dict with: balance, equity, margin, free_margin, leverage, currency
        """
        self._ensure_connected()

        if not self._account_id:
            raise BrokerConnectionError("Account ID not set - call authenticate first")

        account = await self._executor.get_account_info(self._account_id)

        if account is None:
            raise BrokerConnectionError(f"Failed to get account info for {self._account_id}")

        return {
            "balance": float(account.balance),
            "equity": float(account.equity),
            "margin": float(account.margin),
            "free_margin": float(account.free_margin),
            "leverage": account.leverage,
            "currency": account.currency,
        }

    async def get_positions(self) -> List[Position]:
        """
        Get all open positions from MT5.

        Returns:
            List of Position domain entities
        """
        self._ensure_connected()

        positions_data = await self._executor.get_positions(self._account_id)
        return [self._to_domain_position(p) for p in positions_data]

    async def get_orders(self) -> List[Order]:
        """
        Get all pending orders from MT5.

        Returns:
            List of Order domain entities
        """
        self._ensure_connected()

        # MT5Executor has get_orders but returns empty list
        # This is a known limitation in the executor
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
        Place a new order on MT5.

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
            InvalidOrderError: Order validation failed
            BrokerConnectionError: Failed to place order
        """
        self._ensure_connected()

        if not self._account_id:
            raise BrokerConnectionError("Account ID not set - call authenticate first")

        # Convert domain OrderType to MT5 order type string
        mt5_order_type = self._to_mt5_order_type(order_type)

        # Import OrderRequest model
        from app.models.pydantic_schemas import OrderRequest

        order_request = OrderRequest(
            account_id=self._account_id,
            symbol=symbol.value,
            order_type=mt5_order_type,
            quantity=float(volume.value),
            price=float(price.value) if price else None,
            stop_loss=float(stop_loss.value) if stop_loss else None,
            take_profit=float(take_profit.value) if take_profit else None,
            comment=comment or "",
        )

        response = await self._executor.place_order(order_request)

        if not response.success:
            raise InvalidOrderError(f"MT5 order failed: {response.error}")

        return self._order_response_to_domain(response, symbol, order_type, volume)

    async def modify_order(
        self,
        order_id: OrderId,
        price: Optional[Price] = None,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
    ) -> Order:
        """
        Modify an existing pending order on MT5.

        Args:
            order_id: Order identifier
            price: New limit/stop price
            stop_loss: New stop loss price
            take_profit: New take profit price

        Returns:
            Updated Order domain entity

        Raises:
            OrderNotFoundError: Order not found
        """
        self._ensure_connected()

        modifications = {}
        if price:
            modifications["price"] = float(price.value)
        if stop_loss:
            modifications["stop_loss"] = float(stop_loss.value)
        if take_profit:
            modifications["take_profit"] = float(take_profit.value)

        response = await self._executor.modify_order(order_id.value, modifications)

        if not response.success:
            if "not found" in response.error.lower():
                raise OrderNotFoundError(f"Order {order_id.value} not found")
            raise InvalidOrderError(f"MT5 order modification failed: {response.error}")

        # Return a basic order entity - in production would fetch full order details
        return Order(
            id=order_id,
            broker_order_id=response.order_id,
            account_id=self._account_id,
            symbol=Symbol("UNKNOWN"),  # Would need to fetch from order details
            order_type=OrderType.BUY,  # Would need to fetch from order details
            volume=Volume(Decimal("0.01")),  # Would need to fetch from order details
            status=OrderStatus.PENDING,
        )

    async def cancel_order(self, order_id: OrderId) -> None:
        """
        Cancel a pending order on MT5.

        Args:
            order_id: Order identifier

        Raises:
            OrderNotFoundError: Order not found
        """
        self._ensure_connected()

        response = await self._executor.cancel_order(order_id.value)

        if not response.success:
            if "not found" in response.error.lower():
                raise OrderNotFoundError(f"Order {order_id.value} not found")
            raise InvalidOrderError(f"MT5 order cancellation failed: {response.error}")

    async def close_position(
        self,
        position_id: PositionId,
        volume: Optional[Volume] = None,
    ) -> Trade:
        """
        Close a position (fully or partially) on MT5.

        Args:
            position_id: Position identifier
            volume: Optional volume to close (None = close all)

        Returns:
            Resulting Trade domain entity

        Raises:
            PositionNotFoundError: Position not found
        """
        self._ensure_connected()

        close_volume = float(volume.value) if volume else None

        response = await self._executor.close_position(position_id.value, close_volume)

        if not response.success:
            if "not found" in response.error.lower():
                raise PositionNotFoundError(f"Position {position_id.value} not found")
            raise InvalidOrderError(f"MT5 position close failed: {response.error}")

        return self._trade_response_to_domain(response)

    async def modify_position(
        self,
        position_id: PositionId,
        stop_loss: Optional[Price] = None,
        take_profit: Optional[Price] = None,
    ) -> Position:
        """
        Modify position stop loss / take profit on MT5.

        Args:
            position_id: Position identifier
            stop_loss: New stop loss price
            take_profit: New take profit price

        Returns:
            Updated Position domain entity

        Raises:
            PositionNotFoundError: Position not found
        """
        self._ensure_connected()

        result = await self._executor.modify_position(
            position_id.value,
            stop_loss=float(stop_loss.value) if stop_loss else None,
            take_profit=float(take_profit.value) if take_profit else None,
        )

        if "error" in result:
            if "not found" in result["error"].lower():
                raise PositionNotFoundError(f"Position {position_id.value} not found")
            raise InvalidOrderError(f"MT5 position modification failed: {result['error']}")

        # Would need to fetch updated position - return basic entity
        positions = await self.get_positions()
        for pos in positions:
            if pos.id.value == position_id.value:
                return pos

        raise PositionNotFoundError(f"Position {position_id.value} not found after modification")

    async def get_quote(self, symbol: Symbol) -> Dict[str, Any]:
        """
        Get current market quote from MT5.

        Args:
            symbol: Trading symbol

        Returns:
            Dict with: symbol, bid, ask, timestamp
        """
        self._ensure_connected()

        quote = await self._executor.get_quote(symbol.value)

        if quote is None:
            return {
                "symbol": symbol.value,
                "bid": 0.0,
                "ask": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        return quote

    # Private helper methods

    def _ensure_connected(self) -> None:
        """Raise exception if not connected"""
        if self._executor is None or not self._executor.is_connected:
            raise BrokerConnectionError("MT5 not connected - call connect() first")

    def _to_mt5_order_type(self, order_type: OrderType) -> str:
        """Convert domain OrderType to MT5 order type string"""
        mapping = {
            OrderType.BUY: "market_buy",
            OrderType.SELL: "market_sell",
            OrderType.BUY_LIMIT: "buy_limit",
            OrderType.SELL_LIMIT: "sell_limit",
            OrderType.BUY_STOP: "buy_stop",
            OrderType.SELL_STOP: "sell_stop",
        }
        return mapping.get(order_type, "market_buy")

    def _to_domain_position(self, pos_data) -> Position:
        """Convert MT5 Position model to domain Position entity"""
        # Determine position side
        side = PositionSide.LONG if pos_data.side.lower() == "buy" else PositionSide.SHORT

        return Position(
            id=PositionId(pos_data.id),
            broker_position_id=pos_data.id,
            account_id=pos_data.account_id,
            symbol=Symbol(pos_data.symbol),
            side=side,
            volume=Volume(Decimal(str(pos_data.size))),
            open_price=Price(Decimal(str(pos_data.entry_price))),
            current_price=Price(Decimal(str(pos_data.current_price))),
            open_time=pos_data.open_time,
            stop_loss=Price(Decimal(str(pos_data.entry_price))) if hasattr(pos_data, 'stop_loss') and pos_data.stop_loss else None,
            take_profit=Price(Decimal(str(pos_data.entry_price))) if hasattr(pos_data, 'take_profit') and pos_data.take_profit else None,
            comment=pos_data.comment if hasattr(pos_data, 'comment') else None,
            magic_number=pos_data.magic_number if hasattr(pos_data, 'magic_number') else None,
            is_active=pos_data.is_active,
        )

    def _to_domain_order(self, order_data) -> Order:
        """Convert MT5 order data to domain Order entity"""
        # This is placeholder - MT5Executor doesn't return proper order data yet
        return Order(
            id=OrderId(str(order_data.get("id", "unknown"))),
            broker_order_id=str(order_data.get("id", "unknown")),
            account_id=self._account_id or "unknown",
            symbol=Symbol(order_data.get("symbol", "UNKNOWN")),
            order_type=OrderType.BUY,
            volume=Volume(Decimal(str(order_data.get("volume", "0.01")))),
            status=OrderStatus.PENDING,
        )

    def _order_response_to_domain(
        self,
        response,
        symbol: Symbol,
        order_type: OrderType,
        volume: Volume,
    ) -> Order:
        """Convert OrderResponse to domain Order entity"""
        status_mapping = {
            "filled": OrderStatus.EXECUTED,
            "pending": OrderStatus.PENDING,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
        }

        status = status_mapping.get(response.status, OrderStatus.PENDING)

        return Order(
            id=OrderId(response.order_id),
            broker_order_id=response.order_id,
            account_id=self._account_id,
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            status=status,
            filled_volume=Decimal(str(response.filled_quantity)) if hasattr(response, 'filled_quantity') else Decimal("0"),
            created_at=response.timestamp if hasattr(response, 'timestamp') else datetime.utcnow(),
        )

    def _trade_response_to_domain(self, response) -> Trade:
        """Convert TradeResponse to domain Trade entity"""
        # Determine order type from side
        order_type = OrderType.BUY if response.side.lower() == "buy" else OrderType.SELL

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
        )
