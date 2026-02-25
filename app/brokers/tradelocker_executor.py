"""
TradeLocker Broker Executor
Handles all TradeLocker trading operations via official SDK only.
WebSocket kept for real-time updates (SDK doesn't expose WebSocket).
"""
import asyncio
import json
import logging
import math
from typing import Dict, List, Optional, Any
from datetime import datetime
import socketio
from app.brokers.base_executor import BaseExecutor
from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper
from app.core.config import settings
from app.models.pydantic_schemas import (
    OrderRequest, ExecutorOrderResponse as OrderResponse, ExecutorPosition as Position, Account,
    TradeRequest, ExecutorTradeResponse as TradeResponse
)
from app.services.broker_resilience import with_circuit_breaker, execute_with_timeout_and_breaker
from app.core.circuit_breaker import CircuitBreakerOpenException

logger = logging.getLogger(__name__)

class TradeLockerExecutor(BaseExecutor):
    """
    TradeLocker trading executor.

    Supports one authentication mode:
    1. SDK mode (required): Uses official tradelocker package with user credentials

    WebSocket connection is maintained separately for real-time updates
    (SDK doesn't expose WebSocket API).
    """

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        sdk_environment: Optional[str] = None,
        account_id: Optional[str] = None,
        account_num: Optional[str] = None,
        user_id: Optional[int] = None,
    ):
        config = settings.get_broker_config("tradelocker")
        super().__init__(config)
        self.config = config

        # SDK configuration (required)
        self._sdk_username = username or self.config.get("username")
        self._sdk_password = password or self.config.get("password")
        self._sdk_server = server or self.config.get("server")
        self._sdk_environment = sdk_environment or self.config.get("sdk_environment", "https://demo.tradelocker.com")
        # Pre-resolved account info (from stored credentials, avoids rediscovery)
        self._sdk_account_id = account_id or self.config.get("account_id")
        self._sdk_account_num = account_num or self.config.get("account_num") or self.config.get("account_number")
        if user_id is not None:
            self.user_id = user_id

        # Runtime state
        self.sio = None  # WebSocket client
        self._sdk_wrapper: Optional[TradeLockerSDKWrapper] = None
        self._use_sdk = False

        # Determine availability: SDK credentials required
        self._sdk_available = all([self._sdk_username, self._sdk_password, self._sdk_server])
        self.is_available = self._sdk_available

        if not self.is_available:
            logger.info("TradeLocker executor disabled: SDK credentials (username/password/server) not configured")
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
            # Parse account_id/account_num as integers if provided
            account_id = None
            account_num = None
            if self._sdk_account_id:
                try:
                    account_id = int(self._sdk_account_id)
                except (ValueError, TypeError):
                    pass
            if self._sdk_account_num:
                try:
                    account_num = int(self._sdk_account_num)
                except (ValueError, TypeError):
                    pass

            self._sdk_wrapper = TradeLockerSDKWrapper(
                environment=self._sdk_environment,
                username=self._sdk_username,
                password=self._sdk_password,
                server=self._sdk_server,
                account_id=account_id,
                account_num=account_num,
            )
            return await self._sdk_wrapper.initialize()
        except Exception as e:
            logger.error(f"SDK initialization error: {e}")
            return False

    def _sanitize_string_field(self, value: Any) -> str:
        """Sanitize field values that may be nan, None, or other non-string types."""
        if value is None:
            return ""
        if isinstance(value, float) and math.isnan(value):
            return ""
        return str(value)

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

            # Try connecting with auth parameter (socketio 5.x), fallback to headers for older versions
            try:
                await self.sio.connect(
                    ws_url,
                    transports=['websocket'],
                    auth={'type': self._sdk_environment.split('//')[1].split('.')[0]}
                )
            except TypeError as auth_err:
                if 'auth' in str(auth_err):
                    # Fallback: older socketio version doesn't support auth param
                    logger.debug("Falling back to socketio without auth parameter")
                    await self.sio.connect(
                        ws_url,
                        transports=['websocket'],
                        headers={'X-Environment': self._sdk_environment.split('//')[1].split('.')[0]}
                    )
                else:
                    raise

            logger.info("TradeLocker WebSocket connected")
        except Exception as e:
            # WebSocket failure is non-fatal - SDK can work without real-time updates
            logger.debug(f"WebSocket connection skipped (SDK works without it): {e}")
    
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
        """Get ALL accounts via SDK with status (active, blown, expired)."""
        try:
            # Get all broker accounts with status
            broker_accounts = await self._sdk_wrapper.get_all_broker_accounts()
            if not broker_accounts:
                # Fallback to single account if get_all fails
                account_state = await self._sdk_wrapper.get_account_state()
                if account_state:
                    account_number = self._sdk_wrapper.account_number
                    account_id = self._sdk_wrapper.account_id
                    return [Account(
                        id=str(account_number or account_id or ""),
                        broker="tradelocker",
                        account_type="demo",
                        currency=account_state.get("currency", "USD"),
                        balance=float(account_state.get("balance", 0)),
                        equity=float(account_state.get("projectedBalance", account_state.get("equity", 0))),
                        margin=float(account_state.get("initialMarginReq", account_state.get("margin", 0))),
                        free_margin=float(account_state.get("availableFunds", account_state.get("freeMargin", 0))),
                        margin_level=float(account_state.get("marginWarningLevel", account_state.get("marginLevel", 0))),
                        leverage=account_state.get("leverage", 100),
                        is_active=True,
                        is_live=False,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )]
                return []

            # Convert broker accounts to Account objects
            accounts = []
            for acc in broker_accounts:
                status = acc.get('status', 'active')
                is_active = status in ('active', 'blown')  # blown accounts still exist

                accounts.append(Account(
                    id=str(acc.get('broker_account_id', '')),
                    broker="tradelocker",
                    account_type=acc.get('account_type', 'DEMO').lower(),
                    currency=acc.get('currency', 'USD'),
                    balance=float(acc.get('balance', 0)),
                    equity=float(acc.get('equity', 0)),
                    margin=0.0,
                    free_margin=float(acc.get('balance', 0)),
                    margin_level=0.0,
                    leverage=100,
                    is_active=is_active,
                    is_live=acc.get('account_type', 'DEMO').upper() == 'LIVE',
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    # Store extra info for UI
                    extra_data={
                        'display_name': acc.get('display_name', ''),
                        'account_number': acc.get('account_number', ''),
                        'status': status,  # active, inactive, blown, expired
                    }
                ))
            return accounts
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

            # Convert DataFrame to list of dicts if needed (SDK returns DataFrame)
            if positions_data is not None and hasattr(positions_data, 'to_dict'):
                positions_list = positions_data.to_dict('records')
            elif isinstance(positions_data, list):
                positions_list = positions_data
            else:
                positions_list = []

            logger.debug(f"Positions data: {len(positions_list)} positions")

            # Build instrument ID to symbol mapping if possible
            instrument_map = {}
            try:
                instruments = await self._sdk_wrapper.get_all_instruments()
                if instruments is not None:
                    # Handle DataFrame or list
                    if hasattr(instruments, 'to_dict'):
                        # It's a DataFrame - convert to list of dicts
                        inst_list = instruments.to_dict('records')
                    elif isinstance(instruments, list):
                        inst_list = instruments
                    else:
                        inst_list = []

                    for inst in inst_list:
                        if isinstance(inst, dict):
                            inst_id = inst.get("tradableInstrumentId") or inst.get("id")
                            inst_symbol = inst.get("name") or inst.get("symbol", "")
                            if inst_id and inst_symbol:
                                instrument_map[int(inst_id)] = inst_symbol

                    logger.debug(f"Built instrument map with {len(instrument_map)} symbols")
            except Exception as inst_err:
                logger.debug(f"Could not build instrument map: {inst_err}")

            for pos_data in positions_list:
                # Convert dict or DataFrame row to dict
                if hasattr(pos_data, 'to_dict'):
                    pos_dict = pos_data.to_dict()
                elif isinstance(pos_data, dict):
                    pos_dict = pos_data
                else:
                    continue

                # Filter by account if specified AND position has account field
                # Note: TradeLocker SDK returns positions pre-filtered by account, so no accountId field
                pos_account = pos_dict.get("accountId", pos_dict.get("account_id"))
                if pos_account and account_id and str(pos_account) != account_id:
                    continue

                # TradeLocker field mapping:
                # - qty: position quantity
                # - avgPrice: average entry price
                # - unrealizedPl: unrealized P/L
                # - tradableInstrumentId: instrument ID (need to look up symbol)
                # - side: buy/sell
                instrument_id = pos_dict.get("tradableInstrumentId")
                symbol = instrument_map.get(int(instrument_id), "") if instrument_id else ""
                if not symbol:
                    symbol = pos_dict.get("symbol", pos_dict.get("name", f"INST_{instrument_id}"))

                # Handle side - TradeLocker uses "buy"/"sell"
                side_raw = pos_dict.get("side", "buy")
                side = str(side_raw).lower() if side_raw else "buy"

                position = Position(
                    id=str(pos_dict.get("id", pos_dict.get("positionId", ""))),
                    broker="tradelocker",
                    account_id=account_number,
                    symbol=symbol,
                    side=side,
                    size=float(pos_dict.get("qty", pos_dict.get("quantity", pos_dict.get("size", 0))) or 0),
                    entry_price=float(pos_dict.get("avgPrice", pos_dict.get("entryPrice", pos_dict.get("entry_price", 0))) or 0),
                    current_price=float(pos_dict.get("currentPrice", pos_dict.get("current_price", 0)) or 0) or None,
                    unrealized_pnl=float(pos_dict.get("unrealizedPl", pos_dict.get("unrealizedPnl", 0)) or 0),
                    realized_pnl=float(pos_dict.get("realizedPl", pos_dict.get("realizedPnl", 0)) or 0),
                    margin=float(pos_dict.get("margin", 0) or 0),
                    stop_loss=float(pos_dict.get("stopLoss", 0) or 0) or None,
                    take_profit=float(pos_dict.get("takeProfit", 0) or 0) or None,
                    magic_number=pos_dict.get("magic", pos_dict.get("magic_number", 0)),
                    # Sanitize comment - TradeLocker may return nan (float) which fails Pydantic validation
                    comment=self._sanitize_string_field(pos_dict.get("comment", pos_dict.get("strategyId", ""))),
                    open_time=datetime.now(),  # SDK may not provide parsed datetime
                    close_time=None,
                    is_active=True
                )
                positions.append(position)

            return positions
        except Exception as e:
            logger.error(f"SDK get_positions failed: {e}")
            return []

    @with_circuit_breaker("tradelocker")
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order with TradeLocker via SDK (with circuit breaker protection)"""
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

            # TradeLocker requires IOC validity for market orders
            validity = "IOC" if sdk_type == "market" else "GTC"

            # Handle trailing stop - TradeLocker uses stop_loss_type='trailingOffset'
            # with the trailing distance in price units
            trailing_stop = getattr(order, 'trailing_stop', None)
            stop_loss_type = "absolute"
            effective_stop_loss = order.stop_loss

            if trailing_stop:
                # Use trailing stop instead of fixed stop loss
                stop_loss_type = "trailingOffset"
                effective_stop_loss = float(trailing_stop)  # Distance in price units
                logger.info(f"TradeLocker: Using trailing stop with distance {trailing_stop}")

            result = await self._sdk_wrapper.create_order(
                instrument_id=instrument_id,
                quantity=order.quantity,
                side=side,
                order_type=sdk_type,
                price=order.price,
                stop_loss=effective_stop_loss,
                take_profit=order.take_profit,
                stop_loss_type=stop_loss_type,
                validity=validity
            )

            if result and result.get("success"):
                order_result = result.get("result", {})
                # SDK may return order ID as int directly, or as dict with orderId/id
                if isinstance(order_result, int):
                    order_id = str(order_result)
                elif isinstance(order_result, dict):
                    order_id = str(order_result.get("orderId", order_result.get("id", "")))
                else:
                    order_id = str(order_result) if order_result else ""
                return OrderResponse(
                    success=True,
                    order_id=order_id,
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
        """Close position using SDK's _place_close_position_order (works in hedging mode)."""
        try:
            # Get position details for response
            positions = await self.get_positions()
            position = next((p for p in positions if p.id == position_id), None)

            if not position:
                return TradeResponse(success=False, error=f"Position {position_id} not found")

            close_qty = quantity or position.size

            # Use SDK wrapper's close_position which uses _place_close_position_order internally
            result = await self._sdk_wrapper.close_position(
                position_id=int(position_id),
                quantity=close_qty if quantity else None  # None = full close
            )

            if result and result.get("success"):
                return TradeResponse(
                    success=True,
                    trade_id=position_id,
                    broker="tradelocker",
                    symbol=position.symbol,
                    side="close",
                    quantity=close_qty,
                    price=0,  # Actual price determined at execution
                    pnl=0,    # PnL will be calculated by broker
                    commission=0,
                    timestamp=datetime.now()
                )
            else:
                return TradeResponse(
                    success=False,
                    error=result.get("error", "SDK close position failed") if result else "SDK close position failed"
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
            logger.info(f"TradeLocker get_account_info raw state: {account_state}")
            if account_state:
                account_number = self._sdk_wrapper.account_number
                account_id_val = self._sdk_wrapper.account_id
                
                return Account(
                    id=str(account_number or account_id_val or account_id),
                    broker="tradelocker",
                    account_type="live",
                    currency=account_state.get("currency", "USD"),
                    balance=float(account_state.get("balance", 0)),
                    equity=float(account_state.get("projectedBalance", account_state.get("equity", 0))),
                    margin=float(account_state.get("initialMarginReq", account_state.get("margin", 0))),
                    free_margin=float(account_state.get("availableFunds", account_state.get("freeMargin", 0))),
                    margin_level=float(account_state.get("marginWarningLevel", account_state.get("marginLevel", 0))),
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
