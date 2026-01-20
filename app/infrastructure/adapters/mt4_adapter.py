"""
MT4 Broker Adapter

Implements BrokerPort interface for MT4 broker integration.
Wraps MT4Executor and provides domain-typed interface using value objects.
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime

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
    InvalidOrderError
)
from app.brokers.mt4_executor import MT4Executor

logger = logging.getLogger(__name__)


class MT4Adapter(BrokerPort):
    """
    MT4 broker adapter implementing domain BrokerPort.

    Wraps MT4Executor and converts between domain value objects
    and executor primitives. Uses MT4 Manager API via REST bridge.
    """

    def __init__(self, executor: Optional[MT4Executor] = None):
        """
        Initialize MT4 adapter.

        Args:
            executor: Optional pre-configured MT4Executor instance.
                     If None, creates new executor on connect().
        """
        self._executor = executor
        self._account_id: Optional[str] = None

    @property
    def broker_type(self) -> BrokerType:
        """Return the broker type this adapter handles"""
        return BrokerType.MT4

    async def connect(self) -> bool:
        """
        Establish connection to MT4 Manager API.
        Returns True if connection successful.
        """
        try:
            if self._executor is None:
                self._executor = MT4Executor()

            result = await self._executor.initialize()
            if not result:
                logger.error("MT4 connection failed during initialization")
            return result
        except Exception as e:
            logger.error(f"MT4 connection error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=str(e),
                context={"error": str(e)}
            )

    async def disconnect(self) -> None:
        """Close MT4 connection"""
        if self._executor:
            await self._executor.disconnect()

    async def is_connected(self) -> bool:
        """Check if MT4 connection is active"""
        if self._executor is None:
            return False
        return self._executor.is_connected()

    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """
        Authenticate with MT4 using provided credentials.

        Credentials dict should contain:
        - login: MT4 account login
        - password: MT4 account password
        - server: Optional server name

        Returns True if authentication successful.
        """
        try:
            # Store account_id for later use
            self._account_id = str(credentials.get("login"))

            # MT4Executor authentication happens during initialize()
            # which uses credentials from config
            if not await self.is_connected():
                return await self.connect()
            return True
        except Exception as e:
            logger.error(f"MT4 authentication error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=f"Authentication failed: {e}",
                account_id=self._account_id,
                context={"error": str(e)}
            )

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.
        Returns dict with: balance, equity, margin, free_margin, leverage, currency
        """
        if not self._account_id:
            raise BrokerConnectionError(
                broker="MT4",
                message="No account authenticated"
            )

        try:
            account = await self._executor.get_account_info(self._account_id)
            if not account:
                raise BrokerConnectionError(
                    broker="MT4",
                    message=f"Failed to retrieve account info for {self._account_id}"
                )

            return {
                "balance": float(account.balance),
                "equity": float(account.equity),
                "margin": float(account.margin),
                "free_margin": float(account.free_margin),
                "leverage": account.leverage,
                "currency": account.currency,
            }
        except Exception as e:
            logger.error(f"MT4 get_account_info error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=f"Failed to get account info: {e}",
                account_id=self._account_id,
                context={"error": str(e)}
            )

    async def get_positions(self) -> List[Position]:
        """
        Get all open positions.
        Returns list of Position domain entities.
        """
        try:
            positions_data = await self._executor.get_positions(self._account_id)
            return [self._to_domain_position(p) for p in positions_data]
        except Exception as e:
            logger.error(f"MT4 get_positions error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=f"Failed to get positions: {e}",
                account_id=self._account_id,
                context={"error": str(e)}
            )

    async def get_orders(self) -> List[Order]:
        """
        Get all pending orders.
        Returns list of Order domain entities.
        """
        try:
            orders_data = await self._executor.get_orders()
            return [self._to_domain_order(o) for o in orders_data]
        except Exception as e:
            logger.error(f"MT4 get_orders error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=f"Failed to get orders: {e}",
                account_id=self._account_id,
                context={"error": str(e)}
            )

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
        if not self._account_id:
            raise BrokerConnectionError(
                broker="MT4",
                message="No account authenticated"
            )

        try:
            # Convert domain OrderType to MT4 order type string
            mt4_order_type = self._to_mt4_order_type(order_type)

            # Create order request using MT4Executor's expected format
            from app.models.pydantic_schemas import OrderRequest

            order_request = OrderRequest(
                account_id=self._account_id,
                symbol=symbol.value,
                order_type=mt4_order_type,
                quantity=float(volume.value),
                price=float(price.value) if price else None,
                stop_loss=float(stop_loss.value) if stop_loss else None,
                take_profit=float(take_profit.value) if take_profit else None,
                comment=comment or "",
            )

            response = await self._executor.place_order(order_request)

            if not response.success:
                raise InvalidOrderError(
                    message=response.error or "Order placement failed",
                    context={"symbol": symbol.value, "order_type": order_type.value}
                )

            # Convert response to domain Order entity
            return Order(
                id=OrderId(response.order_id),
                broker_order_id=response.order_id,
                account_id=self._account_id,
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                status=OrderStatus.EXECUTED if response.status == "filled" else OrderStatus.PENDING,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                filled_volume=Decimal(str(response.filled_quantity)) if response.filled_quantity else Decimal("0"),
                comment=comment,
                created_at=response.timestamp or datetime.utcnow(),
            )

        except InvalidOrderError:
            raise
        except Exception as e:
            logger.error(f"MT4 place_order error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=f"Failed to place order: {e}",
                account_id=self._account_id,
                context={"error": str(e), "symbol": symbol.value}
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
        Returns updated Order domain entity.
        Raises: OrderNotFoundError, BusinessRuleViolation
        """
        try:
            modifications = {}
            if price:
                modifications["price"] = float(price.value)
            if stop_loss:
                modifications["stop_loss"] = float(stop_loss.value)
            if take_profit:
                modifications["take_profit"] = float(take_profit.value)

            response = await self._executor.modify_order(order_id.value, modifications)

            if not response.success:
                raise OrderNotFoundError(
                    order_id=order_id.value,
                    context={"error": response.error}
                )

            # Return a basic order entity (MT4 doesn't return full order details on modify)
            return Order(
                id=order_id,
                broker_order_id=order_id.value,
                account_id=self._account_id or "",
                symbol=Symbol("UNKNOWN"),  # Not provided in response
                order_type=OrderType.BUY,  # Not provided in response
                volume=Volume(Decimal("0")),  # Not provided in response
                status=OrderStatus.PENDING,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                updated_at=response.timestamp or datetime.utcnow(),
            )

        except OrderNotFoundError:
            raise
        except Exception as e:
            logger.error(f"MT4 modify_order error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=f"Failed to modify order: {e}",
                account_id=self._account_id,
                context={"error": str(e), "order_id": order_id.value}
            )

    async def cancel_order(self, order_id: OrderId) -> None:
        """
        Cancel a pending order.
        Raises: OrderNotFoundError, BusinessRuleViolation
        """
        try:
            response = await self._executor.cancel_order(order_id.value)

            if not response.success:
                raise OrderNotFoundError(
                    order_id=order_id.value,
                    context={"error": response.error}
                )

        except OrderNotFoundError:
            raise
        except Exception as e:
            logger.error(f"MT4 cancel_order error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=f"Failed to cancel order: {e}",
                account_id=self._account_id,
                context={"error": str(e), "order_id": order_id.value}
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
        try:
            response = await self._executor.close_position(
                position_id=position_id.value,
                quantity=float(volume.value) if volume else None,
            )

            if not response.success:
                raise PositionNotFoundError(
                    position_id=position_id.value,
                    context={"error": response.error}
                )

            # Convert response to domain Trade entity
            return self._to_domain_trade(response)

        except PositionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"MT4 close_position error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=f"Failed to close position: {e}",
                account_id=self._account_id,
                context={"error": str(e), "position_id": position_id.value}
            )

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
        try:
            result = await self._executor.modify_position(
                position_id=position_id.value,
                stop_loss=float(stop_loss.value) if stop_loss else None,
                take_profit=float(take_profit.value) if take_profit else None,
            )

            if "error" in result:
                raise PositionNotFoundError(
                    position_id=position_id.value,
                    context={"error": result["error"]}
                )

            # Convert result to domain Position entity
            return self._to_domain_position(result)

        except PositionNotFoundError:
            raise
        except Exception as e:
            logger.error(f"MT4 modify_position error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=f"Failed to modify position: {e}",
                account_id=self._account_id,
                context={"error": str(e), "position_id": position_id.value}
            )

    async def get_quote(self, symbol: Symbol) -> Dict[str, Any]:
        """
        Get current market quote.
        Returns dict with: symbol, bid, ask, timestamp
        """
        try:
            quote = await self._executor.get_quote(symbol.value)
            if not quote:
                raise BrokerConnectionError(
                    broker="MT4",
                    message=f"Failed to get quote for {symbol.value}"
                )
            return quote
        except Exception as e:
            logger.error(f"MT4 get_quote error: {e}")
            raise BrokerConnectionError(
                broker="MT4",
                message=f"Failed to get quote: {e}",
                account_id=self._account_id,
                context={"error": str(e), "symbol": symbol.value}
            )

    # Private conversion methods

    def _to_mt4_order_type(self, order_type: OrderType) -> str:
        """Convert domain OrderType to MT4 order type string"""
        mapping = {
            OrderType.BUY: "market_buy",
            OrderType.SELL: "market_sell",
            OrderType.BUY_LIMIT: "buy_limit",
            OrderType.SELL_LIMIT: "sell_limit",
            OrderType.BUY_STOP: "buy_stop",
            OrderType.SELL_STOP: "sell_stop",
        }
        return mapping.get(order_type, "market_buy")

    def _to_domain_position(self, data: Any) -> Position:
        """Convert MT4 position data to domain Position entity"""
        # Handle both dict and Pydantic model
        if hasattr(data, 'dict'):
            data = data.dict()

        return Position(
            id=PositionId(str(data.get("id", data.get("order")))),
            broker_position_id=str(data.get("id", data.get("order"))),
            account_id=str(data.get("account_id", data.get("login", self._account_id))),
            symbol=Symbol(data["symbol"]),
            side=PositionSide.LONG if data["side"] == "buy" else PositionSide.SHORT,
            volume=Volume(Decimal(str(data["size"]))),
            open_price=Price(Decimal(str(data["entry_price"]))),
            current_price=Price(Decimal(str(data.get("current_price", data["entry_price"])))),
            open_time=data.get("open_time", datetime.utcnow()),
            stop_loss=Price(Decimal(str(data["stop_loss"]))) if data.get("stop_loss") else None,
            take_profit=Price(Decimal(str(data["take_profit"]))) if data.get("take_profit") else None,
            margin=Money(abs(Decimal(str(data.get("margin", 0))))),
            commission=Money(abs(Decimal(str(data.get("commission", 0))))),
            comment=data.get("comment"),
            magic_number=data.get("magic_number"),
            is_active=data.get("is_active", True),
        )

    def _to_domain_order(self, data: Dict[str, Any]) -> Order:
        """Convert MT4 order data to domain Order entity"""
        # Map MT4 cmd to domain OrderType
        cmd = data.get("cmd", 0)
        order_type_map = {
            0: OrderType.BUY,
            1: OrderType.SELL,
            2: OrderType.BUY_LIMIT,
            3: OrderType.SELL_LIMIT,
            4: OrderType.BUY_STOP,
            5: OrderType.SELL_STOP,
        }

        return Order(
            id=OrderId(str(data.get("order", data.get("ticket")))),
            broker_order_id=str(data.get("order", data.get("ticket"))),
            account_id=str(data.get("login", self._account_id)),
            symbol=Symbol(data["symbol"]),
            order_type=order_type_map.get(cmd, OrderType.BUY),
            volume=Volume(Decimal(str(data["volume"]))),
            status=OrderStatus.PENDING,
            price=Price(Decimal(str(data["price"]))) if data.get("price") else None,
            stop_loss=Price(Decimal(str(data["sl"]))) if data.get("sl") else None,
            take_profit=Price(Decimal(str(data["tp"]))) if data.get("tp") else None,
            comment=data.get("comment"),
            magic_number=data.get("magic"),
            created_at=data.get("open_time", datetime.utcnow()),
        )

    def _to_domain_trade(self, response: Any) -> Trade:
        """Convert MT4 trade response to domain Trade entity"""
        # Handle TradeResponse pydantic model
        if hasattr(response, 'dict'):
            data = response.dict()
        else:
            data = response

        order_type = OrderType.BUY if data["side"] == "buy" else OrderType.SELL

        return Trade(
            trade_id=str(data.get("trade_id", data.get("order_id"))),
            broker_trade_id=str(data.get("trade_id")),
            account_id=self._account_id or "",
            symbol=Symbol(data["symbol"]),
            order_type=order_type,
            volume=Volume(Decimal(str(data["quantity"]))),
            open_price=Price(Decimal(str(data["price"]))),
            open_time=data.get("timestamp", datetime.utcnow()),
            close_price=Price(Decimal(str(data["price"]))),
            close_time=data.get("timestamp", datetime.utcnow()),
            status=TradeStatus.CLOSED,
            commission=Money(abs(Decimal(str(data.get("commission", 0))))),
            realized_pnl=Money(abs(Decimal(str(data.get("pnl", 0))))) if data.get("pnl", 0) >= 0 else Money(Decimal("0")),
        )
