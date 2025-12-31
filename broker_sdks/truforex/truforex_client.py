#!/usr/bin/env python3
"""
TruForex MT4/MT5 Backend Client
Aligned with MT4/MT5 REST API patterns and TruForex backend implementation.

TruForex uses MT4/MT5 platforms with a REST API bridge/backend.
"""

import requests
import json
import os
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TruForexClient:
    """
    TruForex MT4/MT5 Backend Client
    
    This client communicates with the TruForex backend which bridges
    to MT4/MT5 platforms via REST API.
    
    Base URL: Configured via TRUFOREX_URL environment variable
    Default: http://localhost:5017
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        platform: str = "MT4"  # "MT4" or "MT5"
    ):
        """
        Initialize TruForex client
        
        Args:
            api_key: API key for authentication
            base_url: Backend base URL (defaults to env var or localhost:5017)
            platform: Platform type ("MT4" or "MT5")
        """
        self.api_key = api_key
        self.platform = platform
        self.base_url = base_url or os.getenv("TRUFOREX_URL", "http://localhost:5017")
        
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to TruForex backend"""
        url = f"{self.base_url}{endpoint}"
        
        # Add API key to params if not in headers (for GET requests)
        if params is None:
            params = {}
        if "api_key" not in params:
            params["api_key"] = self.api_key
        
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
            logger.error(f"TruForex API error: {e}")
            raise
    
    # User Management
    
    def verify_user(self) -> Dict[str, Any]:
        """
        Verify user and get user information
        
        Returns:
            User dictionary with username, platform, server, account_login
        """
        response = self._request("GET", "/users/verify")
        return response
    
    def heartbeat(self) -> Dict[str, Any]:
        """
        Send heartbeat to keep connection alive
        
        Returns:
            Status dictionary
        """
        response = self._request("GET", "/heartbeat")
        return response
    
    # Signal Management (for MT4/MT5 EA polling)
    
    def get_signal(self, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get pending signal for MT4/MT5 EA
        
        Args:
            symbol: Optional symbol filter
        
        Returns:
            Signal dictionary or None if no signal
        """
        endpoint = "/mt4_signal" if self.platform == "MT4" else "/mt5_signal"
        params = {}
        if symbol:
            params["symbol"] = symbol
        
        response = self._request("GET", endpoint, params=params)
        
        if response.get("status") == "no_signal":
            return None
        
        return response
    
    def enqueue_signal(
        self,
        symbol: str,
        action: str,  # "buy", "sell", "close", "partial_close", "trail"
        quantity: float = 1.0,  # Lot size
        percentage_tp: Optional[float] = None,
        percentage_sl: Optional[float] = None,
        price: Optional[float] = None,
        tp1: Optional[float] = None,
        tp2: Optional[float] = None,
        tp3: Optional[float] = None,
        tp4: Optional[float] = None,
        tp5: Optional[float] = None,
        sl: Optional[float] = None,
        data: str = "",  # Passthrough data field
        multiple_accounts: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Enqueue a trading signal (webhook endpoint)
        
        Aligned with TruForex backend contract:
        - Endpoint: POST /webhook
        - Auth: X-API-Key header or api_key in body
        - Actions: buy, sell, close, partial_close, trail
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            action: "buy", "sell", "close", "partial_close", or "trail"
            quantity: Lot size (default: 1.0)
            percentage_tp: Take profit percentage
            percentage_sl: Stop loss percentage
            price: Entry price (optional, passthrough)
            tp1-tp5: Take profit levels 1-5
            sl: Stop loss price
            data: Passthrough data string
            multiple_accounts: List of account configs (optional)
        
        Returns:
            Signal queued confirmation with status, user, symbol, action
        """
        signal_data = {
            "symbol": symbol,
            "action": action.lower(),
            "quantity": float(quantity),
            "percentage_tp": float(percentage_tp) if percentage_tp else 0.0,
            "percentage_sl": float(percentage_sl) if percentage_sl else 0.0,
            "data": data
        }
        
        if price is not None:
            signal_data["price"] = float(price)
        if tp1 is not None:
            signal_data["tp1"] = float(tp1)
        if tp2 is not None:
            signal_data["tp2"] = float(tp2)
        if tp3 is not None:
            signal_data["tp3"] = float(tp3)
        if tp4 is not None:
            signal_data["tp4"] = float(tp4)
        if tp5 is not None:
            signal_data["tp5"] = float(tp5)
        if sl is not None:
            signal_data["sl"] = float(sl)
        if multiple_accounts:
            signal_data["multiple_accounts"] = multiple_accounts
        
        # API key can be in header (already set) or body
        # Backend checks header first, then body
        response = self._request("POST", "/webhook", data=signal_data)
        return response
    
    def report_execution(
        self,
        symbol: str,
        action: str,
        quantity: float,
        status: str,  # "success", "failed"
        entryPrice: Optional[float] = None,
        stopLoss: Optional[float] = None,
        takeProfit: Optional[float] = None,
        order_id: Optional[str] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Report execution result from MT4/MT5 EA
        
        Aligned with TruForex backend contract:
        - Endpoint: POST /execution_report
        - Auth: X-API-Key header or api_key form field
        - Content-Type: application/x-www-form-urlencoded (form data)
        
        Args:
            symbol: Trading symbol
            action: "buy", "sell", "close", or "partial_close"
            quantity: Lot size
            status: "success" or "failed"
            entryPrice: Entry price (camelCase to match backend)
            stopLoss: Stop loss price (camelCase)
            takeProfit: Take profit price (camelCase)
            order_id: Order ID from MT4/MT5 (order_id field)
            error: Error message if status is "failed"
        
        Returns:
            Execution report confirmation with status and live_open_for_symbol count
        """
        execution_data = {
            "api_key": self.api_key,
            "symbol": symbol,
            "action": action.lower(),
            "quantity": str(float(quantity)),
            "status": status.lower(),
            "entryPrice": str(float(entryPrice)) if entryPrice else "0.0",
            "stopLoss": str(float(stopLoss)) if stopLoss else "0.0",
            "takeProfit": str(float(takeProfit)) if takeProfit else "0.0",
            "order_id": order_id or "",
            "error": error or ""
        }
        
        # Backend expects form data, not JSON
        url = f"{self.base_url}/execution_report"
        response = requests.post(
            url,
            data=execution_data,  # Form data, not json=
            headers={"X-API-Key": self.api_key},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    # Order Management (via signals)
    
    def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        percentage_tp: Optional[float] = None,
        percentage_sl: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place an order (via signal queue)
        
        Args:
            symbol: Trading symbol
            side: "buy" or "sell"
            quantity: Lot size
            order_type: Order type (mostly market orders via EA)
            price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            percentage_tp: Take profit percentage
            percentage_sl: Stop loss percentage
        
        Returns:
            Signal queued confirmation
        """
        return self.enqueue_signal(
            symbol=symbol,
            action=side,
            quantity=quantity,
            percentage_tp=percentage_tp,
            percentage_sl=percentage_sl,
            price=price,
            tp1=take_profit,
            sl=stop_loss
        )
    
    def close_position(
        self,
        symbol: str,
        quantity: Optional[float] = None  # None = full close
    ) -> Dict[str, Any]:
        """
        Close a position (via signal)
        
        Aligned with TruForex backend:
        - action: "close" for full close, "partial_close" for partial
        
        Args:
            symbol: Trading symbol
            quantity: Quantity to close (None = full close, float = partial close)
        
        Returns:
            Close signal confirmation
        """
        # Backend normalizes "close" to "full_close" internally
        # Use "partial_close" action if quantity specified
        if quantity and quantity > 0:
            action = "partial_close"
            qty = float(quantity)
        else:
            action = "close"  # Full close
            qty = 0.0  # Backend interprets 0 as full close
        
        return self.enqueue_signal(
            symbol=symbol,
            action=action,
            quantity=qty
        )
    
    def modify_order(
        self,
        symbol: str,
        order_id: Optional[str] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Modify order (SL/TP modification)
        
        Note: TruForex backend doesn't have a dedicated "modify" action.
        Modifications are typically done via the EA directly or by closing/reopening.
        This method is kept for API compatibility but may not be fully supported.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID (optional)
            stop_loss: New stop loss
            take_profit: New take profit
        
        Returns:
            Modification confirmation (or error if not supported)
        """
        # Backend doesn't have "modify" action - this would need EA support
        # For now, return an error indicating this needs EA implementation
        logger.warning("Modify order not directly supported via TruForex backend - requires EA implementation")
        return {
            "status": "not_supported",
            "message": "Order modification requires MT4/MT5 EA implementation",
            "symbol": symbol
        }
    
    def set_trailing_stop(
        self,
        symbol: str,
        trailing_stop: Optional[float] = None,
        trailing_step: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Set trailing stop for a position
        
        Aligned with TruForex backend:
        - action: "trail"
        - Backend normalizes this action internally
        
        Args:
            symbol: Trading symbol
            trailing_stop: Trailing stop distance (optional, can be in payload)
            trailing_step: Trailing stop step (optional)
        
        Returns:
            Trailing stop confirmation
        """
        signal_data = {
            "symbol": symbol,
            "action": "trail",
            "quantity": 0.0  # Trailing stop doesn't require quantity
        }
        
        # Note: Backend may handle trailing stop differently
        # These fields are passthrough - EA handles the logic
        if trailing_stop is not None:
            signal_data["trailingStop"] = float(trailing_stop)
        if trailing_step is not None:
            signal_data["trailingStep"] = float(trailing_step)
        
        response = self._request("POST", "/webhook", data=signal_data)
        return response
    
    def partial_close(
        self,
        symbol: str,
        quantity: float
    ) -> Dict[str, Any]:
        """
        Partially close a position
        
        Args:
            symbol: Trading symbol
            quantity: Quantity to close
        
        Returns:
            Partial close confirmation
        """
        return self.close_position(symbol, quantity)
    
    # Position Queries (via backend tracking)
    
    def get_open_positions(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get open positions (tracked by backend)
        
        Note: TruForex backend doesn't have a direct positions API endpoint.
        Positions are tracked in backend Redis and database via execution reports.
        Use admin endpoints or database queries for position data.
        
        Args:
            symbol: Optional symbol filter
        
        Returns:
            Empty list (positions not available via API - use admin endpoints)
        """
        # TruForex backend doesn't expose positions via REST API
        # Positions are tracked internally via:
        # 1. Redis sets: pos:{user_id}:{symbol}
        # 2. Database trades table with status='open'
        # 3. Admin endpoints: /admin/trades_json
        
        logger.warning(
            "TruForex positions not available via REST API. "
            "Positions are tracked internally via Redis and database. "
            "Use /admin/trades_json endpoint (requires admin token) or "
            "query database directly."
        )
        return []
    
    # Helper Methods
    
    def calculate_lot_size(self, risk_amount: float, stop_loss_pips: float, pip_value: float = 10.0) -> float:
        """
        Calculate lot size based on risk
        
        Args:
            risk_amount: Amount to risk
            stop_loss_pips: Stop loss in pips
            pip_value: Pip value per lot (default 10 for standard lots)
        
        Returns:
            Lot size
        """
        lot_size = risk_amount / (stop_loss_pips * pip_value)
        return round(lot_size, 2)
