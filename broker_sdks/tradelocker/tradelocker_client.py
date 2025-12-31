#!/usr/bin/env python3
"""
TradeLocker REST API Client
Aligned with official TradeLocker API documentation:
- https://public-api.tradelocker.com/
- https://tradelocker.com/portal/tradelocker-rest-api-traders/
- https://api.tradelocker.com/brand-api/socket/docs/ (WebSocket)
"""

import requests
import json
import os
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TradeLockerClient:
    """
    TradeLocker REST API Client
    
    Official API Base URLs:
    - Demo: https://demo.tradelocker.com
    - Live: https://live.tradelocker.com
    
    Authentication:
    - API Key in header: X-API-Key
    - Or JWT token in Authorization header
    """
    
    def __init__(
        self,
        server: str,
        api_key: Optional[str] = None,
        account_id: Optional[str] = None,
        acc_num: Optional[int] = None,
        environment: str = "demo"
    ):
        """
        Initialize TradeLocker client
        
        Args:
            server: Server name (e.g., "demo.tradelocker.com" or "live.tradelocker.com")
            api_key: API key for authentication
            account_id: Account ID
            acc_num: Account number
            environment: "demo" or "live"
        """
        self.server = server
        self.api_key = api_key
        self.account_id = account_id
        self.acc_num = acc_num
        self.environment = environment
        
        # Base URL based on server
        if "demo" in server.lower():
            self.base_url = f"https://demo.tradelocker.com"
        elif "live" in server.lower():
            self.base_url = f"https://live.tradelocker.com"
        else:
            self.base_url = f"https://{server}"
        
        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"X-API-Key": self.api_key})
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to TradeLocker API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=10)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, timeout=10)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"TradeLocker API error: {e}")
            raise
    
    # Account Management
    
    def list_accounts(self) -> List[Dict[str, Any]]:
        """
        List all accounts for the authenticated user
        
        Returns:
            List of account dictionaries with id, accNum, name, balance, equity, margin, status
        """
        response = self._request("GET", "/api/v1/accounts")
        return response.get("accounts", [])
    
    def get_account(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get account information
        
        Args:
            account_id: Account ID (uses self.account_id if not provided)
        
        Returns:
            Account dictionary
        """
        acc_id = account_id or self.account_id
        if not acc_id:
            raise ValueError("Account ID required")
        
        response = self._request("GET", f"/api/v1/accounts/{acc_id}")
        return response
    
    def get_account_balance(self, account_id: Optional[str] = None) -> float:
        """Get account balance"""
        account = self.get_account(account_id)
        return account.get("balance", 0.0)
    
    def get_account_equity(self, account_id: Optional[str] = None) -> float:
        """Get account equity"""
        account = self.get_account(account_id)
        return account.get("equity", 0.0)
    
    # Instrument/Symbol Management
    
    def get_instruments(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available instruments
        
        Args:
            symbol: Optional symbol filter (e.g., "EURUSD", "GBPUSD")
        
        Returns:
            List of instrument dictionaries
        """
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        response = self._request("GET", "/api/v1/instruments", params=params)
        return response.get("instruments", [])
    
    def resolve_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Resolve symbol to instrument details
        
        Args:
            symbol: Symbol name (e.g., "EURUSD")
        
        Returns:
            Instrument dictionary with contract details
        """
        instruments = self.get_instruments(symbol=symbol)
        if not instruments:
            raise ValueError(f"Symbol not found: {symbol}")
        return instruments[0]
    
    # Order Management
    
    def place_order(
        self,
        symbol: str,
        side: str,  # "buy" or "sell"
        quantity: float,
        order_type: str = "market",  # "market", "limit", "stop", "stop_limit"
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        account_id: Optional[str] = None,
        trailing_stop: Optional[float] = None,
        trailing_step: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place an order
        
        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            quantity: Order size (lot size)
            order_type: Order type ("market", "limit", "stop", "stop_limit")
            price: Limit/stop price (required for limit/stop orders)
            stop_loss: Stop loss price
            take_profit: Take profit price
            account_id: Account ID (uses self.account_id if not provided)
            trailing_stop: Trailing stop distance
            trailing_step: Trailing stop step
        
        Returns:
            Order dictionary with order_id, status, etc.
        """
        acc_id = account_id or self.account_id
        if not acc_id:
            raise ValueError("Account ID required")
        
        order_data = {
            "accountId": acc_id,
            "symbol": symbol,
            "side": side.lower(),
            "type": order_type.lower(),
            "quantity": quantity
        }
        
        if price:
            order_data["price"] = price
        
        if stop_loss:
            order_data["stopLoss"] = stop_loss
        
        if take_profit:
            order_data["takeProfit"] = take_profit
        
        if trailing_stop:
            order_data["trailingStop"] = trailing_stop
        
        if trailing_step:
            order_data["trailingStep"] = trailing_step
        
        response = self._request("POST", "/api/v1/orders", data=order_data)
        return response
    
    def modify_order(
        self,
        order_id: str,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        quantity: Optional[float] = None,
        trailing_stop: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Modify an existing order
        
        Args:
            order_id: Order ID to modify
            price: New limit/stop price
            stop_loss: New stop loss
            take_profit: New take profit
            quantity: New quantity (for partial close)
            trailing_stop: New trailing stop
        
        Returns:
            Updated order dictionary
        """
        update_data = {}
        
        if price is not None:
            update_data["price"] = price
        if stop_loss is not None:
            update_data["stopLoss"] = stop_loss
        if take_profit is not None:
            update_data["takeProfit"] = take_profit
        if quantity is not None:
            update_data["quantity"] = quantity
        if trailing_stop is not None:
            update_data["trailingStop"] = trailing_stop
        
        response = self._request("PUT", f"/api/v1/orders/{order_id}", data=update_data)
        return response
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            Cancellation confirmation
        """
        response = self._request("DELETE", f"/api/v1/orders/{order_id}")
        return response
    
    def get_orders(
        self,
        account_id: Optional[str] = None,
        status: Optional[str] = None  # "pending", "filled", "cancelled", "rejected"
    ) -> List[Dict[str, Any]]:
        """
        Get orders for account
        
        Args:
            account_id: Account ID (uses self.account_id if not provided)
            status: Filter by status
        
        Returns:
            List of order dictionaries
        """
        acc_id = account_id or self.account_id
        if not acc_id:
            raise ValueError("Account ID required")
        
        params = {"accountId": acc_id}
        if status:
            params["status"] = status
        
        response = self._request("GET", "/api/v1/orders", params=params)
        return response.get("orders", [])
    
    # Position Management
    
    def get_positions(
        self,
        account_id: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get open positions
        
        Args:
            account_id: Account ID (uses self.account_id if not provided)
            symbol: Optional symbol filter
        
        Returns:
            List of position dictionaries
        """
        acc_id = account_id or self.account_id
        if not acc_id:
            raise ValueError("Account ID required")
        
        params = {"accountId": acc_id}
        if symbol:
            params["symbol"] = symbol
        
        response = self._request("GET", "/api/v1/positions", params=params)
        return response.get("positions", [])
    
    def close_position(
        self,
        position_id: str,
        quantity: Optional[float] = None  # None = full close, float = partial close
    ) -> Dict[str, Any]:
        """
        Close a position (full or partial)
        
        Args:
            position_id: Position ID to close
            quantity: Quantity to close (None = full close)
        
        Returns:
            Closure confirmation
        """
        close_data = {}
        if quantity:
            close_data["quantity"] = quantity
        
        response = self._request("POST", f"/api/v1/positions/{position_id}/close", data=close_data)
        return response
    
    def close_all_positions(
        self,
        account_id: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Close all positions (optionally filtered by symbol)
        
        Args:
            account_id: Account ID (uses self.account_id if not provided)
            symbol: Optional symbol filter
        
        Returns:
            Closure confirmation with list of closed positions
        """
        positions = self.get_positions(account_id, symbol)
        results = []
        
        for position in positions:
            try:
                result = self.close_position(position["id"])
                results.append(result)
            except Exception as e:
                logger.error(f"Error closing position {position['id']}: {e}")
        
        return {"closed": len(results), "positions": results}
    
    def set_trailing_stop(
        self,
        position_id: str,
        trailing_stop: float,
        trailing_step: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Set trailing stop for a position
        
        Args:
            position_id: Position ID
            trailing_stop: Trailing stop distance
            trailing_step: Trailing stop step (optional)
        
        Returns:
            Updated position dictionary
        """
        update_data = {"trailingStop": trailing_stop}
        if trailing_step:
            update_data["trailingStep"] = trailing_step
        
        response = self._request("PUT", f"/api/v1/positions/{position_id}", data=update_data)
        return response
    
    # Portfolio/Portfolio Management
    
    def get_portfolio(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get portfolio summary (balance, equity, margin, PnL)
        
        Args:
            account_id: Account ID (uses self.account_id if not provided)
        
        Returns:
            Portfolio dictionary
        """
        account = self.get_account(account_id)
        positions = self.get_positions(account_id)
        
        total_pnl = sum(pos.get("unrealizedPnl", 0) for pos in positions)
        
        return {
            "accountId": account.get("id"),
            "balance": account.get("balance", 0.0),
            "equity": account.get("equity", 0.0),
            "margin": account.get("margin", 0.0),
            "freeMargin": account.get("freeMargin", 0.0),
            "unrealizedPnl": total_pnl,
            "positions": len(positions)
        }
    
    def get_pnl(self, account_id: Optional[str] = None) -> float:
        """Get total PnL (unrealized)"""
        portfolio = self.get_portfolio(account_id)
        return portfolio.get("unrealizedPnl", 0.0)
    
    # Market Data (if available via REST)
    
    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get current market data for symbol
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Market data dictionary (bid, ask, last, etc.)
        """
        response = self._request("GET", f"/api/v1/market-data/{symbol}")
        return response
    
    # Helper Methods
    
    def calculate_lot_size(self, symbol: str, risk_amount: float, stop_loss_pips: float) -> float:
        """
        Calculate lot size based on risk
        
        Args:
            symbol: Trading symbol
            risk_amount: Amount to risk
            stop_loss_pips: Stop loss in pips
        
        Returns:
            Lot size
        """
        # This is a simplified calculation - actual implementation depends on
        # contract specifications and pip values
        instrument = self.resolve_symbol(symbol)
        pip_value = instrument.get("pipValue", 0.0001)
        contract_size = instrument.get("contractSize", 100000)
        
        # Simplified calculation
        lot_size = risk_amount / (stop_loss_pips * pip_value * contract_size)
        return round(lot_size, 2)
