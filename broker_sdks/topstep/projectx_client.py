#!/usr/bin/env python3
"""
TopStep/ProjectX Gateway API Client
Aligned with official ProjectX Gateway API documentation:
- https://gateway.docs.projectx.com/
- https://help.topstep.com/en/articles/11187768-topstepx-api-access

TopStepX is accessed through the ProjectX Gateway API.
"""

import requests
import json
import os
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProjectXClient:
    """
    ProjectX Gateway API Client for TopStepX
    
    Official API Base URL:
    - Gateway API: https://gateway.projectx.com/api (or environment-specific)
    
    Authentication:
    - Username and API Key
    - JWT token after authentication
    """
    
    def __init__(
        self,
        username: str,
        api_key: str,
        environment: str = "TopstepX"  # Can be "Demo", "TopstepX", etc.
    ):
        """
        Initialize ProjectX client
        
        Args:
            username: TopStep username/email
            api_key: TopStep API key
            environment: Trading platform name (default: "TopstepX")
        """
        self.username = username
        self.api_key = api_key
        self.environment = environment
        
        # Base URL - ProjectX Gateway API
        # Demo: https://gateway-api-demo.s2f.projectx.com/api
        # Live: https://gateway-api.s2f.projectx.com/api or https://gateway.projectx.com/api
        if "demo" in environment.lower():
            self.base_url = "https://gateway-api-demo.s2f.projectx.com/api"
        else:
            self.base_url = "https://gateway-api.s2f.projectx.com/api"
        
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Username": self.username
        })
        
        self.token = None
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate and get JWT token
        
        Uses ProjectX Gateway API authentication endpoint:
        POST /Auth/loginKey
        """
        try:
            # ProjectX Gateway API uses /Auth/loginKey endpoint
            auth_data = {
                "userName": self.username,
                "apiKey": self.api_key
            }
            
            response = requests.post(
                f"{self.base_url}/Auth/loginKey",
                json=auth_data,
                headers={"Content-Type": "application/json", "Accept": "text/plain"},
                timeout=10
            )
            response.raise_for_status()
            
            # Response is typically plain text token or JSON with token field
            auth_response = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"token": response.text.strip()}
            self.token = auth_response.get("token") or auth_response.get("accessToken")
            
            if self.token:
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
        except Exception as e:
            logger.warning(f"Authentication failed, continuing without token: {e}")
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to ProjectX Gateway API"""
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
            logger.error(f"ProjectX API error: {e}")
            raise
    
    # Account Management
    
    def list_accounts(self) -> List[Dict[str, Any]]:
        """
        List all accounts for the authenticated user
        
        Uses ProjectX Gateway API: POST /Account/search
        
        Returns:
            List of account dictionaries with account_id, acc_num, account_name, etc.
        """
        # ProjectX Gateway uses POST for search endpoints
        response = self._request("POST", "/Account/search", data={})
        # Response may be a list directly or wrapped in a data/accounts field
        if isinstance(response, list):
            return response
        return response.get("accounts", response.get("data", []))
    
    def get_account(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get account information
        
        Args:
            account_id: Account ID (if None, returns first account)
        
        Returns:
            Account dictionary
        """
        accounts = self.list_accounts()
        if not accounts:
            raise ValueError("No accounts found")
        
        if account_id:
            for acc in accounts:
                if acc.get("id") == account_id or acc.get("account_id") == account_id:
                    return acc
            raise ValueError(f"Account not found: {account_id}")
        
        return accounts[0]
    
    def get_account_balance(self, account_id: Optional[str] = None) -> float:
        """Get account balance"""
        account = self.get_account(account_id)
        return account.get("balance", 0.0)
    
    def get_account_equity(self, account_id: Optional[str] = None) -> float:
        """Get account equity"""
        account = self.get_account(account_id)
        return account.get("equity", 0.0)
    
    # Contract/Instrument Management
    
    def search_contracts(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Search for contracts by symbol
        
        Uses ProjectX Gateway API: POST /Contract/search
        
        Args:
            symbol: Contract symbol (e.g., "MES", "MNQ", "MYM")
        
        Returns:
            List of contract dictionaries
        """
        # ProjectX Gateway uses POST for search endpoints
        response = self._request("POST", "/Contract/search", data={"symbol": symbol})
        # Response may be a list directly or wrapped
        if isinstance(response, list):
            return response
        return response.get("contracts", response.get("data", []))
    
    def get_contract(self, symbol: str) -> Dict[str, Any]:
        """
        Get contract details for symbol
        
        Args:
            symbol: Contract symbol
        
        Returns:
            Contract dictionary with id, symbol, name, etc.
        """
        contracts = self.search_contracts(symbol)
        if not contracts:
            raise ValueError(f"Contract not found: {symbol}")
        return contracts[0]
    
    def get_contract_id(self, symbol: str) -> str:
        """Get contract ID for symbol"""
        contract = self.get_contract(symbol)
        return contract.get("id") or contract.get("contract_id")
    
    # Order Management
    
    def place_order(
        self,
        account_id: str,
        symbol: str,
        side: str,  # "buy" or "sell"
        size: int,  # Contract size (number of contracts)
        order_type: str = "market",  # "market", "limit", "stop"
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        take_profit_2: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place an order
        
        Args:
            account_id: Account ID
            symbol: Contract symbol (e.g., "MES")
            side: "buy" or "sell"
            size: Number of contracts
            order_type: Order type ("market", "limit", "stop")
            price: Limit/stop price
            stop_loss: Stop loss price
            take_profit: Take profit price (TP1)
            take_profit_2: Second take profit price (TP2)
        
        Returns:
            Order dictionary with order_id, status, etc.
        """
        contract = self.get_contract(symbol)
        contract_id = contract.get("id") or contract.get("contract_id")
        
        order_data = {
            "accountId": account_id,
            "contractId": contract_id,
            "side": side.lower(),
            "type": order_type.lower(),
            "size": size
        }
        
        if price:
            order_data["price"] = price
        
        if stop_loss:
            order_data["stopLoss"] = stop_loss
        
        if take_profit:
            order_data["takeProfit"] = take_profit
        
        if take_profit_2:
            order_data["takeProfit2"] = take_profit_2
        
        # ProjectX Gateway API uses /Order/place endpoint
        response = self._request("POST", "/Order/place", data=order_data)
        return response
    
    def modify_order(
        self,
        order_id: str,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Modify an existing order
        
        Args:
            order_id: Order ID to modify
            price: New limit/stop price
            stop_loss: New stop loss
            take_profit: New take profit
            size: New size (for partial close)
        
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
        if size is not None:
            update_data["size"] = size
        
        # ProjectX Gateway API uses /Order/modify endpoint
        update_data["orderId"] = order_id
        response = self._request("POST", "/Order/modify", data=update_data)
        return response
    
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            Cancellation confirmation
        """
        # ProjectX Gateway API uses /Order/cancel endpoint
        cancel_data = {"orderId": order_id}
        response = self._request("POST", "/Order/cancel", data=cancel_data)
        return response
    
    def get_orders(
        self,
        account_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get orders for account
        
        Args:
            account_id: Account ID
            status: Filter by status
        
        Returns:
            List of order dictionaries
        """
        params = {}
        if account_id:
            params["accountId"] = account_id
        if status:
            params["status"] = status
        
        # ProjectX Gateway API uses POST /Order/search or /Order/searchOpen
        search_data = {}
        if account_id:
            search_data["accountId"] = account_id
        if status:
            search_data["status"] = status
        
        endpoint = "/Order/searchOpen" if status == "open" else "/Order/search"
        response = self._request("POST", endpoint, data=search_data)
        if isinstance(response, list):
            return response
        return response.get("orders", response.get("data", []))
    
    # Position Management
    
    def get_positions(
        self,
        account_id: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get open positions
        
        Args:
            account_id: Account ID
            symbol: Optional symbol filter
        
        Returns:
            List of position dictionaries
        """
        params = {}
        if account_id:
            params["accountId"] = account_id
        if symbol:
            params["symbol"] = symbol
        
        # ProjectX Gateway API uses POST /Position/searchOpen
        search_data = {}
        if account_id:
            search_data["accountId"] = account_id
        if symbol:
            search_data["symbol"] = symbol
        
        response = self._request("POST", "/Position/searchOpen", data=search_data)
        if isinstance(response, list):
            return response
        return response.get("positions", response.get("data", []))
    
    def close_position(
        self,
        position_id: str,
        size: Optional[int] = None  # None = full close, int = partial close
    ) -> Dict[str, Any]:
        """
        Close a position (full or partial)
        
        Args:
            position_id: Position ID to close
            size: Size to close (None = full close)
        
        Returns:
            Closure confirmation
        """
        close_data = {}
        if size:
            close_data["size"] = size
        
        # ProjectX Gateway API uses /Position/closeContract endpoint
        close_data["accountId"] = account_id if account_id else self.get_account().get("id")
        close_data["contractId"] = position_id  # In ProjectX, position_id is typically contractId
        response = self._request("POST", "/Position/closeContract", data=close_data)
        return response
    
    def close_all_positions(
        self,
        account_id: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Close all positions (optionally filtered by symbol)
        
        Args:
            account_id: Account ID
            symbol: Optional symbol filter
        
        Returns:
            Closure confirmation
        """
        positions = self.get_positions(account_id, symbol)
        results = []
        
        if not account_id:
            account = self.get_account()
            account_id = account.get("id") or account.get("accountId")
        
        for position in positions:
            try:
                # ProjectX uses contractId for closing
                contract_id = position.get("contractId") or position.get("id")
                result = self.close_position(contract_id, account_id=account_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error closing position {position.get('id')}: {e}")
        
        return {"closed": len(results), "positions": results}
    
    def route_order(
        self,
        account_id: str,
        symbol: str,
        action: str,  # "buy" or "sell"
        size: int,
        entry: Optional[float] = None,
        tp1: Optional[float] = None,
        tp2: Optional[float] = None,
        sl: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Route order (convenience method matching TopStep terminology)
        
        Args:
            account_id: Account ID
            symbol: Contract symbol
            action: "buy" or "sell"
            size: Number of contracts
            entry: Entry price (for limit orders)
            tp1: Take profit 1
            tp2: Take profit 2
            sl: Stop loss
        
        Returns:
            Order dictionary
        """
        order_type = "limit" if entry else "market"
        return self.place_order(
            account_id=account_id,
            symbol=symbol,
            side=action,
            size=size,
            order_type=order_type,
            price=entry,
            stop_loss=sl,
            take_profit=tp1,
            take_profit_2=tp2
        )
    
    # Risk Management
    
    def get_risk_limits(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get risk limits for account
        
        Args:
            account_id: Account ID
        
        Returns:
            Risk limits dictionary
        """
        account = self.get_account(account_id)
        return account.get("riskLimits", {})
    
    # Portfolio Management
    
    def get_portfolio(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get portfolio summary
        
        Args:
            account_id: Account ID
        
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
            "unrealizedPnl": total_pnl,
            "positions": len(positions)
        }
    
    def get_equity_history(
        self,
        account_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get equity history
        
        Args:
            account_id: Account ID
            start_date: Start date
            end_date: End date
        
        Returns:
            List of equity data points
        """
        params = {}
        if account_id:
            params["accountId"] = account_id
        if start_date:
            params["startDate"] = start_date.isoformat()
        if end_date:
            params["endDate"] = end_date.isoformat()
        
        response = self._request("GET", "/equity/history", params=params)
        return response.get("history", [])
