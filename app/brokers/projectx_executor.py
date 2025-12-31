"""
ProjectX/TopStep Broker Executor
Handles all ProjectX and TopStep trading operations via Gateway API
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

class ProjectXExecutor(BaseExecutor):
    """ProjectX/TopStep trading executor using Gateway API"""
    
    def __init__(self):
        config = settings.get_broker_config("projectx")
        super().__init__(config)
        self.config = config
        super().__init__(config)
        self.config = settings.get_broker_config("projectx")
        self.api_url = self.config["api_url"]
        self.ws_url = self.config["ws_url"]
        self.api_token = self.config["api_token"]
        self.environment = self.config["environment"]
        self.session = None
        self.ws_connection = None
        
    async def initialize(self) -> bool:
        """Initialize ProjectX connection"""
        try:
            # Initialize HTTP client
            self.session = httpx.AsyncClient(
                base_url=self.api_url,
                headers={"Authorization": f"Bearer {self.api_token}"},
                timeout=30.0
            )
            
            # Test connection
            response = await self.session.get("/auth/validate")
            if response.status_code == 200:
                
                # Initialize WebSocket connection
                await self._init_websocket()
                
                self.is_connected = True
                logger.info("ProjectX executor initialized successfully")
                return True
            else:
                logger.error(f"ProjectX auth failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"ProjectX initialization failed: {e}")
            return False
    
    async def _init_websocket(self):
        """Initialize WebSocket connection"""
        try:
            self.ws_connection = await websockets.connect(
                self.ws_url,
                extra_headers={"Authorization": f"Bearer {self.api_token}"}
            )
            
            # Start WebSocket message handler
            asyncio.create_task(self._handle_websocket_messages())
            
        except Exception as e:
            logger.error(f"Failed to initialize ProjectX WebSocket: {e}")
    
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
            event_type = data.get("type")
            
            if event_type == "account_update":
                await self._handle_account_update(data)
            elif event_type == "position_update":
                await self._handle_position_update(data)
            elif event_type == "order_update":
                await self._handle_order_update(data)
            elif event_type == "trade_update":
                await self._handle_trade_update(data)
                
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    async def _handle_account_update(self, data):
        """Handle account updates"""
        await self.emit_account_update(data)
    
    async def _handle_position_update(self, data):
        """Handle position updates"""
        await self.emit_position_update(data)
    
    async def _handle_order_update(self, data):
        """Handle order updates"""
        await self.emit_order_update(data)
    
    async def _handle_trade_update(self, data):
        """Handle trade updates"""
        await self.emit_trade_update(data)
    
    async def disconnect(self):
        """Disconnect from ProjectX"""
        if self.ws_connection:
            await self.ws_connection.close()
        if self.session:
            await self.session.aclose()
        self.is_connected = False
        logger.info("ProjectX executor disconnected")
    
    async def get_accounts(self) -> List[Account]:
        """Get all ProjectX accounts"""
        try:
            response = await self.session.get("/accounts")
            if response.status_code == 200:
                accounts_data = response.json()
                accounts = []
                
                for account_data in accounts_data:
                    account = Account(
                        id=str(account_data["id"]),
                        broker="projectx",
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
                logger.error(f"Failed to get ProjectX accounts: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting ProjectX accounts: {e}")
            return []
    
    async def get_positions(self, account_id: Optional[str] = None) -> List[Position]:
        """Get open positions from ProjectX"""
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
                            broker="projectx",
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
                logger.error(f"Failed to get ProjectX positions: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting ProjectX positions: {e}")
            return []
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order with ProjectX"""
        try:
            # Map order types
            order_type_map = {
                "market_buy": {"type": "market", "side": "buy"},
                "market_sell": {"type": "market", "side": "sell"},
                "buy_limit": {"type": "limit", "side": "buy"},
                "sell_limit": {"type": "limit", "side": "sell"},
                "buy_stop": {"type": "stop", "side": "buy"},
                "sell_stop": {"type": "stop", "side": "sell"}
            }
            
            order_config = order_type_map.get(order.order_type)
            if not order_config:
                return OrderResponse(
                    success=False,
                    error=f"Unsupported order type: {order.order_type}"
                )
            
            order_data = {
                "account_id": order.account_id,
                "symbol": order.symbol,
                "type": order_config["type"],
                "side": order_config["side"],
                "quantity": order.quantity,
                "price": order.price,
                "stop_loss": order.stop_loss,
                "take_profit": order.take_profit,
                "comment": order.comment,
                "magic_number": order.magic_number
            }
            
            response = await self.session.post("/orders", json=order_data)
            
            if response.status_code == 200:
                result = response.json()
                
                return OrderResponse(
                    success=True,
                    order_id=str(result.get("id")),
                    broker="projectx",
                    status=result.get("status", "submitted"),
                    filled_quantity=result.get("filled_quantity", order.quantity),
                    filled_price=result.get("filled_price", order.price),
                    commission=result.get("commission", 0),
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"ProjectX order failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error placing ProjectX order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify existing order in ProjectX"""
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
                    broker="projectx",
                    status="modified",
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"ProjectX order modification failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error modifying ProjectX order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel order in ProjectX"""
        try:
            response = await self.session.delete(f"/orders/{order_id}")
            
            if response.status_code == 200:
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="projectx",
                    status="cancelled",
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"ProjectX order cancellation failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error cancelling ProjectX order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def close_position(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position in ProjectX"""
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
                    broker="projectx",
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
                logger.error(f"ProjectX position close failed: {error_msg}")
                return TradeResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error closing ProjectX position: {e}")
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
                    broker="projectx",
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
                logger.error(f"Failed to get ProjectX account {account_id}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting ProjectX account {account_id}: {e}")
            return None
    
    async def get_evaluations(self) -> List[Dict[str, Any]]:
        """Get evaluation accounts (TopStep specific)"""
        try:
            response = await self.session.get("/evaluations")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get evaluations: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting evaluations: {e}")
            return []
    
    async def get_evaluation_progress(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        """Get evaluation progress"""
        try:
            response = await self.session.get(f"/evaluations/{evaluation_id}/progress")
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get evaluation progress: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting evaluation progress: {e}")
            return None
    
    async def get_symbols(self) -> List[str]:
        """Get available symbols from ProjectX"""
        try:
            response = await self.session.get("/instruments")
            if response.status_code == 200:
                instruments_data = response.json()
                return [instrument["symbol"] for instrument in instruments_data]
            else:
                logger.error(f"Failed to get ProjectX symbols: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting ProjectX symbols: {e}")
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

