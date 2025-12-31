"""
TradeLocker Broker Executor
Handles all TradeLocker trading operations via Brand API and WebSocket
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
import socketio
from app.brokers.base_executor import BaseExecutor
from app.core.config import settings
from app.models.pydantic_schemas import (
    OrderRequest, OrderResponse, Position, Account, 
    TradeRequest, TradeResponse
)

logger = logging.getLogger(__name__)

class TradeLockerExecutor(BaseExecutor):
    """TradeLocker trading executor using Brand API"""
    
    def __init__(self):
        config = settings.get_broker_config("tradelocker")
        super().__init__(config)
        self.config = config
        super().__init__(config)
        self.config = settings.get_broker_config("tradelocker")
        self.api_url = self.config["api_url"]
        self.ws_url = self.config["ws_url"]
        self.api_key = self.config["api_key"]
        self.environment = self.config["environment"]
        self.session = None
        self.sio = None
        self.access_token = None
        
    async def initialize(self) -> bool:
        """Initialize TradeLocker connection"""
        try:
            # Initialize HTTP client
            self.session = httpx.AsyncClient(
                base_url=self.api_url,
                headers={"brand-api-key": self.api_key},
                timeout=30.0
            )
            
            # Initialize WebSocket client
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
            
            self.is_connected = True
            logger.info("TradeLocker executor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"TradeLocker initialization failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from TradeLocker"""
        if self.sio:
            await self.sio.disconnect()
        if self.session:
            await self.session.aclose()
        self.is_connected = False
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
                
        except Exception as e:
            logger.error(f"Error placing TradeLocker order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify existing order in TradeLocker"""
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
                
        except Exception as e:
            logger.error(f"Error closing TradeLocker position: {e}")
            return TradeResponse(
                success=False,
                error=str(e)
            )
    
    async def get_account_info(self, account_id: str) -> Optional[Account]:
        """Get specific account information"""
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
    
    async def get_symbols(self) -> List[str]:
        """Get available symbols from TradeLocker"""
        try:
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
        return []
    
    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote for symbol"""
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

