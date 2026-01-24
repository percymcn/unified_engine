"""
MetaAPI SDK Service
Wraps official metaapi-cloud-sdk for MT4/MT5 trading.

Uses the official metaapi-cloud-sdk for MetaTrader integration.
Provides async-first interface matching existing executor patterns.
Single API for both MT4 and MT5 platforms via cloud service.
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import SDK - graceful fallback if not installed
try:
    from metaapi_cloud_sdk import MetaApi
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    MetaApi = None
    logger.warning("metaapi-cloud-sdk not installed, MetaAPISDKService unavailable")


class MetaAPISDKService:
    """
    Service wrapper for metaapi-cloud-sdk.

    Manages SDK lifecycle, authentication, and provides
    unified interface for trading operations.

    Works with both MT4 and MT5 accounts via MetaAPI cloud service.
    """

    def __init__(
        self,
        token: str,
        account_id: str,
        application: str = "tradeflow"
    ):
        """
        Initialize MetaAPI SDK service.

        Args:
            token: MetaAPI API token from https://app.metaapi.cloud/token
            account_id: MetaAPI account ID (MT4 or MT5 account provisioned in MetaAPI)
            application: Application name for MetaAPI (default: tradeflow)
        """
        self.token = token
        self.account_id = account_id
        self.application = application
        self._api: Optional[Any] = None  # MetaApi instance
        self._account: Optional[Any] = None  # MetatraderAccount
        self._connection: Optional[Any] = None  # StreamingConnection
        self._is_connected = False

    async def connect(self) -> bool:
        """
        Initialize SDK connection and synchronize with MetaAPI.

        Returns:
            True if connection successful, False otherwise
        """
        if not SDK_AVAILABLE:
            logger.error("metaapi-cloud-sdk not available")
            return False

        try:
            # Create MetaApi instance
            self._api = MetaApi(token=self.token, application=self.application)

            # Get account
            self._account = await self._api.metatrader_account_api.get_account(self.account_id)

            # Ensure account is deployed
            if self._account.state != 'DEPLOYED':
                logger.info(f"Deploying MetaAPI account {self.account_id}...")
                await self._account.deploy()

            # Wait for account to connect to broker
            logger.info(f"Waiting for MetaAPI account to connect to broker...")
            await self._account.wait_connected()

            # Get streaming connection
            self._connection = self._account.get_streaming_connection()
            await self._connection.connect()

            # Wait for synchronization
            logger.info("Waiting for MetaAPI terminal state synchronization...")
            await self._connection.wait_synchronized()

            self._is_connected = True
            logger.info(f"MetaAPI SDK connected: account {self.account_id}")
            return True

        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "Unauthorized" in error_msg or "invalid token" in error_msg.lower():
                logger.error(f"MetaAPI authentication failed: Invalid token. Get valid token from https://app.metaapi.cloud/token")
            elif "404" in error_msg or "not found" in error_msg.lower():
                logger.error(f"MetaAPI account not found: account_id={self.account_id}. Verify account ID in MetaAPI dashboard")
            elif "network" in error_msg.lower() or "connection" in error_msg.lower() or "timeout" in error_msg.lower() or "DNS" in error_msg:
                logger.error(f"MetaAPI network error: {error_msg}. Check internet connection, DNS, and firewall settings")
            elif "deploy" in error_msg.lower() or "state" in error_msg.lower():
                logger.error(f"MetaAPI account deployment error: {error_msg}. Check account state in MetaAPI dashboard")
            else:
                logger.error(f"MetaAPI SDK connection failed: {e}")
            self._is_connected = False
            return False

    async def disconnect(self) -> None:
        """Close SDK connections."""
        if self._connection:
            try:
                await self._connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {e}")
            self._connection = None

        if self._account and self._account.state == 'DEPLOYED':
            try:
                # Optionally undeploy to save resources
                # await self._account.undeploy()
                pass
            except Exception as e:
                logger.warning(f"Error undeploying account: {e}")

        self._api = None
        self._account = None
        self._is_connected = False
        logger.info("MetaAPI SDK disconnected")

    @property
    def is_connected(self) -> bool:
        """Check if SDK is connected."""
        return self._is_connected and self._connection is not None

    @property
    def terminal_state(self) -> Optional[Any]:
        """Get terminal state for direct access to positions/orders/quotes."""
        if self._connection:
            return self._connection.terminal_state
        return None

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information from terminal state.

        Returns:
            Dict with account details (balance, equity, margin, etc.)

        Raises:
            RuntimeError: If not connected
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        account_info = self._connection.terminal_state.account_information
        return {
            "broker": account_info.get("broker", ""),
            "currency": account_info.get("currency", "USD"),
            "server": account_info.get("server", ""),
            "balance": float(account_info.get("balance", 0)),
            "equity": float(account_info.get("equity", 0)),
            "margin": float(account_info.get("margin", 0)),
            "free_margin": float(account_info.get("freeMargin", account_info.get("margin_free", 0))),
            "leverage": int(account_info.get("leverage", 1)),
            "name": account_info.get("name", ""),
            "login": str(account_info.get("login", "")),
            "platform": account_info.get("platform", "mt4"),  # mt4 or mt5
            "credit": float(account_info.get("credit", 0)),
            "margin_level": float(account_info.get("marginLevel", 0)),
            "trade_allowed": account_info.get("tradeAllowed", True),
        }

    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get open positions from terminal state.

        Returns:
            List of position dicts
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        positions = self._connection.terminal_state.positions
        return [
            {
                "id": str(pos.get("id", "")),
                "symbol": pos.get("symbol", ""),
                "type": pos.get("type", ""),  # POSITION_TYPE_BUY or POSITION_TYPE_SELL
                "side": "buy" if pos.get("type") == "POSITION_TYPE_BUY" else "sell",
                "volume": float(pos.get("volume", 0)),
                "open_price": float(pos.get("openPrice", 0)),
                "current_price": float(pos.get("currentPrice", 0)),
                "stop_loss": float(pos.get("stopLoss", 0)) if pos.get("stopLoss") else None,
                "take_profit": float(pos.get("takeProfit", 0)) if pos.get("takeProfit") else None,
                "profit": float(pos.get("profit", 0)),
                "commission": float(pos.get("commission", 0)),
                "swap": float(pos.get("swap", 0)),
                "unrealized_pnl": float(pos.get("unrealizedProfit", pos.get("profit", 0))),
                "magic": pos.get("magic", 0),
                "comment": pos.get("comment", ""),
                "open_time": pos.get("time", ""),
                "update_time": pos.get("updateTime", ""),
                "platform": pos.get("platform", "mt4"),
            }
            for pos in positions
        ]

    async def get_deal_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get deal history (closed trades).
        
        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of deal dictionaries
        """
        if not self._connection:
            raise RuntimeError("Not connected")
        
        # MetaAPI SDK provides deal history through terminal state
        deals = self._connection.terminal_state.deals
        
        deal_list = [
            {
                "id": str(deal.get("id", "")),
                "order_id": str(deal.get("orderId", "")),
                "position_id": str(deal.get("positionId", "")),
                "symbol": deal.get("symbol", ""),
                "type": deal.get("type", ""),
                "entry_type": deal.get("entryType", ""),
                "volume": float(deal.get("volume", 0)),
                "price": float(deal.get("price", 0)),
                "commission": float(deal.get("commission", 0)),
                "swap": float(deal.get("swap", 0)),
                "profit": float(deal.get("profit", 0)),
                "time": deal.get("time", ""),
                "broker_time": deal.get("brokerTime", ""),
            }
            for deal in deals
        ]
        
        # Filter by time if provided
        if start_time or end_time:
            filtered_deals = []
            for deal in deal_list:
                deal_time_str = deal.get("time", deal.get("broker_time", ""))
                if not deal_time_str:
                    continue
                
                try:
                    # Parse deal time
                    if isinstance(deal_time_str, (int, float)):
                        deal_time = datetime.fromtimestamp(deal_time_str)
                    elif 'T' in str(deal_time_str) or 'Z' in str(deal_time_str):
                        deal_time_str_clean = str(deal_time_str).replace('Z', '+00:00')
                        deal_time = datetime.fromisoformat(deal_time_str_clean)
                    else:
                        continue
                    
                    # Apply filters
                    if start_time and deal_time < start_time:
                        continue
                    if end_time and deal_time > end_time:
                        continue
                    
                    filtered_deals.append(deal)
                except Exception:
                    continue
            
            return filtered_deals
        
        return deal_list

    async def get_orders(self) -> List[Dict[str, Any]]:
        """
        Get pending orders from terminal state.

        Returns:
            List of order dicts
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        orders = self._connection.terminal_state.orders
        return [
            {
                "id": str(order.get("id", "")),
                "symbol": order.get("symbol", ""),
                "type": order.get("type", ""),  # ORDER_TYPE_BUY_LIMIT, etc.
                "volume": float(order.get("volume", 0)),
                "open_price": float(order.get("openPrice", 0)),
                "stop_loss": float(order.get("stopLoss", 0)) if order.get("stopLoss") else None,
                "take_profit": float(order.get("takeProfit", 0)) if order.get("takeProfit") else None,
                "magic": order.get("magic", 0),
                "comment": order.get("comment", ""),
                "state": order.get("state", ""),
                "open_time": order.get("time", ""),
            }
            for order in orders
        ]

    async def create_market_buy_order(
        self,
        symbol: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: Optional[str] = None,
        magic: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Place market buy order.

        Args:
            symbol: Trading symbol
            volume: Order volume in lots
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            comment: Optional order comment
            magic: Optional magic number

        Returns:
            Dict with order result (orderId, positionId, success, etc.)
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        options = {}
        if comment:
            options["comment"] = comment
        if magic is not None:
            options["magic"] = magic

        try:
            result = await self._connection.create_market_buy_order(
                symbol=symbol,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                options=options if options else None
            )
            return {
                "success": True,
                "order_id": str(result.get("orderId", "")),
                "position_id": str(result.get("positionId", "")),
                "status": "filled",
                "string_code": result.get("stringCode", ""),
                "message": result.get("message", ""),
            }
        except Exception as e:
            logger.error(f"Market buy order failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_market_sell_order(
        self,
        symbol: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: Optional[str] = None,
        magic: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Place market sell order.

        Args:
            symbol: Trading symbol
            volume: Order volume in lots
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            comment: Optional order comment
            magic: Optional magic number

        Returns:
            Dict with order result
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        options = {}
        if comment:
            options["comment"] = comment
        if magic is not None:
            options["magic"] = magic

        try:
            result = await self._connection.create_market_sell_order(
                symbol=symbol,
                volume=volume,
                stop_loss=stop_loss,
                take_profit=take_profit,
                options=options if options else None
            )
            return {
                "success": True,
                "order_id": str(result.get("orderId", "")),
                "position_id": str(result.get("positionId", "")),
                "status": "filled",
                "string_code": result.get("stringCode", ""),
                "message": result.get("message", ""),
            }
        except Exception as e:
            logger.error(f"Market sell order failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_limit_buy_order(
        self,
        symbol: str,
        volume: float,
        open_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: Optional[str] = None,
        magic: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Place buy limit order.

        Args:
            symbol: Trading symbol
            volume: Order volume in lots
            open_price: Limit price
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            comment: Optional order comment
            magic: Optional magic number

        Returns:
            Dict with order result
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        options = {}
        if comment:
            options["comment"] = comment
        if magic is not None:
            options["magic"] = magic

        try:
            result = await self._connection.create_limit_buy_order(
                symbol=symbol,
                volume=volume,
                open_price=open_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                options=options if options else None
            )
            return {
                "success": True,
                "order_id": str(result.get("orderId", "")),
                "status": "pending",
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Limit buy order failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_limit_sell_order(
        self,
        symbol: str,
        volume: float,
        open_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: Optional[str] = None,
        magic: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Place sell limit order.
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        options = {}
        if comment:
            options["comment"] = comment
        if magic is not None:
            options["magic"] = magic

        try:
            result = await self._connection.create_limit_sell_order(
                symbol=symbol,
                volume=volume,
                open_price=open_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                options=options if options else None
            )
            return {
                "success": True,
                "order_id": str(result.get("orderId", "")),
                "status": "pending",
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Limit sell order failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_stop_buy_order(
        self,
        symbol: str,
        volume: float,
        open_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: Optional[str] = None,
        magic: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Place buy stop order.
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        options = {}
        if comment:
            options["comment"] = comment
        if magic is not None:
            options["magic"] = magic

        try:
            result = await self._connection.create_stop_buy_order(
                symbol=symbol,
                volume=volume,
                open_price=open_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                options=options if options else None
            )
            return {
                "success": True,
                "order_id": str(result.get("orderId", "")),
                "status": "pending",
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Stop buy order failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_stop_sell_order(
        self,
        symbol: str,
        volume: float,
        open_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: Optional[str] = None,
        magic: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Place sell stop order.
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        options = {}
        if comment:
            options["comment"] = comment
        if magic is not None:
            options["magic"] = magic

        try:
            result = await self._connection.create_stop_sell_order(
                symbol=symbol,
                volume=volume,
                open_price=open_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                options=options if options else None
            )
            return {
                "success": True,
                "order_id": str(result.get("orderId", "")),
                "status": "pending",
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Stop sell order failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_stop_limit_buy_order(
        self,
        symbol: str,
        volume: float,
        open_price: float,
        stop_limit_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: Optional[str] = None,
        magic: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Place buy stop limit order (MT5 only).
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        options = {"stopLimitPrice": stop_limit_price}
        if comment:
            options["comment"] = comment
        if magic is not None:
            options["magic"] = magic

        try:
            result = await self._connection.create_stop_limit_buy_order(
                symbol=symbol,
                volume=volume,
                open_price=open_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                options=options
            )
            return {
                "success": True,
                "order_id": str(result.get("orderId", "")),
                "status": "pending",
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Stop limit buy order failed: {e}")
            return {"success": False, "error": str(e)}

    async def create_stop_limit_sell_order(
        self,
        symbol: str,
        volume: float,
        open_price: float,
        stop_limit_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: Optional[str] = None,
        magic: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Place sell stop limit order (MT5 only).
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        options = {"stopLimitPrice": stop_limit_price}
        if comment:
            options["comment"] = comment
        if magic is not None:
            options["magic"] = magic

        try:
            result = await self._connection.create_stop_limit_sell_order(
                symbol=symbol,
                volume=volume,
                open_price=open_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                options=options
            )
            return {
                "success": True,
                "order_id": str(result.get("orderId", "")),
                "status": "pending",
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Stop limit sell order failed: {e}")
            return {"success": False, "error": str(e)}

    async def modify_position(
        self,
        position_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Modify position stop loss / take profit.

        Args:
            position_id: Position ID to modify
            stop_loss: New stop loss price (or None to keep)
            take_profit: New take profit price (or None to keep)

        Returns:
            Dict with modification result
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        try:
            result = await self._connection.modify_position(
                position_id=position_id,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            return {
                "success": True,
                "position_id": position_id,
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Position modification failed: {e}")
            return {"success": False, "error": str(e)}

    async def close_position(
        self,
        position_id: str,
        volume: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Close position (fully or partially).

        Args:
            position_id: Position ID to close
            volume: Optional volume for partial close (None = close all)

        Returns:
            Dict with close result
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        try:
            if volume:
                result = await self._connection.close_position_partially(
                    position_id=position_id,
                    volume=volume
                )
            else:
                result = await self._connection.close_position(position_id=position_id)

            return {
                "success": True,
                "position_id": position_id,
                "order_id": str(result.get("orderId", "")),
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Position close failed: {e}")
            return {"success": False, "error": str(e)}

    async def close_positions_by_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Close all positions for a symbol.

        Args:
            symbol: Symbol to close positions for

        Returns:
            Dict with close result
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        try:
            result = await self._connection.close_positions_by_symbol(symbol=symbol)
            return {
                "success": True,
                "symbol": symbol,
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Close positions by symbol failed: {e}")
            return {"success": False, "error": str(e)}

    async def modify_order(
        self,
        order_id: str,
        open_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        volume: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Modify pending order.

        Args:
            order_id: Order ID to modify
            open_price: New limit/stop price
            stop_loss: New stop loss
            take_profit: New take profit
            volume: New volume (partial fill)

        Returns:
            Dict with modification result
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        try:
            result = await self._connection.modify_order(
                order_id=order_id,
                open_price=open_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                volume=volume
            )
            return {
                "success": True,
                "order_id": order_id,
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Order modification failed: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel pending order.

        Args:
            order_id: Order ID to cancel

        Returns:
            Dict with cancellation result
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        try:
            result = await self._connection.cancel_order(order_id=order_id)
            return {
                "success": True,
                "order_id": order_id,
                "string_code": result.get("stringCode", ""),
            }
        except Exception as e:
            logger.error(f"Order cancellation failed: {e}")
            return {"success": False, "error": str(e)}

    async def subscribe_to_market_data(self, symbol: str) -> bool:
        """
        Subscribe to real-time market data for symbol.

        Args:
            symbol: Symbol to subscribe to

        Returns:
            True if subscription successful
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        try:
            await self._connection.subscribe_to_market_data(symbol=symbol)
            logger.info(f"Subscribed to market data for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Market data subscription failed: {e}")
            return False

    async def unsubscribe_from_market_data(self, symbol: str) -> bool:
        """
        Unsubscribe from market data.

        Args:
            symbol: Symbol to unsubscribe from

        Returns:
            True if unsubscription successful
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        try:
            await self._connection.unsubscribe_from_market_data(symbol=symbol)
            logger.info(f"Unsubscribed from market data for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Market data unsubscription failed: {e}")
            return False

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current quote for symbol from terminal state.

        Args:
            symbol: Symbol to get quote for

        Returns:
            Dict with bid, ask, time, etc. or None if not available
        """
        if not self._connection:
            return None

        try:
            price = self._connection.terminal_state.price(symbol)
            if price:
                return {
                    "symbol": price.get("symbol", symbol),
                    "bid": float(price.get("bid", 0)),
                    "ask": float(price.get("ask", 0)),
                    "time": price.get("time", ""),
                    "broker_time": price.get("brokerTime", ""),
                }
            return None
        except Exception as e:
            logger.error(f"Get quote failed: {e}")
            return None

    def get_symbol_specification(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get symbol specification (contract size, digits, etc.).

        Args:
            symbol: Symbol to get spec for

        Returns:
            Dict with symbol specifications
        """
        if not self._connection:
            return None

        try:
            spec = self._connection.terminal_state.specification(symbol)
            if spec:
                return {
                    "symbol": spec.get("symbol", symbol),
                    "description": spec.get("description", ""),
                    "currency": spec.get("currency", ""),
                    "profit_currency": spec.get("profitCurrency", ""),
                    "margin_currency": spec.get("marginCurrency", ""),
                    "contract_size": float(spec.get("contractSize", 1)),
                    "min_volume": float(spec.get("minVolume", 0.01)),
                    "max_volume": float(spec.get("maxVolume", 100)),
                    "volume_step": float(spec.get("volumeStep", 0.01)),
                    "digits": int(spec.get("digits", 5)),
                    "point": float(spec.get("point", 0.00001)),
                    "trade_mode": spec.get("tradeMode", ""),
                    "stops_level": int(spec.get("stopsLevel", 0)),
                    "spread": float(spec.get("spread", 0)),
                }
            return None
        except Exception as e:
            logger.error(f"Get symbol specification failed: {e}")
            return None

    @property
    def health_status(self) -> Dict[str, Any]:
        """
        Get connection health status.

        Returns:
            Dict with connection health information
        """
        if not self._connection:
            return {
                "connected": False,
                "synchronized": False,
            }

        try:
            health_monitor = self._connection.health_monitor
            return {
                "connected": self._is_connected,
                "synchronized": self._connection.synchronized,
                "server_health": getattr(health_monitor, 'server_health_status', None),
                "uptime": getattr(health_monitor, 'uptime', None),
                "connection_uptime": getattr(health_monitor, 'connection_uptime', None),
            }
        except Exception as e:
            logger.warning(f"Error getting health status: {e}")
            return {
                "connected": self._is_connected,
                "synchronized": False,
                "error": str(e),
            }

    # =========================================================================
    # Real-time Streaming Support
    # =========================================================================

    def add_synchronization_listener(self, listener: Any) -> None:
        """
        Add a synchronization listener for real-time updates.

        The listener should implement MetaAPI SynchronizationListener interface:
        - on_symbol_price_updated(instance_index, price)
        - on_symbol_prices_updated(instance_index, prices, equity, margin, free_margin, margin_level, account_currency_exchange_rate)
        - on_position_updated(instance_index, position)
        - on_position_removed(instance_index, position_id)
        - on_pending_order_updated(instance_index, order)
        - on_pending_order_completed(instance_index, order_id)
        - on_order_completed(instance_index, order_id)
        - on_deal_added(instance_index, deal)
        - on_account_information_updated(instance_index, account_information)

        Args:
            listener: Synchronization listener implementing the interface
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        self._connection.add_synchronization_listener(listener)
        logger.info("Added synchronization listener")

    def remove_synchronization_listener(self, listener: Any) -> None:
        """
        Remove a synchronization listener.

        Args:
            listener: Synchronization listener to remove
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        self._connection.remove_synchronization_listener(listener)
        logger.info("Removed synchronization listener")

    async def subscribe_to_symbols(self, symbols: List[str]) -> Dict[str, bool]:
        """
        Subscribe to real-time market data for multiple symbols.

        Args:
            symbols: List of symbols to subscribe to

        Returns:
            Dict mapping symbol to subscription success status
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        results = {}
        for symbol in symbols:
            try:
                await self._connection.subscribe_to_market_data(symbol=symbol)
                results[symbol] = True
                logger.debug(f"Subscribed to {symbol}")
            except Exception as e:
                logger.error(f"Failed to subscribe to {symbol}: {e}")
                results[symbol] = False

        successful = sum(1 for v in results.values() if v)
        logger.info(f"Subscribed to {successful}/{len(symbols)} symbols")
        return results

    async def unsubscribe_from_symbols(self, symbols: List[str]) -> Dict[str, bool]:
        """
        Unsubscribe from market data for multiple symbols.

        Args:
            symbols: List of symbols to unsubscribe from

        Returns:
            Dict mapping symbol to unsubscription success status
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        results = {}
        for symbol in symbols:
            try:
                await self._connection.unsubscribe_from_market_data(symbol=symbol)
                results[symbol] = True
            except Exception as e:
                logger.error(f"Failed to unsubscribe from {symbol}: {e}")
                results[symbol] = False

        return results

    def get_quotes_bulk(self, symbols: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Get current quotes for multiple symbols from terminal state.

        Args:
            symbols: List of symbols to get quotes for

        Returns:
            Dict mapping symbol to quote data (or None if unavailable)
        """
        if not self._connection:
            return {symbol: None for symbol in symbols}

        results = {}
        for symbol in symbols:
            try:
                price = self._connection.terminal_state.price(symbol)
                if price:
                    results[symbol] = {
                        "symbol": price.get("symbol", symbol),
                        "bid": float(price.get("bid", 0)),
                        "ask": float(price.get("ask", 0)),
                        "time": price.get("time", ""),
                        "broker_time": price.get("brokerTime", ""),
                    }
                else:
                    results[symbol] = None
            except Exception as e:
                logger.error(f"Get quote for {symbol} failed: {e}")
                results[symbol] = None

        return results

    @property
    def subscribed_symbols(self) -> List[str]:
        """
        Get list of currently subscribed symbols.

        Returns:
            List of symbol names with active subscriptions
        """
        if not self._connection or not self._connection.terminal_state:
            return []

        try:
            # Get symbols with price data in terminal state
            # This indicates an active subscription
            return list(self._connection.terminal_state.prices.keys())
        except Exception as e:
            logger.error(f"Error getting subscribed symbols: {e}")
            return []

    async def wait_for_price(
        self,
        symbol: str,
        timeout_seconds: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for price update on a symbol.

        Subscribes if not already subscribed, then waits for price.

        Args:
            symbol: Symbol to wait for price on
            timeout_seconds: Maximum time to wait

        Returns:
            Price dict when received, or None on timeout
        """
        if not self._connection:
            raise RuntimeError("Not connected")

        import asyncio

        # Subscribe if needed
        await self.subscribe_to_market_data(symbol)

        # Poll for price with timeout
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            quote = self.get_quote(symbol)
            if quote and quote.get("bid") and quote.get("ask"):
                return quote
            await asyncio.sleep(0.1)

        logger.warning(f"Timeout waiting for price on {symbol}")
        return None

    @property
    def streaming_enabled(self) -> bool:
        """
        Check if streaming connection is active and synchronized.

        Returns:
            True if connected and synchronized for streaming
        """
        if not self._connection:
            return False

        return self._is_connected and self._connection.synchronized
