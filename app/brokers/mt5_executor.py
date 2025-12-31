"""
MT5 Broker Executor
Handles all MT5 trading operations via Manager API
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
from app.brokers.base_executor import BaseExecutor
from app.core.config import settings
from app.models.pydantic_schemas import (
    OrderRequest, OrderResponse, Position, Account, 
    TradeRequest, TradeResponse
)

logger = logging.getLogger(__name__)

class MT5Executor(BaseExecutor):
    """MT5 trading executor using Manager API"""
    
    def __init__(self):
        config = settings.get_broker_config("mt5")
        super().__init__(config)
        self.config = config
        super().__init__(config)
        self.config = settings.get_broker_config("mt5")
        self.api_url = self.config["api_url"]
        self.manager_host = self.config["manager_host"]
        self.manager_port = self.config["manager_port"]
        self.manager_login = self.config["manager_login"]
        self.manager_password = self.config["manager_password"]
        self.session = None
        
    async def initialize(self) -> bool:
        """Initialize MT5 connection"""
        try:
            self.session = httpx.AsyncClient(
                base_url=self.api_url,
                timeout=30.0
            )
            
            # Test connection with auth
            auth_data = {
                "login": self.manager_login,
                "password": self.manager_password
            }
            
            response = await self.session.post("/auth/login", json=auth_data)
            if response.status_code == 200:
                self.is_connected = True
                logger.info("MT5 executor initialized successfully")
                return True
            else:
                logger.error(f"MT5 auth failed: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"MT5 initialization failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MT5"""
        if self.session:
            await self.session.aclose()
            self.is_connected = False
            logger.info("MT5 executor disconnected")
    
    async def get_accounts(self) -> List[Account]:
        """Get all MT5 accounts"""
        try:
            response = await self.session.get("/users")
            if response.status_code == 200:
                users_data = response.json()
                accounts = []
                
                for user in users_data:
                    account = Account(
                        id=str(user["login"]),
                        broker="mt5",
                        account_type=user.get("group", "standard"),
                        currency=user.get("currency", "USD"),
                        balance=float(user.get("balance", 0)),
                        equity=float(user.get("equity", 0)),
                        margin=float(user.get("margin", 0)),
                        free_margin=float(user.get("margin_free", 0)),
                        margin_level=float(user.get("margin_level", 0)),
                        leverage=user.get("leverage", 100),
                        is_active=user.get("enable", True),
                        is_live=user.get("enable", True),
                        created_at=datetime.fromtimestamp(user.get("regdate", 0)),
                        updated_at=datetime.now()
                    )
                    accounts.append(account)
                
                return accounts
            else:
                logger.error(f"Failed to get MT5 accounts: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting MT5 accounts: {e}")
            return []
    
    async def get_positions(self, account_id: Optional[str] = None) -> List[Position]:
        """Get open positions from MT5"""
        try:
            params = {}
            if account_id:
                params["login"] = account_id
                
            response = await self.session.get("/trades", params=params)
            if response.status_code == 200:
                trades_data = response.json()
                positions = []
                
                for trade in trades_data:
                    if trade["close_time"] == 0:  # Open position
                        position = Position(
                            id=str(trade["order"]),
                            broker="mt5",
                            account_id=str(trade["login"]),
                            symbol=trade["symbol"],
                            side="buy" if trade["cmd"] == 0 else "sell",
                            size=float(trade["volume"]),
                            entry_price=float(trade["open_price"]),
                            current_price=float(trade.get("close_price", trade["open_price"])),
                            unrealized_pnl=float(trade.get("profit", 0)),
                            realized_pnl=0.0,
                            margin=float(trade.get("margin", 0)),
                            magic_number=trade.get("magic", 0),
                            comment=trade.get("comment", ""),
                            open_time=datetime.fromtimestamp(trade["open_time"]),
                            close_time=None,
                            is_active=True
                        )
                        positions.append(position)
                
                return positions
            else:
                logger.error(f"Failed to get MT5 positions: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting MT5 positions: {e}")
            return []
    
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order with MT5"""
        try:
            # Convert order type to MT5 command
            cmd_map = {
                "market_buy": 0,    # OP_BUY
                "market_sell": 1,   # OP_SELL
                "buy_limit": 2,     # OP_BUY_LIMIT
                "sell_limit": 3,    # OP_SELL_LIMIT
                "buy_stop": 4,      # OP_BUY_STOP
                "sell_stop": 5      # OP_SELL_STOP
            }
            
            cmd = cmd_map.get(order.order_type)
            if cmd is None:
                return OrderResponse(
                    success=False,
                    error=f"Unsupported order type: {order.order_type}"
                )
            
            trade_data = {
                "login": order.account_id,
                "symbol": order.symbol,
                "cmd": cmd,
                "volume": order.quantity,
                "price": order.price or 0,
                "sl": order.stop_loss or 0,
                "tp": order.take_profit or 0,
                "comment": order.comment or "",
                "magic": order.magic_number or 0
            }
            
            response = await self.session.post("/trades", json=trade_data)
            
            if response.status_code == 200:
                result = response.json()
                
                # Get order ticket from response
                order_ticket = result.get("order", 0)
                
                return OrderResponse(
                    success=True,
                    order_id=str(order_ticket),
                    broker="mt5",
                    status="filled" if cmd in [0, 1] else "pending",
                    filled_quantity=order.quantity,
                    filled_price=result.get("price", order.price),
                    commission=result.get("commission", 0),
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"MT5 order failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error placing MT5 order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify existing order in MT5"""
        try:
            modify_data = {
                "order": int(order_id),
                "price": modifications.get("price", 0),
                "sl": modifications.get("stop_loss", 0),
                "tp": modifications.get("take_profit", 0)
            }
            
            response = await self.session.put(f"/orders/{order_id}", json=modify_data)
            
            if response.status_code == 200:
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="mt5",
                    status="modified",
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"MT5 order modification failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error modifying MT5 order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel order in MT5"""
        try:
            response = await self.session.delete(f"/orders/{order_id}")
            
            if response.status_code == 200:
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="mt5",
                    status="cancelled",
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"MT5 order cancellation failed: {error_msg}")
                return OrderResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error cancelling MT5 order: {e}")
            return OrderResponse(
                success=False,
                error=str(e)
            )
    
    async def close_position(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position in MT5"""
        try:
            # Get position details first
            response = await self.session.get(f"/trades/{position_id}")
            if response.status_code != 200:
                return TradeResponse(
                    success=False,
                    error="Position not found"
                )
            
            position = response.json()
            
            # Determine close command (opposite of open command)
            close_cmd = 1 if position["cmd"] == 0 else 0  # OP_SELL if OP_BUY, vice versa
            
            close_data = {
                "login": position["login"],
                "symbol": position["symbol"],
                "cmd": close_cmd,
                "volume": quantity or position["volume"],
                "price": 0,  # Market close
                "comment": f"Close position {position_id}",
                "magic": position.get("magic", 0)
            }
            
            response = await self.session.delete(f"/trades/{position_id}", json=close_data)
            
            if response.status_code == 200:
                result = response.json()
                return TradeResponse(
                    success=True,
                    trade_id=str(result.get("order", position_id)),
                    broker="mt5",
                    symbol=position["symbol"],
                    side="sell" if close_cmd == 1 else "buy",
                    quantity=quantity or position["volume"],
                    price=result.get("price", 0),
                    pnl=result.get("profit", 0),
                    commission=result.get("commission", 0),
                    timestamp=datetime.now()
                )
            else:
                error_msg = response.text
                logger.error(f"MT5 position close failed: {error_msg}")
                return TradeResponse(
                    success=False,
                    error=error_msg
                )
                
        except Exception as e:
            logger.error(f"Error closing MT5 position: {e}")
            return TradeResponse(
                success=False,
                error=str(e)
            )
    
    async def get_account_info(self, account_id: str) -> Optional[Account]:
        """Get specific account information"""
        try:
            response = await self.session.get(f"/users/{account_id}")
            if response.status_code == 200:
                user_data = response.json()
                
                account = Account(
                    id=str(user_data["login"]),
                    broker="mt5",
                    account_type=user_data.get("group", "standard"),
                    currency=user_data.get("currency", "USD"),
                    balance=float(user_data.get("balance", 0)),
                    equity=float(user_data.get("equity", 0)),
                    margin=float(user_data.get("margin", 0)),
                    free_margin=float(user_data.get("margin_free", 0)),
                    margin_level=float(user_data.get("margin_level", 0)),
                    leverage=user_data.get("leverage", 100),
                    is_active=user_data.get("enable", True),
                    is_live=user_data.get("enable", True),
                    created_at=datetime.fromtimestamp(user_data.get("regdate", 0)),
                    updated_at=datetime.now()
                )
                
                return account
            else:
                logger.error(f"Failed to get MT5 account {account_id}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting MT5 account {account_id}: {e}")
            return None
    
    async def get_symbols(self) -> List[str]:
        """Get available symbols from MT5"""
        try:
            response = await self.session.get("/symbols")
            if response.status_code == 200:
                symbols_data = response.json()
                return [symbol["symbol"] for symbol in symbols_data]
            else:
                logger.error(f"Failed to get MT5 symbols: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting MT5 symbols: {e}")
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

