"""
TradeLocker Broker Executor
Handles all TradeLocker trading operations via official SDK only.
WebSocket kept for real-time updates (SDK doesn't expose WebSocket).
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
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

    Supports one authentication mode:
    1. SDK mode (required): Uses official tradelocker package with user credentials

    WebSocket connection is maintained separately for real-time updates
    (SDK doesn't expose WebSocket API).
    """

    def __init__(self):
        config = settings.get_broker_config("tradelocker")
        super().__init__(config)
        self.config = config

        # SDK only)
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
        self.sio = None  # WebSocket client
        self._sdk_wrapper: Optional[TradeLockerSDKWrapper] = None
        self._use_sdk = False

        # Determine availability: SDK credentials required
        self._sdk_available = all([self._sdk_username, self._sdk_password, self._sdk_server])
        self.is_available = self._sdk_available

        if not self.is_available:
            logger.warning("TradeLocker executor disabled: SDK credentials (username/password/server) not configured")
        else:
            logger.info("TradeLocker will use official SDK (user credentials)")
        
    async def initialize(self) -> bool:
        """
        Initialize TradeLocker connection using SDK only.
        WebSocket is initialized separately for real-time updates.
        """
        if not self.is_available:
            logger.info("TradeLocker skipped: SDK credentials not configured")
            return False

        try:
            # Initialize SDK
            if self._sdk_available:
                success = await self._initialize_sdk()
                if success:
                    self._use_sdk = True
                    # Set up WebSocket for real-time updates
                    await self._initialize_websocket()
                    self.is_connected = True
                    logger.info("TradeLocker executor initialized via SDK")
                    return True
                else:
                    logger.error("SDK initialization failed")
                    return False
            else:
                logger.error("SDK credentials not available")
                return False
        except Exception as e:
            logger.error(f"TradeLocker initialization error: {e}", exc_info=True)
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
            ws_url = self.config.get("ws_url") or f"{self._sdk_environment.replace('https://', 'wss://')}/socket.io"
            await self.sio.connect(
                ws_url,
                transports=['websocket'],
                auth={'type': self._sdk_environment.split('//')[1].split('.')[0]}  # Extract environment from URL
            )
            logger.info("TradeLocker WebSocket connected")
        except Exception as e:
            # WebSocket failure is non-fatal - SDK can work without real-time updates
            logger.warning(f"WebSocket connection failed (non-fatal): {e}")
    
    async def disconnect(self):
        """Disconnect from TradeLocker"""
        if self.sio:
            await self.sio.disconnect()
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
        """Get all TradeLocker accounts via SDK"""
        if not self._use_sdk or not self._sdk_wrapper:
            logger.error("SDK not initialized")
            return []
        return await self._get_accounts_sdk()

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

    async def get_positions(self, account_id: Optional[str] = None) -> List[Position]:
        """Get open positions from TradeLocker via SDK"""
        if not self._use_sdk or not self._sdk_wrapper:
            logger.error("SDK not initialized")
            return []
        return await self._get_positions_sdk(account_id)

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

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order with TradeLocker via SDK"""
        if not self._use_sdk or not self._sdk_wrapper:
            logger.error("SDK not initialized")
            return OrderResponse(success=False, error="SDK not initialized")
        return await self._place_order_sdk(order)

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

    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify existing order in TradeLocker"""
        # Use SDK if available
        if self._use_sdk and self._sdk_wrapper:
            return await self._modify_order_sdk(order_id, modifications)
        


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

    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel order in TradeLocker via SDK"""
        if not self._use_sdk or not self._sdk_wrapper:
            logger.error("SDK not initialized")
            return OrderResponse(success=False, error="SDK not initialized")
        return await self._cancel_order_sdk(order_id)


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

    async def close_position(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position in TradeLocker via SDK"""
        if not self._use_sdk or not self._sdk_wrapper:
            logger.error("SDK not initialized")
            return TradeResponse(success=False, error="SDK not initialized")
        return await self._close_position_sdk(position_id, quantity)

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

    async def get_account_info(self, account_id: str) -> Optional[Account]:
        """Get specific account information via SDK"""
        if not self._use_sdk or not self._sdk_wrapper:
            logger.error("SDK not initialized")
            return None
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
            return None
        except Exception as e:
            logger.error(f"SDK get_account_info failed: {e}")
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
        """Get available symbols from TradeLocker via SDK"""
        if not self._use_sdk or not self._sdk_wrapper:
            logger.error("SDK not initialized")
            return []
        try:
            instruments = await self._sdk_wrapper.get_all_instruments()
            if instruments is not None:
                # SDK returns DataFrame, extract symbol names
                if hasattr(instruments, 'to_dict'):
                    records = instruments.to_dict('records')
                    return [inst.get('name', inst.get('symbol', '')) for inst in records]
                return []
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
        """Get pending orders via SDK"""
        if not self._use_sdk or not self._sdk_wrapper:
            logger.error("SDK not initialized")
            return []
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
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote for symbol via SDK"""
        if not self._use_sdk or not self._sdk_wrapper:
            logger.error("SDK not initialized")
            return None
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
        return self._use_sdk and self._sdk_wrapper is not None

