"""
Base class for broker executors
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime


class BaseExecutor(ABC):
    """Base class for all broker executors"""

    def __init__(self, account_config: Dict[str, Any]):
        self.account_config = account_config
        self.api_key = account_config.get("api_key")
        self.api_secret = account_config.get("api_secret")
        self.access_token = account_config.get("access_token")
        self.account_number = account_config.get("account_number")
        self.broker = account_config.get("broker")

    @abstractmethod
    async def connect(self) -> bool:
        """
        Connect to broker API
        Returns True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def disconnect(self):
        """Disconnect from broker API"""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with broker API"""
        pass

    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information
        Returns: {balance, equity, margin, free_margin, margin_level}
        """
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get open positions
        Returns list of positions
        """
        pass

    @abstractmethod
    async def get_orders(self) -> List[Dict[str, Any]]:
        """
        Get pending orders
        Returns list of orders
        """
        pass

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Place a new order
        Returns: {order_id, status, message}
        """
        pass

    @abstractmethod
    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[float] = None,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Modify existing order
        Returns: {success, message}
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel order
        Returns: {success, message}
        """
        pass

    @abstractmethod
    async def close_position(
        self,
        position_id: str,
        quantity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Close position (fully or partially)
        Returns: {success, closed_quantity, message}
        """
        pass

    @abstractmethod
    async def modify_position(
        self,
        position_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Modify position stop loss / take profit
        Returns: {success, message}
        """
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get current quote for symbol
        Returns: {symbol, bid, ask, last, timestamp}
        """
        pass

    async def execute_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute trading signal
        This is a common method that can be overridden
        """
        action = signal.get("action", "").lower()
        symbol = signal.get("symbol")
        quantity = signal.get("quantity", 1.0)
        price = signal.get("price")
        stop_loss = signal.get("stop_loss")
        take_profit = signal.get("take_profit")

        try:
            if action in ["buy", "sell"]:
                result = await self.place_order(
                    symbol=symbol,
                    side=action,
                    quantity=quantity,
                    order_type="market" if not price else "limit",
                    price=price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
                return {
                    "success": True,
                    "action": action,
                    "result": result,
                }

            elif action in ["close", "close_position"]:
                # Close all positions for symbol
                positions = await self.get_positions()
                results = []
                for pos in positions:
                    if pos.get("symbol") == symbol:
                        close_result = await self.close_position(pos.get("position_id"))
                        results.append(close_result)

                return {
                    "success": True,
                    "action": "close",
                    "results": results,
                }

            elif action == "modify":
                positions = await self.get_positions()
                results = []
                for pos in positions:
                    if pos.get("symbol") == symbol:
                        modify_result = await self.modify_position(
                            pos.get("position_id"),
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                        )
                        results.append(modify_result)

                return {
                    "success": True,
                    "action": "modify",
                    "results": results,
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp"""
        timestamp = datetime.utcnow().isoformat()
        print(f"[{timestamp}] [{self.broker.upper()}] [{level}] {message}")

    def is_connected(self) -> bool:
        """Check if broker is connected"""
        return hasattr(self, 'session') and self.session is not None and not self.session.is_closed

