"""
ProjectX/TopStep Broker Executor
Supports both official SDK and custom httpx implementation.

Dual-mode executor:
- SDK mode: Uses official project-x-py SDK (preferred)
- Custom mode: Uses httpx + websockets (fallback)
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.brokers.base_executor import BaseExecutor
from app.core.config import settings
from app.models.pydantic_schemas import (
    OrderRequest, ExecutorOrderResponse as OrderResponse, ExecutorPosition as Position, Account,
    TradeRequest, ExecutorTradeResponse as TradeResponse
)

logger = logging.getLogger(__name__)

# Try to import SDK service
try:
    from app.services.projectx_sdk_service import ProjectXSDKService, SDK_AVAILABLE
except ImportError:
    SDK_AVAILABLE = False
    ProjectXSDKService = None
    logger.warning("project-x-py SDK not available, using httpx fallback")


class ProjectXExecutor(BaseExecutor):
    """
    ProjectX/TopStep trading executor.

    Supports two modes:
    - SDK mode: Uses official project-x-py SDK (preferred)
    - Custom mode: Uses httpx + websockets (fallback)
    """

    def __init__(
        self,
        account_id: Optional[str] = None,
        account_name: Optional[str] = None,
        username: Optional[str] = None,
        api_key: Optional[str] = None,
        use_sdk: bool = True,
    ):
        """
        Initialize ProjectX executor.

        Args:
            account_id: Optional account ID to use
            username: TopStep username (for SDK mode)
            api_key: TopStep API key (for both modes)
            use_sdk: Whether to prefer SDK mode (default True)
        """
        # Get config from settings
        config = settings.get_broker_config("projectx") if hasattr(settings, 'get_broker_config') else {}
        super().__init__(config)

        self.config = config
        self._account_id = account_id
        self._account_name = account_name or account_id

        # Credentials - prefer parameters, then settings
        self._username = username or getattr(settings, 'PROJECT_X_USERNAME', None) or config.get("username")
        self._api_key = api_key or getattr(settings, 'PROJECT_X_API_KEY', None) or config.get("api_token") or config.get("api_key")

        # SDK service (preferred mode)
        self._sdk_service: Optional[Any] = None
        self._use_sdk = use_sdk and SDK_AVAILABLE

        # Fallback httpx client
        self._session = None
        self._ws_connection = None
        self._is_connected = False

        # API URL for httpx fallback
        self._api_url = config.get("api_url", "https://api.topstepx.com")

        # Check for required credentials
        self.is_available = bool(self._api_key and self._username) if self._use_sdk else bool(self._api_key)
        if not self.is_available:
            logger.info("ProjectX executor disabled: credentials not configured")

    @property
    def is_using_sdk(self) -> bool:
        """Check if using official SDK."""
        return self._use_sdk and self._sdk_service is not None and self._sdk_service.is_connected

    async def initialize(self) -> bool:
        """Initialize ProjectX connection."""
        if not self.is_available:
            logger.info("ProjectX skipped: credentials not configured")
            return False

        # Try SDK first
        if self._use_sdk and SDK_AVAILABLE and ProjectXSDKService is not None:
            try:
                self._sdk_service = ProjectXSDKService(
                    username=self._username,
                    api_key=self._api_key,
                    account_name=self._account_name,
                )

                success = await self._sdk_service.connect()
                if success:
                    self._is_connected = True
                    logger.info("ProjectX executor initialized via SDK")
                    return True
                else:
                    logger.warning("SDK connection failed, falling back to httpx")
                    self._sdk_service = None
            except Exception as e:
                logger.warning(f"SDK init failed: {e}, falling back to httpx")
                self._sdk_service = None

        # Fallback to custom httpx implementation
        return await self._initialize_httpx()

    async def _initialize_httpx(self) -> bool:
        """Initialize using custom httpx client (fallback)."""
        try:
            import httpx

            self._session = httpx.AsyncClient(
                base_url=self._api_url,
                timeout=30.0
            )

            # Authenticate via ProjectX Gateway API
            auth_response = await self._session.post(
                "/api/Auth/loginKey",
                json={"userName": self._username, "apiKey": self._api_key},
                headers={"Content-Type": "application/json", "Accept": "text/plain"}
            )

            if auth_response.status_code == 200:
                # Response is typically plain text token or JSON
                content_type = auth_response.headers.get("content-type", "")
                if content_type.startswith("application/json"):
                    token_data = auth_response.json()
                else:
                    token_data = {"token": auth_response.text.strip()}

                token = token_data.get("token") or token_data.get("accessToken")

                if token:
                    self._session.headers.update({"Authorization": f"Bearer {token}"})
                    self._is_connected = True
                    logger.info("ProjectX executor initialized via httpx")
                    return True

            logger.error(f"ProjectX auth failed: {auth_response.text}")
            return False

        except Exception as e:
            logger.error(f"ProjectX httpx initialization failed: {e}")
            return False

    async def disconnect(self):
        """Disconnect from ProjectX."""
        if self._sdk_service:
            await self._sdk_service.disconnect()
            self._sdk_service = None

        if self._ws_connection:
            try:
                await self._ws_connection.close()
            except Exception:
                pass
            self._ws_connection = None

        if self._session:
            await self._session.aclose()
            self._session = None

        self._is_connected = False
        logger.info("ProjectX executor disconnected")

    async def get_accounts(self, limit: int = 5) -> List[Account]:
        """Get all ProjectX accounts (most recent first, limited).

        IMPORTANT: For ProjectX/TopStep, the SDK expects the account 'name'
        (e.g., 'PRAC-V2-95183-68790057') to be used as the primary identifier,
        NOT the numeric 'id'. This name is what gets passed to the SDK for
        authentication and order placement.

        For account discovery (when we don't have a valid account yet),
        this method uses discover_accounts_static which can list accounts
        without requiring a pre-selected account.
        """
        # If SDK is connected and working, use it directly
        if self.is_using_sdk:
            try:
                # Use list_accounts to get all accounts with status
                accounts_data = await self._sdk_service.list_accounts(limit=limit)
                return self._convert_accounts_data(accounts_data)
            except Exception as e:
                logger.error(f"SDK get_accounts failed: {e}")
                # Fall through to discovery mode

        # Try SDK discovery mode (works without pre-selected account)
        if self._use_sdk and SDK_AVAILABLE and ProjectXSDKService is not None:
            try:
                accounts_data = await ProjectXSDKService.discover_accounts_static(
                    username=self._username,
                    api_key=self._api_key
                )
                if accounts_data:
                    logger.info(f"SDK discovery found {len(accounts_data)} accounts")
                    return self._convert_accounts_data(accounts_data[:limit])
            except Exception as e:
                logger.warning(f"SDK discovery failed: {e}, falling back to httpx")

        # Fallback to httpx
        return await self._get_accounts_httpx(limit=limit)

    def _convert_accounts_data(self, accounts_data: List[Dict]) -> List[Account]:
        """Convert account data dicts to Account objects."""
        return [
            Account(
                # Use 'name' as the primary ID - this is what SDK expects!
                # e.g., "PRAC-V2-95183-68790057", "50KTC-V2-95183-95242774"
                id=acc.get("name") or acc.get("id", ""),
                account_number=acc.get("name") or acc.get("id", ""),
                broker="projectx",
                account_type="live" if acc.get("is_live") else "demo",
                currency=acc.get("currency", "USD"),
                balance=float(acc.get("balance", 0)),
                equity=float(acc.get("equity", 0)),
                margin=float(acc.get("margin", 0)),
                free_margin=float(acc.get("free_margin", 0)),
                margin_level=0.0,
                leverage=100,
                is_active=acc.get("is_active", True),
                is_live=acc.get("is_live", False),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                # Pass status and numeric_id in extra_data
                extra_data={
                    "status": acc.get("status", "active"),
                    "numeric_id": acc.get("id", ""),  # Keep numeric ID for reference
                    "name": acc.get("name", ""),
                }
            )
            for acc in accounts_data
        ]

    async def _get_accounts_httpx(self, limit: int = 5) -> List[Account]:
        """Get accounts via httpx (fallback).

        Returns accounts sorted by ID descending (most recent first),
        filtered to only active accounts (positive balance), limited to `limit`.
        """
        try:
            response = await self._session.post("/api/Account/search", json={"onlyActiveAccounts": True})
            if response.status_code == 200:
                data = response.json()
                accounts_data = data if isinstance(data, list) else data.get("accounts", data.get("data", []))

                # Filter to tradeable accounts (canTrade=True) first
                # Use bool() to handle both boolean True and integer 1 from API
                tradeable_accounts = [
                    acc for acc in accounts_data
                    if bool(acc.get("canTrade", False))
                ]

                # Sort by ID descending (most recent first) and limit
                sorted_accounts = sorted(
                    tradeable_accounts,
                    key=lambda x: int(x.get("id", 0)),
                    reverse=True  # Highest IDs (newest) first
                )

                active_accounts = sorted_accounts[:limit]

                return [
                    Account(
                        # Use 'name' as primary ID if available (SDK format)
                        # Fall back to 'id' for API responses
                        id=acc.get("name") or str(acc.get("id", "")),
                        account_number=acc.get("name") or str(acc.get("id", "")),
                        broker="projectx",
                        account_type=acc.get("type", "live"),
                        currency=acc.get("currency", "USD"),
                        balance=float(acc.get("balance", 0)),
                        equity=float(acc.get("equity", 0)),
                        margin=float(acc.get("margin", 0)),
                        free_margin=float(acc.get("free_margin", 0)),
                        margin_level=float(acc.get("margin_level", 0)),
                        leverage=acc.get("leverage", 100),
                        is_active=acc.get("is_active", True),
                        is_live=acc.get("type") == "live",
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        extra_data={
                            "numeric_id": str(acc.get("id", "")),
                            "name": acc.get("name", ""),
                        }
                    )
                    for acc in active_accounts
                ]
            return []
        except Exception as e:
            logger.error(f"httpx get_accounts failed: {e}")
            return []

    async def get_positions(self, account_id: Optional[str] = None) -> List[Position]:
        """Get open positions."""
        if self.is_using_sdk:
            try:
                positions_data = await self._sdk_service.get_positions()
                return [
                    Position(
                        id=pos.get("id", ""),
                        broker="projectx",
                        account_id=account_id or "",
                        symbol=pos.get("symbol", ""),
                        side=pos.get("side", "buy"),
                        size=float(pos.get("size", 0)),
                        entry_price=float(pos.get("entry_price", 0)),
                        current_price=float(pos.get("current_price", 0)),
                        unrealized_pnl=float(pos.get("unrealized_pnl", 0)),
                        realized_pnl=0.0,
                        margin=0.0,
                        magic_number=0,
                        comment="",
                        open_time=datetime.now(),
                        close_time=None,
                        is_active=True
                    )
                    for pos in positions_data
                ]
            except Exception as e:
                logger.error(f"SDK get_positions failed: {e}")
                return []

        # Fallback to httpx
        return await self._get_positions_httpx(account_id)

    async def _get_positions_httpx(self, account_id: Optional[str] = None) -> List[Position]:
        """Get positions via httpx (fallback)."""
        try:
            search_data = {}
            if account_id:
                search_data["accountId"] = account_id

            response = await self._session.post("/api/Position/searchOpen", json=search_data)
            if response.status_code == 200:
                data = response.json()
                positions_data = data if isinstance(data, list) else data.get("positions", data.get("data", []))

                return [
                    Position(
                        id=str(pos.get("id", "")),
                        broker="projectx",
                        account_id=str(pos.get("account_id", account_id or "")),
                        symbol=pos.get("symbol", ""),
                        side=pos.get("side", "buy").lower(),
                        size=float(pos.get("size", 0)),
                        entry_price=float(pos.get("entry_price", 0)),
                        current_price=float(pos.get("current_price", pos.get("entry_price", 0))),
                        unrealized_pnl=float(pos.get("unrealized_pnl", 0)),
                        realized_pnl=float(pos.get("realized_pnl", 0)),
                        margin=float(pos.get("margin", 0)),
                        magic_number=pos.get("magic_number", 0),
                        comment=pos.get("comment", ""),
                        open_time=datetime.fromisoformat(pos.get("open_time", datetime.now().isoformat())),
                        close_time=None,
                        is_active=True
                    )
                    for pos in positions_data
                ]
            return []
        except Exception as e:
            logger.error(f"httpx get_positions failed: {e}")
            return []

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order with ProjectX."""
        if self.is_using_sdk:
            return await self._place_order_sdk(order)
        return await self._place_order_httpx(order)

    async def _place_order_sdk(self, order: OrderRequest) -> OrderResponse:
        """Place order via SDK."""
        try:
            # Map order types
            order_type_lower = order.order_type.lower()
            side = "buy" if "buy" in order_type_lower else "sell"
            is_market = "market" in order_type_lower

            # Check for trailing stop (separate order type)
            trailing_stop = getattr(order, 'trailing_stop', None)
            if trailing_stop:
                result = await self._sdk_service.place_trailing_stop_order(
                    instrument=order.symbol,
                    side=side,
                    size=int(order.quantity),
                    trail_price=float(trailing_stop),  # In ticks
                )
            # Use bracket order if SL or TP provided (supports market entry)
            elif order.stop_loss or order.take_profit:
                result = await self._sdk_service.place_bracket_order(
                    instrument=order.symbol,
                    side=side,
                    size=int(order.quantity),
                    entry_price=None if is_market else order.price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                )
            elif is_market:
                result = await self._sdk_service.place_market_order(
                    instrument=order.symbol,
                    side=side,
                    size=int(order.quantity),
                )
            else:
                result = await self._sdk_service.place_limit_order(
                    instrument=order.symbol,
                    side=side,
                    size=int(order.quantity),
                    limit_price=order.price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                )

            return OrderResponse(
                success=result.get("success", False),
                order_id=result.get("order_id", ""),
                broker="projectx",
                status=result.get("status", "submitted"),
                filled_quantity=order.quantity,
                filled_price=order.price,
                commission=0.0,
                timestamp=datetime.now(),
                error=result.get("error"),
            )
        except Exception as e:
            logger.error(f"SDK place_order failed: {e}")
            return OrderResponse(success=False, error=str(e))

    async def _place_order_httpx(self, order: OrderRequest) -> OrderResponse:
        """Place order via httpx (fallback)."""
        try:
            # First, get contract ID for symbol
            contract_response = await self._session.post(
                "/api/Contract/Search",
                json={"symbol": order.symbol}
            )

            if contract_response.status_code != 200:
                return OrderResponse(success=False, error="Failed to find contract")

            contracts = contract_response.json()
            if isinstance(contracts, dict):
                contracts = contracts.get("contracts", contracts.get("data", []))

            if not contracts:
                return OrderResponse(success=False, error=f"Contract not found: {order.symbol}")

            contract_id = contracts[0].get("id") or contracts[0].get("contract_id")

            # Map order type
            order_type_lower = order.order_type.lower()
            side = "buy" if "buy" in order_type_lower else "sell"
            order_type = "market" if "market" in order_type_lower else "limit"

            order_data = {
                "accountId": order.account_id,
                "contractId": contract_id,
                "side": side,
                "type": order_type,
                "size": int(order.quantity),
            }

            if order.price and order_type != "market":
                order_data["price"] = order.price
            if order.stop_loss:
                order_data["stopLoss"] = order.stop_loss
            if order.take_profit:
                order_data["takeProfit"] = order.take_profit

            response = await self._session.post("/api/Order/place", json=order_data)

            if response.status_code == 200:
                result = response.json()
                return OrderResponse(
                    success=True,
                    order_id=str(result.get("id", "")),
                    broker="projectx",
                    status=result.get("status", "submitted"),
                    filled_quantity=order.quantity,
                    filled_price=order.price,
                    commission=result.get("commission", 0),
                    timestamp=datetime.now()
                )

            return OrderResponse(success=False, error=response.text)

        except Exception as e:
            logger.error(f"httpx place_order failed: {e}")
            return OrderResponse(success=False, error=str(e))

    async def close_position(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position."""
        if self.is_using_sdk:
            try:
                # Need instrument context for SDK
                positions = await self._sdk_service.get_positions()
                for pos in positions:
                    if pos.get("id") == position_id or pos.get("contract_id") == position_id:
                        result = await self._sdk_service.close_position(
                            instrument=pos.get("symbol", "MNQ"),
                            position_id=position_id,
                            size=int(quantity) if quantity else None,
                        )

                        return TradeResponse(
                            success=result.get("success", False),
                            trade_id=result.get("trade_id", ""),
                            broker="projectx",
                            symbol=pos.get("symbol", ""),
                            side="sell" if pos.get("side") == "buy" else "buy",
                            quantity=quantity or pos.get("size", 0),
                            price=pos.get("current_price", 0),
                            pnl=pos.get("unrealized_pnl", 0),
                            commission=0.0,
                            timestamp=datetime.now(),
                            error=result.get("error"),
                        )

                return TradeResponse(success=False, error="Position not found")
            except Exception as e:
                logger.error(f"SDK close_position failed: {e}")
                return TradeResponse(success=False, error=str(e))

        # Fallback to httpx
        return await self._close_position_httpx(position_id, quantity)

    async def _close_position_httpx(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position via httpx (fallback)."""
        try:
            close_data = {"contractId": position_id}
            if quantity:
                close_data["size"] = int(quantity)

            # Get account ID
            accounts = await self._get_accounts_httpx()
            if accounts:
                close_data["accountId"] = accounts[0].id

            response = await self._session.post("/api/Position/closeContract", json=close_data)

            if response.status_code == 200:
                result = response.json()
                return TradeResponse(
                    success=True,
                    trade_id=str(result.get("id", "")),
                    broker="projectx",
                    symbol=result.get("symbol", ""),
                    side=result.get("side", ""),
                    quantity=result.get("quantity", 0),
                    price=result.get("price", 0),
                    pnl=result.get("pnl", 0),
                    commission=result.get("commission", 0),
                    timestamp=datetime.now()
                )

            return TradeResponse(success=False, error=response.text)

        except Exception as e:
            logger.error(f"httpx close_position failed: {e}")
            return TradeResponse(success=False, error=str(e))

    async def modify_order(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify existing order."""
        # SDK doesn't have direct modify - using httpx
        try:
            modify_data = {"orderId": order_id}
            if "price" in modifications:
                modify_data["price"] = modifications["price"]
            if "stop_loss" in modifications:
                modify_data["stopLoss"] = modifications["stop_loss"]
            if "take_profit" in modifications:
                modify_data["takeProfit"] = modifications["take_profit"]

            response = await self._session.post("/api/Order/modify", json=modify_data)

            if response.status_code == 200:
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="projectx",
                    status="modified",
                    timestamp=datetime.now()
                )

            return OrderResponse(success=False, error=response.text)

        except Exception as e:
            logger.error(f"modify_order failed: {e}")
            return OrderResponse(success=False, error=str(e))

    async def cancel_order(self, order_id: str) -> OrderResponse:
        """Cancel order."""
        try:
            response = await self._session.post("/api/Order/cancel", json={"orderId": order_id})

            if response.status_code == 200:
                return OrderResponse(
                    success=True,
                    order_id=order_id,
                    broker="projectx",
                    status="cancelled",
                    timestamp=datetime.now()
                )

            return OrderResponse(success=False, error=response.text)

        except Exception as e:
            logger.error(f"cancel_order failed: {e}")
            return OrderResponse(success=False, error=str(e))

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Cancel all orders (optionally filtered by symbol)."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.cancel_all_orders(symbol)
            except Exception as e:
                logger.error(f"SDK cancel_all_orders failed: {e}")
                return {"success": False, "error": str(e)}
        
        # Fallback: get all orders and cancel each
        try:
            orders = await self.get_orders()
            if symbol:
                orders = [o for o in orders if o.get("symbol", "").upper() == symbol.upper()]
            
            results = []
            for order in orders:
                order_id = str(order.get("id", ""))
                if order_id:
                    result = await self.cancel_order(order_id)
                    results.append({"order_id": order_id, "success": result.success})
            
            return {
                "success": True,
                "cancelled_count": len([r for r in results if r["success"]]),
                "total": len(orders),
                "results": results
            }
        except Exception as e:
            logger.error(f"cancel_all_orders failed: {e}")
            return {"success": False, "error": str(e)}

    # Additional methods for compatibility

    async def authenticate(self) -> bool:
        """Authenticate with broker API."""
        return await self.initialize()

    async def connect(self) -> bool:
        """Connect to broker API."""
        return await self.initialize()

    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get pending orders."""
        try:
            if self._session:
                response = await self._session.post("/api/Order/searchOpen", json={})
                if response.status_code == 200:
                    data = response.json()
                    return data if isinstance(data, list) else data.get("orders", data.get("data", []))
            return []
        except Exception as e:
            logger.error(f"get_orders failed: {e}")
            return []

    def _normalize_futures_symbol(self, symbol: str) -> str:
        """
        Normalize futures symbol by stripping month/year codes.

        Examples:
            MGCZ5 -> MGC
            MGCZ25 -> MGC
            MNQ1! -> MNQ
            MESH2026 -> MES
        """
        import re
        s = symbol.upper().strip()

        # Strip TradingView continuous contract suffix (1!, 2!, etc)
        s = re.sub(r'\d!$', '', s)

        # Strip futures month codes with various year formats
        # Month codes: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec
        # Year formats: Z5, Z25, Z2025, Z2026
        s = re.sub(r'[FGHJKMNQUVXZ]\d{1,4}$', '', s)

        return s

    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote for symbol using orderbook (real-time bid/ask)."""
        if self.is_using_sdk:
            # Normalize symbol for ProjectX (strip month/year codes)
            normalized_symbol = self._normalize_futures_symbol(symbol)
            logger.debug(f"get_quote: normalized {symbol} -> {normalized_symbol}")

            try:
                # First try orderbook for real-time bid/ask (most accurate)
                orderbook = await self._sdk_service.get_orderbook(normalized_symbol, depth=1)
                if orderbook:
                    best_bid = orderbook.get("best_bid", 0)
                    best_ask = orderbook.get("best_ask", 0)

                    if best_bid > 0 or best_ask > 0:
                        return {
                            "symbol": symbol,
                            "bid": best_bid,
                            "ask": best_ask,
                            "price": (best_bid + best_ask) / 2 if best_bid and best_ask else best_bid or best_ask,
                            "spread": orderbook.get("spread", 0),
                            "timestamp": datetime.now(),
                        }

                # Fallback to market data (OHLC - less accurate for current price)
                data = await self._sdk_service.get_market_data(normalized_symbol, days=1, interval=1)
                if data:
                    latest = data[-1]
                    close_price = latest.get("close", 0)
                    if close_price > 0:
                        # Estimate spread based on symbol type (futures typically have small spread)
                        spread_estimate = 0.25 if normalized_symbol.upper().startswith(("M", "E", "N", "Y")) else 0.01
                        return {
                            "symbol": symbol,
                            "bid": close_price - spread_estimate / 2,
                            "ask": close_price + spread_estimate / 2,
                            "price": close_price,
                            "timestamp": datetime.now(),
                        }
            except Exception as e:
                logger.error(f"SDK get_quote failed for {symbol} (normalized: {normalized_symbol}): {e}")
        return None

    async def get_account_info(self, account_id: str) -> Optional[Account]:
        """Get specific account information."""
        accounts = await self.get_accounts()
        for acc in accounts:
            if acc.id == account_id:
                return acc
        return accounts[0] if accounts else None

    async def get_symbols(self) -> List[str]:
        """Get available symbols."""
        common_symbols = ["MNQ", "MES", "MYM", "M2K", "MCL", "MGC", "MBT"]

        if self.is_using_sdk:
            try:
                all_symbols = []
                for sym in common_symbols:
                    instruments = await self._sdk_service.search_instruments(sym)
                    all_symbols.extend([inst.get("symbol", sym) for inst in instruments])
                return list(set(all_symbols))
            except Exception as e:
                logger.error(f"SDK get_symbols failed: {e}")

        return common_symbols

    async def modify_position(
        self,
        position_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """Modify position SL/TP."""
        # ProjectX doesn't have direct position modification
        # Would need to place/modify protective orders
        return {"error": "Position modification not directly supported - use orders"}

    def is_connected(self) -> bool:
        """Check if connected."""
        if self._sdk_service:
            return self._sdk_service.is_connected
        return self._session is not None and hasattr(self._session, 'is_closed') and not self._session.is_closed

    # =========================================================================
    # Advanced SDK Features
    # =========================================================================

    async def place_bracket_order(
        self,
        instrument: str,
        side: str,
        size: int,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> OrderResponse:
        """Place bracket order (OCO) with stop loss and take profit."""
        if self.is_using_sdk:
            try:
                result = await self._sdk_service.place_bracket_order(
                    instrument=instrument,
                    side=side,
                    size=size,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
                return OrderResponse(
                    success=result.get("success", False),
                    order_id=result.get("order_id", ""),
                    broker="projectx",
                    status=result.get("status", "submitted"),
                    timestamp=datetime.now(),
                    error=result.get("error"),
                )
            except Exception as e:
                logger.error(f"SDK bracket order failed: {e}")
                return OrderResponse(success=False, error=str(e))
        
        # Fallback - not implemented in httpx mode
        return OrderResponse(success=False, error="Bracket orders require SDK mode")

    async def get_orderbook(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """Get Level 2 orderbook (market depth)."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.get_orderbook(symbol, depth=depth)
            except Exception as e:
                logger.error(f"SDK get_orderbook failed: {e}")
                return {}
        return {}

    async def get_portfolio_metrics(self, instruments: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get portfolio metrics across multiple instruments."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.get_portfolio_metrics(instruments)
            except Exception as e:
                logger.error(f"SDK get_portfolio_metrics failed: {e}")
                return {}
        return {}

    async def get_position_analytics(self, symbol: str, position_id: Optional[str] = None) -> Dict[str, Any]:
        """Get detailed position analytics."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.get_position_analytics(symbol, position_id)
            except Exception as e:
                logger.error(f"SDK get_position_analytics failed: {e}")
                return {}
        return {}

    async def get_position_history(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get position history (closed positions)."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.get_position_history(symbol, days=days)
            except Exception as e:
                logger.error(f"SDK get_position_history failed: {e}")
                return []
        return []

    async def get_session_statistics(self, symbol: str, session_type: Optional[str] = None) -> Dict[str, Any]:
        """Get session statistics and analytics."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.get_session_statistics(symbol, session_type)
            except Exception as e:
                logger.error(f"SDK get_session_statistics failed: {e}")
                return {}
        return {}

    async def get_performance_stats(self, symbol: str) -> Dict[str, Any]:
        """Get performance statistics (Sharpe ratio, max drawdown, etc.)."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.get_performance_stats(symbol)
            except Exception as e:
                logger.error(f"SDK get_performance_stats failed: {e}")
                return {}
        return {}

    async def calculate_technical_indicators(
        self,
        symbol: str,
        days: int = 30,
        interval: int = 5,
    ) -> Dict[str, Any]:
        """Calculate technical indicators (RSI, MACD, Bollinger Bands, etc.)."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.calculate_technical_indicators(symbol, days=days, interval=interval)
            except Exception as e:
                logger.error(f"SDK calculate_technical_indicators failed: {e}")
                return {}
        return {}

    async def get_risk_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get risk analysis for positions."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.get_risk_analysis(symbol)
            except Exception as e:
                logger.error(f"SDK get_risk_analysis failed: {e}")
                return {}
        return {}

    async def calculate_position_size(
        self,
        symbol: str,
        risk_amount: float,
        stop_loss_price: float,
        entry_price: float,
    ) -> Dict[str, Any]:
        """Calculate optimal position size based on risk."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.calculate_position_size(
                    symbol, risk_amount, stop_loss_price, entry_price
                )
            except Exception as e:
                logger.error(f"SDK calculate_position_size failed: {e}")
                return {}
        return {}

    async def subscribe_realtime_data(self, symbol: str, callback: Optional[callable] = None) -> Dict[str, Any]:
        """Subscribe to real-time market data."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.subscribe_realtime_data(symbol, callback)
            except Exception as e:
                logger.error(f"SDK subscribe_realtime_data failed: {e}")
                return {"success": False, "error": str(e)}
        return {"success": False, "error": "Real-time data requires SDK mode"}

    async def close_all_positions(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Close all open positions (optionally filtered by symbol).

        Args:
            symbol: Optional symbol to filter positions

        Returns:
            Dict with success status, closed count, and results
        """
        if self.is_using_sdk:
            try:
                return await self._sdk_service.close_all_positions(symbol)
            except Exception as e:
                logger.error(f"SDK close_all_positions failed: {e}")
                return {"success": False, "error": str(e)}

        # Fallback to httpx - get all positions and close each
        try:
            positions = await self._get_positions_httpx()
            if symbol:
                positions = [p for p in positions if symbol.upper() in p.symbol.upper()]

            results = []
            for pos in positions:
                result = await self._close_position_httpx(str(pos.id))
                results.append({
                    "position_id": str(pos.id),
                    "symbol": pos.symbol,
                    "success": result.success,
                    "trade_id": result.trade_id if result.success else "",
                    "error": result.error if not result.success else None,
                })

            closed_count = sum(1 for r in results if r["success"])
            return {
                "success": closed_count > 0 or len(results) == 0,
                "closed_count": closed_count,
                "total": len(results),
                "results": results,
            }
        except Exception as e:
            logger.error(f"close_all_positions failed: {e}")
            return {"success": False, "error": str(e)}

    async def place_stop_order(
        self,
        instrument: str,
        side: str,
        size: int,
        stop_price: float,
    ) -> OrderResponse:
        """
        Place stop order (triggers market order when stop price is reached).

        Args:
            instrument: Instrument symbol
            side: "buy" or "sell"
            size: Number of contracts
            stop_price: Stop trigger price

        Returns:
            OrderResponse with order details
        """
        if self.is_using_sdk:
            try:
                result = await self._sdk_service.place_stop_order(
                    instrument=instrument,
                    side=side,
                    size=size,
                    stop_price=stop_price,
                )
                return OrderResponse(
                    success=result.get("success", False),
                    order_id=result.get("order_id", ""),
                    broker="projectx",
                    status=result.get("status", "submitted"),
                    timestamp=datetime.now(),
                    error=result.get("error"),
                )
            except Exception as e:
                logger.error(f"SDK place_stop_order failed: {e}")
                return OrderResponse(success=False, error=str(e))

        # Fallback to httpx
        try:
            # Get contract ID for symbol
            contract_response = await self._session.post(
                "/api/Contract/Search",
                json={"symbol": instrument}
            )

            if contract_response.status_code != 200:
                return OrderResponse(success=False, error="Failed to find contract")

            contracts = contract_response.json()
            if isinstance(contracts, dict):
                contracts = contracts.get("contracts", contracts.get("data", []))

            if not contracts:
                return OrderResponse(success=False, error=f"Contract not found: {instrument}")

            contract_id = contracts[0].get("id") or contracts[0].get("contract_id")

            order_data = {
                "contractId": contract_id,
                "side": side,
                "type": "stop",
                "size": int(size),
                "stopPrice": stop_price,
            }

            response = await self._session.post("/api/Order/place", json=order_data)

            if response.status_code == 200:
                result = response.json()
                return OrderResponse(
                    success=True,
                    order_id=str(result.get("id", "")),
                    broker="projectx",
                    status=result.get("status", "submitted"),
                    timestamp=datetime.now(),
                )

            return OrderResponse(success=False, error=response.text)
        except Exception as e:
            logger.error(f"httpx place_stop_order failed: {e}")
            return OrderResponse(success=False, error=str(e))
