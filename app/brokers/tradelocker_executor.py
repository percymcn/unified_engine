"""
TradeLocker Broker Executor
Handles all TradeLocker trading operations via official SDK or Brand API fallback.
WebSocket kept for real-time updates (SDK doesn't expose WebSocket).
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
import socketio
from app.brokers.base_executor import BaseExecutor
from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper
from app.core.config import settings
from app.models.pydantic_schemas import (
    OrderRequest, OrderResponse, Position, Account,
    TradeRequest, TradeResponse
)

logger = logging.getLogger(__name__)

class TradeLockerExecutor(BaseExecutor):
    """
    TradeLocker trading executor.

    Supports two authentication modes:
    1. SDK mode (preferred): Uses official tradelocker package with user credentials
    2. Brand API mode (fallback): Uses httpx with Brand API key

    WebSocket connection is maintained separately for real-time updates
    (SDK doesn't expose WebSocket API).
    """

    def __init__(self):
        config = settings.get_broker_config("tradelocker")
        super().__init__(config)
        self.config = config

        # Brand API configuration (fallback)
        self.api_url = self.config.get("api_url")
        self.ws_url = self.config.get("ws_url")
        self.api_key = self.config.get("api_key")
        self.environment = self.config.get("environment", "demo")

        # SDK configuration (preferred)
        self._sdk_username = self.config.get("username")
        self._sdk_password = self.config.get("password")
        self._sdk_server = self.config.get("server")
        self._sdk_environment = self.config.get("sdk_environment", "https://demo.tradelocker.com")

        # Runtime state
        self.session = None  # httpx client for Brand API
        self.sio = None  # WebSocket client
        self._sdk_wrapper: Optional[TradeLockerSDKWrapper] = None
        self.access_token = None
        self._use_sdk = False  # Track which mode is active

        # Determine availability: SDK credentials OR Brand API key
        self._sdk_available = all([self._sdk_username, self._sdk_password, self._sdk_server])
        self._brand_api_available = bool(self.api_key)
        self.is_available = self._sdk_available or self._brand_api_available

        if not self.is_available:
            logger.warning("TradeLocker executor disabled: No credentials configured")
        elif self._sdk_available:
            logger.info("TradeLocker will use official SDK (user credentials)")
        else:
            logger.info("TradeLocker will use Brand API fallback")
        
    async def initialize(self) -> bool:
        """
        Initialize TradeLocker connection.

        Tries SDK first if credentials available, falls back to Brand API.
        WebSocket is initialized separately for real-time updates.
        """
        if not self.is_available:
            logger.info("TradeLocker skipped: credentials not configured")
            return False

        try:
            # Try SDK initialization first (preferred)
            if self._sdk_available:
                success = await self._initialize_sdk()
                if success:
                    self._use_sdk = True
                    # Still set up WebSocket for real-time updates
                    await self._initialize_websocket()
                    self.is_connected = True
                    logger.info("TradeLocker executor initialized via SDK")
                    return True
                else:
                    logger.warning("SDK initialization failed, trying Brand API fallback")

            # Fall back to Brand API if SDK fails or not available
            if self._brand_api_available:
                success = await self._initialize_brand_api()
                if success:
                    self._use_sdk = False
                    self.is_connected = True
                    logger.info("TradeLocker executor initialized via Brand API")
                    return True

            logger.error("TradeLocker initialization failed: All methods exhausted")
            return False

        except Exception as e:
            logger.error(f"TradeLocker initialization failed: {e}")
            return False

    async def _initialize_sdk(self) -> bool:
        """Initialize using official SDK."""
        try:
            self._sdk_wrapper = TradeLockerSDKWrapper(
                environment=self._sdk_environment,
                username=self._sdk_username,
                password=self._sdk_password,
                server=self._sdk_server
            )
            return await self._sdk_wrapper.initialize()
        except Exception as e:
            logger.error(f"SDK initialization error: {e}")
            return False

    async def _initialize_brand_api(self) -> bool:
        """Initialize using Brand API (legacy)."""
        try:
            # Initialize HTTP client
            self.session = httpx.AsyncClient(
                base_url=self.api_url,
                headers={"brand-api-key": self.api_key},
                timeout=30.0
            )

            # Initialize WebSocket
            await self._initialize_websocket()
            return True
        except Exception as e:
            logger.error(f"Brand API initialization error: {e}")
            return False

    async def _initialize_websocket(self) -> None:
        """Initialize WebSocket connection for real-time updates."""
        try:
            self.sio = socketio.AsyncClient()

            # Set up WebSocket event handlers
            self.sio.on('connect', self._on_connect)
            self.sio.on('disconnect', self._on_disconnect)
            self.sio.on('stream', self._on_stream)
            self.sio.on('subscriptions', self._on_subscriptions)
            self.sio.on('connection', self._on_connection)

            # Connect to WebSocket
            await self.sio.connect(
                self.ws_url,
                transports=['websocket'],
                auth={'type': self.environment}
            )
            logger.info("TradeLocker WebSocket connected")
        except Exception as e:
            # WebSocket failure is non-fatal - SDK can work without real-time updates
            logger.warning(f"WebSocket connection failed (non-fatal): {e}")
    
    async def disconnect(self):
        """Disconnect from TradeLocker"""
        if self.sio:
            await self.sio.disconnect()
        if self.session:
            await self.session.aclose()
        if self._sdk_wrapper:
            self._sdk_wrapper.shutdown()
            self._sdk_wrapper = None
        self.is_connected = False
        self._use_sdk = False
        logger.info("TradeLocker executor disconnected")
    
    async def _on_connect(self):
        """WebSocket connect handler"""
        logger.info("TradeLocker WebSocket connected")
    
    async def _on_disconnect(self):
        """WebSocket disconnect handler"""
        logger.warning("TradeLocker WebSocket disconnected")
    
    async def _on_stream(self, data):
        """Handle stream events"""
        try:
            event_type = data.get('type')
            if event_type == 'AccountStatus':
                await self._handle_account_update(data)
            elif event_type == 'Position':
                await self._handle_position_update(data)
            elif event_type == 'ClosePosition':
                await self._handle_position_close(data)
            elif event_type == 'OpenOrder':
                await self._handle_order_update(data)
        except Exception as e:
            logger.error(f"Error handling stream event: {e}")
    
    async def _on_subscriptions(self, data):
        """Handle subscription events"""
        logger.debug(f"TradeLocker subscription: {data}")
    
    async def _on_connection(self, data):
        """Handle connection events"""
        logger.info(f"TradeLocker connection event: {data}")
    
    async def _handle_account_update(self, data):
        """Handle account status updates"""
        # Emit WebSocket update to UI
        await self.emit_account_update(data)
    
    async def _handle_position_update(self, data):
        """Handle position updates"""
        # Emit WebSocket update to UI
        await self.emit_position_update(data)
    
    async def _handle_position_close(self, data):
        """Handle position closure"""
        # Emit WebSocket update to UI
        await self.emit_position_close(data)
    
    async def _handle_order_update(self, data):
        """Handle order updates"""
        # Emit WebSocket update to UI
        await self.emit_order_update(data)
    
    async def get_accounts(self) -> List[Account]:
        """Get all TradeLocker accounts"""
        # Use SDK if available
        if self._use_sdk and self._sdk_wrapper:
            return await self._get_accounts_sdk()
        
        # Fall back to Brand API
        return await self._get_accounts_brand_api()

    async def _get_accounts_sdk(self) -> List[Account]:
        """Get accounts via SDK."""
        try:
            account_state = await self._sdk_wrapper.get_account_state()
            if account_state:
                account_number = self._sdk_wrapper.account_number
                account_id = self._sdk_wrapper.account_id
                
                return [Account(
                    id=str(account_number or account_id or ""),
                    broker="tradelocker",
                    account_type="live",
                    currency=account_state.get("currency", "USD"),
                    balance=float(account_state.get("balance", 0)),
                    equity=float(account_state.get("equity", 0)),
                    margin=float(account_state.get("margin", 0)),
                    free_margin=float(account_state.get("freeMargin", account_state.get("free_margin", 0))),
                    margin_level=float(account_state.get("marginLevel", account_state.get("margin_level", 0))),
                    leverage=account_state.get("leverage", 100),
                    is_active=True,
                    is_live=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )]
            return []
        except Exception as e:
            logger.error(f"SDK get_accounts failed: {e}")
            return []

    async def _get_accounts_brand_api(self) -> List[Account]:
        """Get accounts via Brand API."""
        try:
            response = await self.session.get("/accounts")
            if response.status_code == 200:
                accounts_data = response.json()
                accounts = []
                
                for account_data in accounts_data:
                    account = Account(
                        id=str(account_data["id"]),
                        broker="tradelocker",
                        account_type=account_data.get("type", "live"),
                        currency=account_data.get("currency", "USD"),
                        balance=float(account_data.get("balance", 0)),
                        equity=float(account_data.get("equity", 0)),
                        margin=float(account_data.get("margin", 0)),
                        free_margin=float(account_data.get("free_margin", 0)),
                        margin_level=float(account_data.get("margin_level", 0)),
                        leverage=account_data.get("leverage", 100),
                        is_active=account_data.get("is_active", True),
                        is_live=account_data.get("type") == "live",
                        created_at=datetime.fromisoformat(account_data.get("created_at", "2023-01-01")),
                        updated_at=datetime.now()
                    )
                    accounts.append(account)
                
                return accounts
            else:
                logger.error(f"Failed to get TradeLocker accounts: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting TradeLocker accounts: {e}")
            return []
    
    async def get_positions(self, account_id: Optional[str] = None) -> List[Position]:
        """Get open positions from TradeLocker"""
        # Use SDK if available
        if self._use_sdk and self._sdk_wrapper:
            return await self._get_positions_sdk(account_id)
        
        # Fall back to Brand API
        return await self._get_positions_brand_api(account_id)

    async def _get_positions_sdk(self, account_id: Optional[str] = None) -> List[Position]:
        """Get positions via SDK."""
        try:
            positions_data = await self._sdk_wrapper.get_positions()
            positions = []
            account_number = str(self._sdk_wrapper.account_number or account_id or "")
            
            for pos_data in positions_data:
                # Convert dict or DataFrame row to dict
                if hasattr(pos_data, 'to_dict'):
                    pos_dict = pos_data.to_dict()
                elif isinstance(pos_data, dict):
                    pos_dict = pos_data
                else:
                    continue
                
                # Filter by account if specified
                if account_id and str(pos_dict.get("accountId", pos_dict.get("account_id", ""))) != account_id:
                    continue
                
                position = Position(
                    id=str(pos_dict.get("id", pos_dict.get("positionId", ""))),
                    broker="tradelocker",
                    account_id=account_number,
                    symbol=pos_dict.get("symbol", pos_dict.get("name", "")),
                    side=pos_dict.get("side", "buy").lower(),
                    size=float(pos_dict.get("quantity", pos_dict.get("size", 0))),
                    entry_price=float(pos_dict.get("entryPrice", pos_dict.get("entry_price", 0))),
                    current_price=float(pos_dict.get("currentPrice", pos_dict.get("current_price", pos_dict.get("entryPrice", 0)))),
                    unrealized_pnl=float(pos_dict.get("unrealizedPnl", pos_dict.get("unrealized_pnl", 0))),
                    realized_pnl=float(pos_dict.get("realizedPnl", pos_dict.get("realized_pnl", 0))),
                    margin=float(pos_dict.get("margin", 0)),
                    magic_number=pos_dict.get("magic", pos_dict.get("magic_number", 0)),
                    comment=pos_dict.get("comment", ""),
                    open_time=datetime.now(),  # SDK may not provide parsed datetime
                    close_time=None,
                    is_active=True
                )
                positions.append(position)
            
            return positions
        except Exception as e:
            logger.error(f"SDK get_positions failed: {e}")
            return []

    async def _get_positions_brand_api(self, account_id: Optional[str] = None) -> List[Position]:
        """Get positions via Brand API."""
        try:
            params = {}
            if account_id:
                params["account_id"] = account_id
                
            response = await self.session.get("/positions", params=params)
            if response.status_code == 200:
                positions_data = response.json()
                positions = []
                
                for pos_data in positions_data:
                    if pos_data.get("is_active", True):
                        position = Position(
                            id=str(pos_data["id"]),
                            broker="tradelocker",
                            account_id=str(pos_data["account_id"]),
                            symbol=pos_data["symbol"],
                            side=pos_data["side"].lower(),
                            size=float(pos_data["size"]),
                            entry_price=float(pos_data["entry_price"]),
                            current_price=float(pos_data.get("current_price", pos_data["entry_price"])),
                            unrealized_pnl=float(pos_data.get("unrealized_pnl", 0)),
                            realized_pnl=float(pos_data.get("realized_pnl", 0)),
                            margin=float(pos_data.get("margin", 0)),
                            magic_number=pos_data.get("magic_number", 0),
                            comment=pos_data.get("comment", ""),
                            open_time=datetime.fromisoformat(pos_data.get("open_time", "2023-01-01")),
                            close_time=datetime.fromisoformat(pos_data["close_time"]) if pos_data.get("close_time") else None,
                            is_active=pos_data.get("is_active", True)
                        )
                        positions.append(position)
                
                return positions
            else:
                logger.error(f"Failed to get TradeLocker positions: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting TradeLocker positions: {e}")
            return []
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order with TradeLocker"""
        try:
            # Use SDK if available
            if self._use_sdk and self._sdk_wrapper:
                return await self._place_order_sdk(order)

            # Fall back to Brand API
            return await self._place_order_brand_api(order)

        except Exception as e:
            logger.error(f"Error placing TradeLocker order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )

    async def _place_order_sdk(self, order: OrderRequest) -> OrderResponse:
        """Place order using official SDK."""
        try:
            # Lookup instrument ID from symbol
            instrument_id = await self._sdk_wrapper.get_instrument_id_by_symbol(order.symbol)
            if instrument_id is None:
                return OrderResponse(
                    success=False,
                    error=f"Instrument not found: {order.symbol}"
                )

            # Map order type to SDK format
            order_type = order.order_type.lower()
            if "market" in order_type:
                sdk_type = "market"
            elif "limit" in order_type:
                sdk_type = "limit"
            elif "stop" in order_type:
                sdk_type = "stop"
            else:
                sdk_type = "market"

            # Determine side
            side = "buy" if "buy" in order_type else "sell"

            result = await self._sdk_wrapper.create_order(
                instrument_id=instrument_id,
                quantity=order.quantity,
                side=side,
                order_type=sdk_type,
                price=order.price,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit
            )

            if result and result.get("success"):
                order_result = result.get("result", {})
                return OrderResponse(
                    success=True,
                    order_id=str(order_result.get("orderId", order_result.get("id", ""))),
                    broker="tradelocker",
                    status="filled" if sdk_type == "market" else "pending",
                    filled_quantity=order.quantity if sdk_type == "market" else 0,
                    filled_price=order.price,
                    commission=0,
                    timestamp=datetime.now()
                )
            else:
                return OrderResponse(
                    success=False,
                    error=result.get("error", "SDK order failed") if result else "SDK order failed"
                )

        except Exception as e:
            logger.error(f"SDK order error: {e}")
            return OrderResponse(success=False, error=str(e))

    async def _place_order_brand_api(self, order: OrderRequest) -> OrderResponse:
        """Place order using Brand API (legacy)."""
        # Map order types
        order_type_map = {
            "market_buy": "MARKET_BUY",
            "market_sell": "MARKET_SELL",
            "buy_limit": "BUY_LIMIT",
            "sell_limit": "SELL_LIMIT",
            "buy_stop": "BUY_STOP",
            "sell_stop": "SELL_STOP"
        }

        api_order_type = order_type_map.get(order.order_type)
        if not api_order_type:
            return OrderResponse(
                success=False,
                error=f"Unsupported order type: {order.order_type}"
            )

        order_data = {
            "account_id": order.account_id,
            "symbol": order.symbol,
            "type": api_order_type,
            "quantity": order.quantity,
            "price": order.price,
            "stop_loss": order.stop_loss,
            "take_profit": order.take_profit,
            "comment": order.comment,
            "magic_number": order.magic_number
        }

        response = await self.session.post("/trades/market", json=order_data)

        if response.status_code == 200:
            result = response.json()

            return OrderResponse(
                success=True,
                order_id=str(result.get("id")),
                broker="tradelocker",
                status=result.get("status", "filled"),
                filled_quantity=result.get("filled_quantity", order.quantity),
                filled_price=result.get("filled_price", order.price),
                commission=result.get("commission", 0),
                timestamp=datetime.now()
            )
        else:
            error_msg = response.text
            logger.error(f"TradeLocker order failed: {error_msg}")
            return OrderResponse(
                success=False,
                error=error_msg
            )
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify existing order in TradeLocker"""
        # Use SDK if available
        if self._use_sdk and self._sdk_wrapper:
            return await self._modify_order_sdk(order_id, modifications)
        
        # Fall back to Brand API
        return await self._modify_order_brand_api(order_id, modifications)

    async def _modify_order_sdk(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify order via SDK."""
        try:
            result = await self._sdk_wrapper.modify_order(
                order_id=int(order_id),
                price=modifications.get("price"),
                stop_loss=modifications.get("stop_loss"),
                take_profit=modifications.get("take_profit")
            )
            
            if result and result.get("success"):
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="tradelocker",
                    status="modified",
                    timestamp=datetime.now()
                )
            else:
                return OrderResponse(
                    success=False,
                    error=result.get("error", "SDK order modification failed") if result else "SDK order modification failed"
                )
        except Exception as e:
            logger.error(f"SDK modify_order failed: {e}")
            return OrderResponse(success=False, error=str(e))

    async def _modify_order_brand_api(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify order via Brand API."""
        try:
            modify_data = {
                "price": modifications.get("price"),
                "stop_loss": modifications.get("stop_loss"),
                "take_profit": modifications.get("take_profit")
            }
            
            response = await self.session.put(f"/orders/{order_id}", json=modify_data)
            
            if response.status_code == 200:
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="tradelocker",
                    status="modified",
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"TradeLocker order modification failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error modifying TradeLocker order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel order in TradeLocker"""
        # Use SDK if available
        if self._use_sdk and self._sdk_wrapper:
            return await self._cancel_order_sdk(order_id)
        
        # Fall back to Brand API
        return await self._cancel_order_brand_api(order_id)

    async def _cancel_order_sdk(self, order_id: str) -> OrderResponse:
        """Cancel order via SDK."""
        try:
            result = await self._sdk_wrapper.cancel_order(int(order_id))
            
            if result and result.get("success"):
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="tradelocker",
                    status="cancelled",
                    timestamp=datetime.now()
                )
            else:
                return OrderResponse(
                    success=False,
                    error=result.get("error", "SDK order cancellation failed") if result else "SDK order cancellation failed"
                )
        except Exception as e:
            logger.error(f"SDK cancel_order failed: {e}")
            return OrderResponse(success=False, error=str(e))

    async def _cancel_order_brand_api(self, order_id: str) -> OrderResponse:
        """Cancel order via Brand API."""
        try:
            response = await self.session.delete(f"/orders/{order_id}")
            
            if response.status_code == 200:
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="tradelocker",
                    status="cancelled",
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"TradeLocker order cancellation failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error cancelling TradeLocker order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def close_position(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position in TradeLocker"""
        try:
            # Use SDK if available
            if self._use_sdk and self._sdk_wrapper:
                return await self._close_position_sdk(position_id, quantity)

            # Fall back to Brand API
            return await self._close_position_brand_api(position_id, quantity)

        except Exception as e:
            logger.error(f"Error closing TradeLocker position: {e}")
            return TradeResponse(
                success=False,
                error=str(e)
            )

    async def _close_position_sdk(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position using official SDK."""
        try:
            result = await self._sdk_wrapper.close_position(
                position_id=int(position_id),
                quantity=quantity
            )

            if result and result.get("success"):
                close_result = result.get("result", {})
                return TradeResponse(
                    success=True,
                    trade_id=str(close_result.get("id", position_id)),
                    broker="tradelocker",
                    symbol=close_result.get("symbol", ""),
                    side=close_result.get("side", ""),
                    quantity=close_result.get("quantity", quantity or 0),
                    price=close_result.get("price", 0),
                    pnl=close_result.get("pnl", 0),
                    commission=close_result.get("commission", 0),
                    timestamp=datetime.now()
                )
            else:
                return TradeResponse(
                    success=False,
                    error=result.get("error", "SDK close failed") if result else "SDK close failed"
                )

        except Exception as e:
            logger.error(f"SDK close position error: {e}")
            return TradeResponse(success=False, error=str(e))

    async def _close_position_brand_api(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position using Brand API (legacy)."""
        close_data = {
            "quantity": quantity
        }

        response = await self.session.delete(f"/positions/{position_id}", json=close_data)

        if response.status_code == 200:
            result = response.json()

            return TradeResponse(
                success=True,
                trade_id=str(result.get("id")),
                broker="tradelocker",
                symbol=result.get("symbol", ""),
                side=result.get("side", ""),
                quantity=result.get("quantity", 0),
                price=result.get("price", 0),
                pnl=result.get("pnl", 0),
                commission=result.get("commission", 0),
                timestamp=datetime.now()
            )
        else:
            error_msg = response.text
            logger.error(f"TradeLocker position close failed: {error_msg}")
            return TradeResponse(
                success=False,
                error=error_msg
            )
    
    async def get_account_info(self, account_id: str) -> Optional[Account]:
        """Get specific account information"""
        # Use SDK if available
        if self._use_sdk and self._sdk_wrapper:
            try:
                account_state = await self._sdk_wrapper.get_account_state()
                if account_state:
                    account_number = self._sdk_wrapper.account_number
                    account_id_val = self._sdk_wrapper.account_id
                    
                    return Account(
                        id=str(account_number or account_id_val or account_id),
                        broker="tradelocker",
                        account_type="live",
                        currency=account_state.get("currency", "USD"),
                        balance=float(account_state.get("balance", 0)),
                        equity=float(account_state.get("equity", 0)),
                        margin=float(account_state.get("margin", 0)),
                        free_margin=float(account_state.get("freeMargin", account_state.get("free_margin", 0))),
                        margin_level=float(account_state.get("marginLevel", account_state.get("margin_level", 0))),
                        leverage=account_state.get("leverage", 100),
                        is_active=True,
                        is_live=True,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
            except Exception as e:
                logger.error(f"SDK get_account_info failed: {e}")
        
        # Fall back to Brand API
        try:
            response = await self.session.get(f"/accounts/{account_id}")
            if response.status_code == 200:
                account_data = response.json()
                
                account = Account(
                    id=str(account_data["id"]),
                    broker="tradelocker",
                    account_type=account_data.get("type", "live"),
                    currency=account_data.get("currency", "USD"),
                    balance=float(account_data.get("balance", 0)),
                    equity=float(account_data.get("equity", 0)),
                    margin=float(account_data.get("margin", 0)),
                    free_margin=float(account_data.get("free_margin", 0)),
                    margin_level=float(account_data.get("margin_level", 0)),
                    leverage=account_data.get("leverage", 100),
                    is_active=account_data.get("is_active", True),
                    is_live=account_data.get("type") == "live",
                    created_at=datetime.fromisoformat(account_data.get("created_at", "2023-01-01")),
                    updated_at=datetime.now()
                )
                
                return account
            else:
                logger.error(f"Failed to get TradeLocker account {account_id}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting TradeLocker account {account_id}: {e}")
            return None
    
    async def get_price_history(
        self,
        symbol: str,
        resolution: str = "1D",
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        lookback_period: str = "5D"
    ) -> Optional[Any]:
        """
        Get price history for a symbol.
        
        Args:
            symbol: Symbol name (e.g., "EURUSD", "BTCUSD")
            resolution: Time resolution (1m, 5m, 15m, 1H, 4H, 1D, etc.)
            start_timestamp: Start timestamp in milliseconds
            end_timestamp: End timestamp in milliseconds
            lookback_period: Alternative to timestamps (5D, 1M, etc.)
        
        Returns:
            DataFrame with OHLCV data or None on error
        """
        if self._use_sdk and self._sdk_wrapper:
            try:
                instrument_id = await self._sdk_wrapper.get_instrument_id_by_symbol(symbol)
                if instrument_id:
                    return await self._sdk_wrapper.get_price_history(
                        instrument_id=instrument_id,
                        resolution=resolution,
                        start_timestamp=start_timestamp,
                        end_timestamp=end_timestamp,
                        lookback_period=lookback_period
                    )
            except Exception as e:
                logger.error(f"SDK get_price_history failed: {e}")
        
        return None

    async def get_symbols(self) -> List[str]:
        """Get available symbols from TradeLocker"""
        try:
            # Use SDK if available
            if self._use_sdk and self._sdk_wrapper:
                instruments = await self._sdk_wrapper.get_all_instruments()
                if instruments is not None:
                    # SDK returns DataFrame, extract symbol names
                    if hasattr(instruments, 'to_dict'):
                        records = instruments.to_dict('records')
                        return [inst.get('name', inst.get('symbol', '')) for inst in records]
                    return []
                return []

            # Fall back to Brand API
            response = await self.session.get("/instruments")
            if response.status_code == 200:
                instruments_data = response.json()
                return [instrument["symbol"] for instrument in instruments_data]
            else:
                logger.error(f"Failed to get TradeLocker symbols: {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error getting TradeLocker symbols: {e}")
            return []
    async def authenticate(self) -> bool:
        """Authenticate with broker API"""
        return await self.initialize()
    
    async def connect(self) -> bool:
        """Connect to broker API"""
        return await self.initialize()
    
    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get pending orders"""
        # Use SDK if available
        if self._use_sdk and self._sdk_wrapper:
            try:
                orders_data = await self._sdk_wrapper.get_orders()
                orders = []
                
                for order_data in orders_data:
                    # Convert dict or DataFrame row to dict
                    if hasattr(order_data, 'to_dict'):
                        order_dict = order_data.to_dict()
                    elif isinstance(order_data, dict):
                        order_dict = order_data
                    else:
                        continue
                    
                    orders.append({
                        "id": str(order_dict.get("id", order_dict.get("orderId", ""))),
                        "symbol": order_dict.get("symbol", order_dict.get("name", "")),
                        "side": order_dict.get("side", ""),
                        "quantity": float(order_dict.get("quantity", order_dict.get("size", 0))),
                        "price": float(order_dict.get("price", 0)),
                        "order_type": order_dict.get("type", order_dict.get("orderType", "")),
                        "status": order_dict.get("status", "pending"),
                        "stop_loss": float(order_dict.get("stopLoss", order_dict.get("stop_loss", 0))) if order_dict.get("stopLoss") else None,
                        "take_profit": float(order_dict.get("takeProfit", order_dict.get("take_profit", 0))) if order_dict.get("takeProfit") else None,
                    })
                
                return orders
            except Exception as e:
                logger.error(f"SDK get_orders failed: {e}")
                return []
        
        # Brand API fallback - not implemented
        return []
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote for symbol"""
        # Use SDK if available
        if self._use_sdk and self._sdk_wrapper:
            try:
                instrument_id = await self._sdk_wrapper.get_instrument_id_by_symbol(symbol)
                if instrument_id:
                    ask_price = await self._sdk_wrapper.get_latest_asking_price(instrument_id)
                    if ask_price:
                        # SDK may not provide bid, estimate from ask
                        return {
                            "symbol": symbol,
                            "ask": ask_price,
                            "bid": ask_price - 0.0001,  # Approximate spread
                            "time": datetime.now().isoformat()
                        }
            except Exception as e:
                logger.error(f"SDK get_quote failed: {e}")
        
        return None
    
    async def modify_position(
        self,
        position_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """Modify position"""
        return {"error": "Not implemented"}

    def is_connected(self) -> bool:
        """Check if broker is connected"""
        return hasattr(self, 'session') and self.session is not None and not self.session.is_closed

