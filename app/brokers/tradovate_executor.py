"""
Tradovate Broker Executor
Handles all Tradovate trading operations via REST API and WebSocket
"""
import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
import websockets
from app.brokers.base_executor import BaseExecutor
from app.core.config import settings
from app.models.pydantic_schemas import (
    OrderRequest, OrderResponse, Position, Account, 
    TradeRequest, TradeResponse
)

logger = logging.getLogger(__name__)

class TradovateExecutor(BaseExecutor):
    """Tradovate trading executor using REST API"""
    
    def __init__(self):
        config = settings.get_broker_config("tradovate")
        super().__init__(config)
        self.config = config
        super().__init__(config)
        self.config = settings.get_broker_config("tradovate")
        self.api_url = self.config["api_url"]
        self.ws_url = self.config["ws_url"]
        self.user_id = self.config["user_id"]
        self.password = self.config["password"]
        self.app_id = self.config["app_id"]
        self.app_version = self.config["app_version"]
        self.cid = self.config["cid"]
        self.sec = self.config["sec"]
        self.session = None
        self.access_token = None
        self.ws_connection = None
        
    async def initialize(self) -> bool:
        """Initialize Tradovate connection"""
        try:
            # Initialize HTTP client
            self.session = httpx.AsyncClient(
                base_url=self.api_url,
                timeout=30.0
            )
            
            # Authenticate and get access token
            auth_data = {
                "username": self.user_id,
                "password": self.password,
                "appId": self.app_id,
                "appVersion": self.app_version,
                "cid": self.cid,
                "sec": self.sec
            }
            
            response = await self.session.post("/auth/accesstokenrequest", json=auth_data)
            if response.status_code == 200:
                auth_result = response.json()
                self.access_token = auth_result.get("accessToken")
                
                # Set authorization header
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                
                # Initialize WebSocket connection
                await self._init_websocket()
                
                self.is_connected = True
                logger.info("Tradovate executor initialized successfully")
                return True
            else:
                logger.error(f"Tradovate auth failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Tradovate initialization failed: {e}")
            return False
    
    async def _init_websocket(self):
        """Initialize WebSocket connection"""
        try:
            self.ws_connection = await websockets.connect(
                self.ws_url,
                extra_headers={"Authorization": f"Bearer {self.access_token}"}
            )
            
            # Start WebSocket message handler
            asyncio.create_task(self._handle_websocket_messages())
            
        except Exception as e:
            logger.error(f"Failed to initialize Tradovate WebSocket: {e}")
    
    async def _handle_websocket_messages(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.ws_connection:
                data = json.loads(message)
                await self._process_websocket_message(data)
        except Exception as e:
            logger.error(f"WebSocket message handling error: {e}")
    
    async def _process_websocket_message(self, data):
        """Process WebSocket message"""
        try:
            event_type = data.get("e")
            
            if event_type == "order":
                await self._handle_order_update(data)
            elif event_type == "position":
                await self._handle_position_update(data)
            elif event_type == "account":
                await self._handle_account_update(data)
            elif event_type == "fill":
                await self._handle_fill_update(data)
                
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    async def _handle_order_update(self, data):
        """Handle order updates"""
        await self.emit_order_update(data)
    
    async def _handle_position_update(self, data):
        """Handle position updates"""
        await self.emit_position_update(data)
    
    async def _handle_account_update(self, data):
        """Handle account updates"""
        await self.emit_account_update(data)
    
    async def _handle_fill_update(self, data):
        """Handle fill updates"""
        await self.emit_trade_update(data)
    
    async def disconnect(self):
        """Disconnect from Tradovate"""
        if self.ws_connection:
            await self.ws_connection.close()
        if self.session:
            await self.session.aclose()
        self.is_connected = False
        logger.info("Tradovate executor disconnected")
    
    async def get_accounts(self) -> List[Account]:
        """Get all Tradovate accounts"""
        try:
            response = await self.session.get("/account/list")
            if response.status_code == 200:
                accounts_data = response.json()
                accounts = []
                
                for account_data in accounts_data:
                    account = Account(
                        id=str(account_data["accountId"]),
                        broker="tradovate",
                        account_type=account_data.get("accountType", "live"),
                        currency=account_data.get("currency", "USD"),
                        balance=float(account_data.get("cashBalance", 0)),
                        equity=float(account_data.get("totalCashValue", 0)),
                        margin=float(account_data.get("marginRequirement", 0)),
                        free_margin=float(account_data.get("availableFunds", 0)),
                        margin_level=0.0,  # Tradovate doesn't provide this directly
                        leverage=account_data.get("leverage", 1),
                        is_active=account_data.get("active", True),
                        is_live=account_data.get("accountType") == "live",
                        created_at=datetime.fromisoformat(account_data.get("creationTime", "2023-01-01")),
                        updated_at=datetime.now()
                    )
                    accounts.append(account)
                
                return accounts
            else:
                logger.error(f"Failed to get Tradovate accounts: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting Tradovate accounts: {e}")
            return []
    
    async def get_positions(self, account_id: Optional[str] = None) -> List[Position]:
        """Get open positions from Tradovate"""
        try:
            response = await self.session.get("/position/list")
            if response.status_code == 200:
                positions_data = response.json()
                positions = []
                
                for pos_data in positions_data:
                    if pos_data.get("netPos", 0) != 0:  # Has position
                        # Filter by account if specified
                        if account_id and str(pos_data.get("accountId")) != account_id:
                            continue
                            
                        position = Position(
                            id=str(pos_data["id"]),
                            broker="tradovate",
                            account_id=str(pos_data["accountId"]),
                            symbol=pos_data["contract"]["symbol"],
                            side="long" if pos_data["netPos"] > 0 else "short",
                            size=abs(float(pos_data["netPos"])),
                            entry_price=float(pos_data.get("averagePrice", 0)),
                            current_price=float(pos_data.get("marketValue", 0)),
                            unrealized_pnl=float(pos_data.get("unrealizedPnl", 0)),
                            realized_pnl=float(pos_data.get("realizedPnl", 0)),
                            margin=float(pos_data.get("marginRequirement", 0)),
                            magic_number=0,
                            comment=pos_data.get("description", ""),
                            open_time=datetime.fromisoformat(pos_data.get("creationTime", "2023-01-01")),
                            close_time=None,
                            is_active=True
                        )
                        positions.append(position)
                
                return positions
            else:
                logger.error(f"Failed to get Tradovate positions: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting Tradovate positions: {e}")
            return []
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order with Tradovate"""
        try:
            # Map order types
            order_type_map = {
                "market_buy": {"orderType": "Market", "side": "Buy"},
                "market_sell": {"orderType": "Market", "side": "Sell"},
                "buy_limit": {"orderType": "Limit", "side": "Buy"},
                "sell_limit": {"orderType": "Limit", "side": "Sell"},
                "buy_stop": {"orderType": "StopMarket", "side": "Buy"},
                "sell_stop": {"orderType": "StopMarket", "side": "Sell"}
            }
            
            order_config = order_type_map.get(order.order_type)
            if not order_config:
                return OrderResponse(
                    success=False,
                    error=f"Unsupported order type: {order.order_type}"
                )
            
            # Get contract details
            contract_response = await self.session.get(
                f"/contract/find?symbol={order.symbol}"
            )
            if contract_response.status_code != 200:
                return OrderResponse(
                    success=False,
                    error=f"Symbol {order.symbol} not found"
                )
            
            contract = contract_response.json()[0]
            
            order_data = {
                "accountId": int(order.account_id),
                "contractId": contract["contractId"],
                "orderType": order_config["orderType"],
                "side": order_config["side"],
                "orderQty": order.quantity,
                "price": order.price,
                "stopPrice": order.stop_loss,
                "isAutomated": True
            }
            
            response = await self.session.post("/order/placeorder", json=order_data)
            
            if response.status_code == 200:
                result = response.json()
                
                return OrderResponse(
                    success=True,
                    order_id=str(result.get("orderId")),
                    broker="tradovate",
                    status=result.get("status", "submitted"),
                    filled_quantity=result.get("filledQty", 0),
                    filled_price=result.get("avgFillPrice", 0),
                    commission=result.get("commission", 0),
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"Tradovate order failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error placing Tradovate order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify existing order in Tradovate"""
        try:
            modify_data = {
                "orderId": int(order_id),
                "price": modifications.get("price"),
                "stopPrice": modifications.get("stop_loss")
            }
            
            response = await self.session.post("/order/modifyorder", json=modify_data)
            
            if response.status_code == 200:
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="tradovate",
                    status="modified",
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"Tradovate order modification failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error modifying Tradovate order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel order in Tradovate"""
        try:
            cancel_data = {
                "orderId": int(order_id)
            }
            
            response = await self.session.post("/order/cancelorder", json=cancel_data)
            
            if response.status_code == 200:
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="tradovate",
                    status="cancelled",
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"Tradovate order cancellation failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error cancelling Tradovate order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def close_position(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position in Tradovate"""
        try:
            # Get position details
            response = await self.session.get(f"/position/item?id={position_id}")
            if response.status_code != 200:
                return TradeResponse(
                    success=False,
                    error="Position not found"
                )
            
            position = response.json()
            
            # Determine close side (opposite of current position)
            close_side = "Sell" if position["netPos"] > 0 else "Buy"
            close_quantity = quantity or abs(position["netPos"])
            
            close_data = {
                "accountId": position["accountId"],
                "contractId": position["contractId"],
                "orderType": "Market",
                "side": close_side,
                "orderQty": close_quantity,
                "isAutomated": True
            }
            
            response = await self.session.post("/order/placeorder", json=close_data)
            
            if response.status_code == 200:
                result = response.json()
                
                return TradeResponse(
                    success=True,
                    trade_id=str(result.get("orderId")),
                    broker="tradovate",
                    symbol=position["contract"]["symbol"],
                    side=close_side.lower(),
                    quantity=close_quantity,
                    price=result.get("avgFillPrice", 0),
                    pnl=result.get("realizedPnl", 0),
                    commission=result.get("commission", 0),
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"Tradovate position close failed: {error_msg}")
                return TradeResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error closing Tradovate position: {e}")
            return TradeResponse(
                success=False,
                error=str(e)
            )
    
    async def get_account_info(self, account_id: str) -> Optional[Account]:
        """Get specific account information"""
        try:
            response = await self.session.get(f"/account/item?id={account_id}")
            if response.status_code == 200:
                account_data = response.json()
                
                account = Account(
                    id=str(account_data["accountId"]),
                    broker="tradovate",
                    account_type=account_data.get("accountType", "live"),
                    currency=account_data.get("currency", "USD"),
                    balance=float(account_data.get("cashBalance", 0)),
                    equity=float(account_data.get("totalCashValue", 0)),
                    margin=float(account_data.get("marginRequirement", 0)),
                    free_margin=float(account_data.get("availableFunds", 0)),
                    margin_level=0.0,
                    leverage=account_data.get("leverage", 1),
                    is_active=account_data.get("active", True),
                    is_live=account_data.get("accountType") == "live",
                    created_at=datetime.fromisoformat(account_data.get("creationTime", "2023-01-01")),
                    updated_at=datetime.now()
                )
                
                return account
            else:
                logger.error(f"Failed to get Tradovate account {account_id}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting Tradovate account {account_id}: {e}")
            return None
    
    async def get_symbols(self) -> List[str]:
        """Get available symbols from Tradovate"""
        try:
            response = await self.session.get("/contract/find")
            if response.status_code == 200:
                contracts_data = response.json()
                return [contract["symbol"] for contract in contracts_data]
            else:
                logger.error(f"Failed to get Tradovate symbols: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting Tradovate symbols: {e}")
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

