"""
MT5 Broker Executor
Supports both official MetaAPI SDK and custom httpx implementation.

Dual-mode executor:
- SDK mode: Uses official metaapi-cloud-sdk (preferred)
- Custom mode: Uses httpx to Manager API (fallback)
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
from app.brokers.base_executor import BaseExecutor
from app.core.config import settings
from app.models.pydantic_schemas import (
    OrderRequest, ExecutorOrderResponse as OrderResponse, ExecutorPosition as Position, Account,
    TradeRequest, ExecutorTradeResponse as TradeResponse
)
from app.utils.broker_field_limits import truncate_comment

logger = logging.getLogger(__name__)

# Try to import SDK service
try:
    from app.services.metaapi_sdk_service import MetaAPISDKService, SDK_AVAILABLE
except ImportError:
    SDK_AVAILABLE = False
    MetaAPISDKService = None
    logger.warning("metaapi-cloud-sdk not available, using httpx fallback for MT5")


class MT5Executor(BaseExecutor):
    """
    MT5 trading executor.

    Supports two modes:
    - SDK mode: Uses official metaapi-cloud-sdk (preferred)
    - Custom mode: Uses httpx + Manager API (fallback)
    """

    def __init__(
        self,
        metaapi_token: Optional[str] = None,
        metaapi_account_id: Optional[str] = None,
        use_sdk: bool = True,
    ):
        """
        Initialize MT5 executor.

        Args:
            metaapi_token: MetaAPI token (for SDK mode)
            metaapi_account_id: MetaAPI account ID (for SDK mode)
            use_sdk: Whether to prefer SDK mode (default True)
        """
        config = settings.get_broker_config("mt5")
        super().__init__(config)
        self.config = config
        self.api_url = self.config.get("api_url")
        self.manager_host = self.config.get("manager_host")
        self.manager_port = self.config.get("manager_port")
        self.manager_login = self.config.get("manager_login")
        self.manager_password = self.config.get("manager_password")
        self.session = None

        # MetaAPI SDK credentials - prefer parameters, then config
        self._metaapi_token = metaapi_token or self.config.get("metaapi_token")
        self._metaapi_account_id = metaapi_account_id or self.config.get("metaapi_account_id")
        self._metaapi_application = self.config.get("metaapi_application", "tradeflow")

        # SDK service (preferred mode)
        self._sdk_service: Optional[Any] = None
        self._use_sdk = use_sdk and SDK_AVAILABLE

        # REST API mode (most reliable, no WebSocket issues)
        self._using_rest_api = False
        self._rest_client: Optional[httpx.AsyncClient] = None
        # MetaAPI REST API base URLs - use metaapi.cloud which resolves reliably
        self._metaapi_provisioning_api = "https://mt-provisioning-api-v1.agiliumtrade.ai"
        self._metaapi_client_api = "https://mt-client-api-v1.agiliumtrade.ai"
        self._account_region: Optional[str] = None

        # Check for required credentials (either SDK or Manager API)
        has_sdk_credentials = bool(self._metaapi_token and self._metaapi_account_id)
        has_manager_credentials = bool(self.manager_login and self.manager_password)
        self.is_available = has_sdk_credentials or has_manager_credentials

        if not self.is_available:
            logger.info("MT5 executor disabled: no credentials configured (MetaAPI or Manager API)")

    @property
    def is_using_sdk(self) -> bool:
        """Check if using official MetaAPI SDK."""
        return self._use_sdk and self._sdk_service is not None and self._sdk_service.is_connected

    @property
    def is_using_rest_api(self) -> bool:
        """Check if using MetaAPI REST API mode."""
        return self._using_rest_api and self._rest_client is not None

    def _has_metaapi_credentials(self) -> bool:
        """Check if MetaAPI credentials are available."""
        return bool(self._metaapi_token and self._metaapi_account_id)

    async def _initialize_metaapi_rest(self) -> bool:
        """Initialize MetaAPI REST API mode (bypasses WebSocket issues)."""
        if not self._has_metaapi_credentials():
            return False

        try:
            self._rest_client = httpx.AsyncClient(
                timeout=30.0,
                verify=False,  # Disable SSL verification for MetaAPI endpoints
                headers={
                    "auth-token": self._metaapi_token,
                    "Content-Type": "application/json"
                }
            )

            # Try multiple API endpoints to find one that resolves
            # MetaAPI has region-specific domains - use agiliumtrade.agiliumtrade.ai pattern which works
            provisioning_urls = [
                f"https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts/{self._metaapi_account_id}",
                f"https://metaapi.cloud/users/current/accounts/{self._metaapi_account_id}",
                f"https://mt-provisioning-api-v1.london.agiliumtrade.agiliumtrade.ai/users/current/accounts/{self._metaapi_account_id}",
                f"https://mt-provisioning-api-v1.new-york.agiliumtrade.agiliumtrade.ai/users/current/accounts/{self._metaapi_account_id}",
            ]

            account_data = None
            working_provisioning_url = None

            for url in provisioning_urls:
                try:
                    logger.info(f"MetaAPI REST: Trying {url}")
                    response = await self._rest_client.get(url, timeout=3.0)  # Short timeout, fail fast
                    if response.status_code == 200:
                        account_data = response.json()
                        working_provisioning_url = url.rsplit('/users', 1)[0]
                        logger.info(f"MetaAPI REST: Success with {working_provisioning_url}")
                        break
                    elif response.status_code == 401:
                        logger.error("MetaAPI REST: Invalid token (401 Unauthorized)")
                        return False
                    elif response.status_code == 404:
                        logger.warning(f"MetaAPI REST: Account not found at {url}")
                except Exception as e:
                    logger.warning(f"MetaAPI REST: Failed to reach {url}: {e}")
                    continue

            if not account_data:
                logger.error("MetaAPI REST: Could not reach any API endpoint")
                return False

            state = account_data.get("state", "UNKNOWN")
            region = account_data.get("region", "london")
            self._account_region = region
            logger.info(f"MetaAPI REST: Account {self._metaapi_account_id} state={state}, region={region}")

            # Update client API URL based on detected region
            # Use metaapi.cloud for client API (more reliable with SSL)
            self._metaapi_client_api = f"https://mt-client-api-v1.{region}.agiliumtrade.ai"
            self._metaapi_provisioning_api = working_provisioning_url or f"https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai"
            logger.info(f"MetaAPI REST: Using client API: {self._metaapi_client_api}")

            if state != "DEPLOYED":
                # Try to deploy the account
                deploy_url = f"{self._metaapi_provisioning_api}/users/current/accounts/{self._metaapi_account_id}/deploy"
                try:
                    deploy_response = await self._rest_client.post(deploy_url)
                    if deploy_response.status_code in (200, 204):
                        logger.info("MetaAPI REST: Account deployment initiated")
                        # Wait a bit for deployment
                        await asyncio.sleep(2)
                except Exception as e:
                    logger.warning(f"MetaAPI REST: Deploy request failed: {e}")

            self._using_rest_api = True
            return True

        except Exception as e:
            logger.error(f"MetaAPI REST API initialization error: {e}")
            if self._rest_client:
                await self._rest_client.aclose()
                self._rest_client = None
            return False

    async def _place_order_rest(self, order: OrderRequest) -> OrderResponse:
        """Place order via MetaAPI REST API."""
        if not self._rest_client:
            return OrderResponse(success=False, error="REST client not initialized")

        try:
            # Determine action type from order_type field
            # order_type can be: 'buy', 'sell', 'buy_limit', 'sell_limit', 'buy_stop', 'sell_stop', 'market'
            order_type_str = str(order.order_type).lower()
            if "buy" in order_type_str:
                action_type = "ORDER_TYPE_BUY"
            elif "sell" in order_type_str:
                action_type = "ORDER_TYPE_SELL"
            else:
                # Default to buy for 'market' type
                action_type = "ORDER_TYPE_BUY"

            # Build trade request
            trade_data = {
                "actionType": action_type,
                "symbol": order.symbol,
                "volume": float(order.quantity),
            }

            # Add optional fields
            if order.comment:
                trade_data["comment"] = truncate_comment(order.comment, "mt5")

            if order.stop_loss:
                trade_data["stopLoss"] = float(order.stop_loss)

            if order.take_profit:
                trade_data["takeProfit"] = float(order.take_profit)

            # Handle trailing stop - MetaAPI uses trailingStopLoss object
            # with distance (pips) and units (RELATIVE_PIPS is most common)
            trailing_stop = getattr(order, 'trailing_stop', None)
            if trailing_stop:
                trade_data["trailingStopLoss"] = {
                    "distance": {
                        "distance": float(trailing_stop),
                        "units": "RELATIVE_PIPS"  # Trailing distance in pips
                    }
                }
                logger.info(f"MT5: Using trailing stop with distance {trailing_stop} pips")

            # Execute trade via REST API using region-specific URL
            url = f"{self._metaapi_client_api}/users/current/accounts/{self._metaapi_account_id}/trade"
            logger.info(f"MetaAPI REST: Placing order via {url} with data: {trade_data}")
            response = await self._rest_client.post(url, json=trade_data)
            logger.info(f"MetaAPI REST: Order response: {response.status_code} - {response.text[:500] if response.text else 'empty'}")

            if response.status_code in (200, 201):
                result = response.json()
                # MetaAPI returns 200 even for errors - check stringCode/numericCode
                # Success: numericCode=10009, stringCode="TRADE_RETCODE_DONE"
                # Errors: numericCode=4301 (unknown symbol), etc.
                string_code = result.get("stringCode", "")
                numeric_code = result.get("numericCode", 0)

                if string_code == "TRADE_RETCODE_DONE" or numeric_code == 10009:
                    return OrderResponse(
                        success=True,
                        order_id=str(result.get("orderId", result.get("positionId", ""))),
                        broker_order_id=str(result.get("orderId", "")),
                        filled_quantity=float(order.quantity),
                        status="filled",
                        message=string_code
                    )
                else:
                    # MetaAPI returned an error in the response body
                    error_msg = result.get("message", f"MetaAPI error: {string_code} ({numeric_code})")
                    return OrderResponse(success=False, error=error_msg)
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_data.get("error", response.text))
                except:
                    pass
                return OrderResponse(success=False, error=f"REST API error: {error_msg}")

        except Exception as e:
            logger.error(f"MetaAPI REST order error: {e}")
            return OrderResponse(success=False, error=str(e))

    async def initialize(self) -> bool:
        """Initialize MT5 connection."""
        if not self.is_available:
            logger.info("MT5 skipped: credentials not configured")
            return False

        # First try direct REST API (most reliable, no WebSocket issues)
        if self._has_metaapi_credentials():
            try:
                success = await self._initialize_metaapi_rest()
                if success:
                    logger.info("MT5 initialized via MetaAPI REST API")
                    self._is_connected = True
                    return True
            except Exception as e:
                logger.warning(f"MetaAPI REST API initialization failed: {e}")

        # Try SDK if enabled and credentials available (may have WebSocket issues)
        if self._use_sdk and SDK_AVAILABLE and self._has_metaapi_credentials() and MetaAPISDKService is not None:
            try:
                self._sdk_service = MetaAPISDKService(
                    token=self._metaapi_token,
                    account_id=self._metaapi_account_id,
                    application=self._metaapi_application,
                )

                success = await self._sdk_service.connect()
                if success:
                    self._is_connected = True
                    logger.info("MT5 executor initialized via MetaAPI SDK")
                    return True
                else:
                    logger.warning("MetaAPI SDK connection failed, falling back to httpx")
                    self._sdk_service = None
            except ImportError as e:
                logger.error(f"MetaAPI SDK not installed: {e}. Install with: pip install metaapi-cloud-sdk")
                self._sdk_service = None
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    logger.error(f"MetaAPI authentication failed: Invalid METAAPI_TOKEN. Get token from https://app.metaapi.cloud/token")
                elif "404" in error_msg or "not found" in error_msg.lower():
                    logger.error(f"MetaAPI account not found: METAAPI_ACCOUNT_ID={self._metaapi_account_id}. Check account ID in MetaAPI dashboard")
                elif "network" in error_msg.lower() or "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                    logger.error(f"MetaAPI network error: {error_msg}. Check internet connection and retry")
                else:
                    logger.warning(f"MetaAPI SDK init failed: {e}, falling back to httpx")
                self._sdk_service = None

        # Fallback to custom httpx implementation (Manager API)
        return await self._initialize_httpx()

    async def _initialize_httpx(self) -> bool:
        """Initialize using custom httpx client (fallback to Manager API)."""
        if not (self.manager_login and self.manager_password):
            # INFO not ERROR - this is expected for multi-user platform (credentials come from database per-user)
            logger.info("MT5 Manager API: no global credentials (per-user credentials used at runtime)")
            return False

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
                self._is_connected = True
                logger.info("MT5 executor initialized via httpx (Manager API)")
                return True
            else:
                logger.error(f"MT5 auth failed: {response.text}")
                return False

        except Exception as e:
            # INFO level: Multi-user platform uses per-user credentials from database
            logger.info(f"MT5 initialization skipped (credentials from database): {e}")
            return False

    async def disconnect(self):
        """Disconnect from MT5"""
        if self._sdk_service:
            await self._sdk_service.disconnect()
            self._sdk_service = None

        if self.session:
            await self.session.aclose()
            self.session = None

        self._is_connected = False
        logger.info("MT5 executor disconnected")

    async def get_accounts(self) -> List[Account]:
        """Get all MT5 accounts."""
        # Try REST API first (most reliable)
        if self.is_using_rest_api:
            return await self._get_accounts_rest()
        if self.is_using_sdk:
            return await self._get_accounts_sdk()
        return await self._get_accounts_httpx()

    async def _get_accounts_rest(self) -> List[Account]:
        """Get account info via MetaAPI REST API."""
        logger.info(f"_get_accounts_rest called, rest_client={self._rest_client is not None}, account_id={self._metaapi_account_id}")
        if not self._rest_client:
            logger.warning("_get_accounts_rest: no REST client available")
            return []

        try:
            # Per MetaAPI docs: GET /users/current/accounts/:accountId/account-information
            url = f"{self._metaapi_client_api}/users/current/accounts/{self._metaapi_account_id}/account-information"
            logger.info(f"_get_accounts_rest: fetching from {url}")
            response = await self._rest_client.get(url, timeout=15.0)

            if response.status_code == 200:
                info = response.json()
                logger.info(f"_get_accounts_rest SUCCESS: balance={info.get('balance')}, equity={info.get('equity')}, margin={info.get('margin')}, freeMargin={info.get('freeMargin')}")
                return [Account(
                    id=str(info.get("login", self._metaapi_account_id)),
                    broker="mt5",
                    account_type="demo" if info.get("type", "").upper() == "DEMO" else "live",
                    currency=info.get("currency", "USD"),
                    balance=float(info.get("balance", 0)),
                    equity=float(info.get("equity", 0)),
                    margin=float(info.get("margin", 0)),
                    free_margin=float(info.get("freeMargin", 0)),
                    margin_level=float(info.get("marginLevel", 0) or 0),
                    leverage=int(info.get("leverage", 100)),
                    is_active=True,
                    is_live=info.get("type", "").upper() != "DEMO",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )]
            else:
                logger.warning(f"MetaAPI REST get_accounts failed: {response.status_code} - {response.text[:200]}")
                return []
        except Exception as e:
            logger.error(f"Error getting MT5 accounts via REST: {e}")
            return []

    async def _get_accounts_sdk(self) -> List[Account]:
        """Get accounts via MetaAPI SDK."""
        try:
            info = await self._sdk_service.get_account_info()
            return [Account(
                id=info.get("login", self._metaapi_account_id),
                broker="mt5",
                account_type="live" if info.get("trade_allowed", True) else "demo",
                currency=info.get("currency", "USD"),
                balance=float(info.get("balance", 0)),
                equity=float(info.get("equity", 0)),
                margin=float(info.get("margin", 0)),
                free_margin=float(info.get("free_margin", 0)),
                margin_level=float(info.get("margin_level", 0)),
                leverage=int(info.get("leverage", 100)),
                is_active=True,
                is_live=True,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )]
        except Exception as e:
            logger.error(f"SDK get_accounts failed: {e}")
            return []

    async def _get_accounts_httpx(self) -> List[Account]:
        """Get accounts via httpx (Manager API fallback)."""
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
        """Get open positions from MT5."""
        # Try REST API first (most reliable)
        if self.is_using_rest_api:
            return await self._get_positions_rest(account_id)
        if self.is_using_sdk:
            return await self._get_positions_sdk(account_id)
        return await self._get_positions_httpx(account_id)

    async def _get_positions_rest(self, account_id: Optional[str] = None) -> List[Position]:
        """Get positions via MetaAPI REST API."""
        if not self._rest_client:
            return []

        try:
            # Per MetaAPI docs: GET /users/current/accounts/:accountId/positions
            url = f"{self._metaapi_client_api}/users/current/accounts/{self._metaapi_account_id}/positions"
            response = await self._rest_client.get(url, timeout=15.0)

            if response.status_code == 200:
                positions_data = response.json()
                positions = []
                for pos in positions_data:
                    position = Position(
                        id=str(pos.get("id", "")),
                        broker="mt5",
                        account_id=account_id or self._metaapi_account_id or "",
                        symbol=pos.get("symbol", ""),
                        side="buy" if pos.get("type", "").upper() in ("POSITION_TYPE_BUY", "BUY") else "sell",
                        size=float(pos.get("volume", 0)),
                        entry_price=float(pos.get("openPrice", 0)),
                        current_price=float(pos.get("currentPrice", pos.get("openPrice", 0))),
                        unrealized_pnl=float(pos.get("profit", pos.get("unrealizedProfit", 0))),
                        realized_pnl=0.0,
                        margin=float(pos.get("margin", 0)),
                        magic_number=pos.get("magic", 0),
                        comment=pos.get("comment", ""),
                        open_time=self._parse_sdk_datetime(pos.get("time", pos.get("openTime", ""))),
                        close_time=None,
                        is_active=True
                    )
                    positions.append(position)
                return positions
            else:
                logger.warning(f"MetaAPI REST get_positions failed: {response.status_code} - {response.text[:200]}")
                return []
        except Exception as e:
            logger.error(f"Error getting MT5 positions via REST: {e}")
            return []

    def _parse_sdk_datetime(self, time_str: Optional[str]) -> datetime:
        """Parse MetaAPI datetime string to datetime object."""
        if not time_str:
            return datetime.now()
        try:
            # MetaAPI returns ISO format or timestamp
            if isinstance(time_str, (int, float)):
                return datetime.fromtimestamp(time_str)
            # Try ISO format
            if 'T' in str(time_str) or 'Z' in str(time_str):
                time_str_clean = str(time_str).replace('Z', '+00:00')
                return datetime.fromisoformat(time_str_clean)
            # Try parsing as timestamp string
            try:
                return datetime.fromtimestamp(float(time_str))
            except (ValueError, TypeError):
                pass
            # Fallback to now
            return datetime.now()
        except Exception:
            return datetime.now()

    async def _get_positions_sdk(self, account_id: Optional[str] = None) -> List[Position]:
        """Get positions via MetaAPI SDK."""
        try:
            positions_data = await self._sdk_service.get_positions()
            return [
                Position(
                    id=pos.get("id", ""),
                    broker="mt5",
                    account_id=account_id or self._metaapi_account_id or "",
                    symbol=pos.get("symbol", ""),
                    side=pos.get("side", "buy"),
                    size=float(pos.get("volume", 0)),
                    entry_price=float(pos.get("open_price", 0)),
                    current_price=float(pos.get("current_price", 0)),
                    unrealized_pnl=float(pos.get("unrealized_pnl", pos.get("profit", 0))),
                    realized_pnl=0.0,
                    margin=0.0,
                    magic_number=pos.get("magic", 0),
                    comment=pos.get("comment", ""),
                    open_time=self._parse_sdk_datetime(pos.get("time", pos.get("open_time", ""))),
                    close_time=None,
                    is_active=True
                )
                for pos in positions_data
            ]
        except Exception as e:
            logger.error(f"SDK get_positions failed: {e}")
            return []

    async def _get_positions_httpx(self, account_id: Optional[str] = None) -> List[Position]:
        """Get positions via httpx (Manager API fallback)."""
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
        """Place order with MT5."""
        # Try REST API first (most reliable)
        if self.is_using_rest_api:
            return await self._place_order_rest(order)

        # Try SDK mode
        if self.is_using_sdk:
            return await self._place_order_sdk(order)

        # Check if httpx session is available before trying httpx mode
        if self.session is None:
            # If MetaAPI credentials exist but neither REST nor SDK worked, give helpful error
            if self._has_metaapi_credentials():
                return OrderResponse(
                    success=False,
                    error="MetaAPI connection failed. Please check your MetaAPI account status."
                )
            return OrderResponse(
                success=False,
                error="MT5 executor not initialized - no valid credentials"
            )
        return await self._place_order_httpx(order)

    async def _place_order_sdk(self, order: OrderRequest) -> OrderResponse:
        """Place order via MetaAPI SDK."""
        try:
            order_type_lower = order.order_type.lower()

            # Determine order method based on type
            if order_type_lower == "market_buy":
                result = await self._sdk_service.create_market_buy_order(
                    symbol=order.symbol,
                    volume=order.quantity,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    comment=order.comment,
                    magic=order.magic_number,
                )
            elif order_type_lower == "market_sell":
                result = await self._sdk_service.create_market_sell_order(
                    symbol=order.symbol,
                    volume=order.quantity,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    comment=order.comment,
                    magic=order.magic_number,
                )
            elif order_type_lower == "buy_limit":
                result = await self._sdk_service.create_limit_buy_order(
                    symbol=order.symbol,
                    volume=order.quantity,
                    open_price=order.price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    comment=order.comment,
                    magic=order.magic_number,
                )
            elif order_type_lower == "sell_limit":
                result = await self._sdk_service.create_limit_sell_order(
                    symbol=order.symbol,
                    volume=order.quantity,
                    open_price=order.price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    comment=order.comment,
                    magic=order.magic_number,
                )
            elif order_type_lower == "buy_stop":
                result = await self._sdk_service.create_stop_buy_order(
                    symbol=order.symbol,
                    volume=order.quantity,
                    open_price=order.price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    comment=order.comment,
                    magic=order.magic_number,
                )
            elif order_type_lower == "sell_stop":
                result = await self._sdk_service.create_stop_sell_order(
                    symbol=order.symbol,
                    volume=order.quantity,
                    open_price=order.price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    comment=order.comment,
                    magic=order.magic_number,
                )
            elif order_type_lower == "buy_stop_limit":
                # MT5 supports stop-limit orders
                result = await self._sdk_service.create_stop_limit_buy_order(
                    symbol=order.symbol,
                    volume=order.quantity,
                    open_price=order.price,
                    stop_limit_price=order.price,  # Same as open price for basic usage
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    comment=order.comment,
                    magic=order.magic_number,
                )
            elif order_type_lower == "sell_stop_limit":
                result = await self._sdk_service.create_stop_limit_sell_order(
                    symbol=order.symbol,
                    volume=order.quantity,
                    open_price=order.price,
                    stop_limit_price=order.price,
                    stop_loss=order.stop_loss,
                    take_profit=order.take_profit,
                    comment=order.comment,
                    magic=order.magic_number,
                )
            else:
                return OrderResponse(
                    success=False,
                    error=f"Unsupported order type: {order.order_type}"
                )

            return OrderResponse(
                success=result.get("success", False),
                order_id=result.get("order_id", ""),
                broker="mt5",
                status=result.get("status", "submitted"),
                filled_quantity=order.quantity if result.get("success") else 0,
                filled_price=order.price,
                commission=0.0,
                timestamp=datetime.now(),
                error=result.get("error"),
            )
        except Exception as e:
            logger.error(f"SDK place_order failed: {e}")
            return OrderResponse(success=False, error=str(e))

    async def _place_order_httpx(self, order: OrderRequest) -> OrderResponse:
        """Place order via httpx (Manager API fallback)."""
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
                "comment": truncate_comment(order.comment, "mt5") or "",
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
        """Modify existing order in MT5."""
        if self.is_using_sdk:
            return await self._modify_order_sdk(order_id, modifications)
        return await self._modify_order_httpx(order_id, modifications)

    async def _modify_order_sdk(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify order via MetaAPI SDK."""
        try:
            result = await self._sdk_service.modify_order(
                order_id=order_id,
                open_price=modifications.get("price"),
                stop_loss=modifications.get("stop_loss"),
                take_profit=modifications.get("take_profit"),
                volume=modifications.get("volume"),
            )
            return OrderResponse(
                success=result.get("success", False),
                order_id=order_id,
                broker="mt5",
                status="modified" if result.get("success") else "failed",
                timestamp=datetime.now(),
                error=result.get("error"),
            )
        except Exception as e:
            logger.error(f"SDK modify_order failed: {e}")
            return OrderResponse(success=False, error=str(e))

    async def _modify_order_httpx(self, order_id: str, modifications: Dict[str, Any]) -> OrderResponse:
        """Modify order via httpx (Manager API fallback)."""
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
        """Cancel order in MT5."""
        if self.is_using_sdk:
            return await self._cancel_order_sdk(order_id)
        return await self._cancel_order_httpx(order_id)

    async def _cancel_order_sdk(self, order_id: str) -> OrderResponse:
        """Cancel order via MetaAPI SDK."""
        try:
            result = await self._sdk_service.cancel_order(order_id=order_id)
            return OrderResponse(
                success=result.get("success", False),
                order_id=order_id,
                broker="mt5",
                status="cancelled" if result.get("success") else "failed",
                timestamp=datetime.now(),
                error=result.get("error"),
            )
        except Exception as e:
            logger.error(f"SDK cancel_order failed: {e}")
            return OrderResponse(success=False, error=str(e))

    async def _cancel_order_httpx(self, order_id: str) -> OrderResponse:
        """Cancel order via httpx (Manager API fallback)."""
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
        """Close position in MT5."""
        # Try REST API first (most reliable)
        if self.is_using_rest_api:
            return await self._close_position_rest(position_id, quantity)
        if self.is_using_sdk:
            return await self._close_position_sdk(position_id, quantity)
        return await self._close_position_httpx(position_id, quantity)

    async def _close_position_rest(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position via MetaAPI REST API."""
        if not self._rest_client:
            return TradeResponse(success=False, error="REST client not initialized")

        try:
            # Get position info first
            positions = await self._get_positions_rest()
            position = None
            for pos in positions:
                if str(pos.id) == str(position_id):
                    position = pos
                    break

            if not position:
                return TradeResponse(success=False, error=f"Position {position_id} not found")

            # Close via REST API
            # Use POSITION_PARTIAL for partial close, POSITION_CLOSE_ID for full close
            if quantity and quantity < position.size:
                # Partial close
                trade_data = {
                    "actionType": "POSITION_PARTIAL",
                    "positionId": str(position_id),
                    "volume": float(quantity),
                }
            else:
                # Full close - POSITION_CLOSE_ID doesn't accept volume
                trade_data = {
                    "actionType": "POSITION_CLOSE_ID",
                    "positionId": str(position_id),
                }

            url = f"{self._metaapi_client_api}/users/current/accounts/{self._metaapi_account_id}/trade"
            logger.info(f"MetaAPI REST: Closing position {position_id} with data: {trade_data}")
            response = await self._rest_client.post(url, json=trade_data, timeout=15.0)
            logger.info(f"MetaAPI REST: Close response: {response.status_code} - {response.text[:500] if response.text else 'empty'}")

            if response.status_code in (200, 201):
                result = response.json()
                # MetaAPI returns 200 even for errors - check stringCode/numericCode
                string_code = result.get("stringCode", "")
                numeric_code = result.get("numericCode", 0)

                if string_code == "TRADE_RETCODE_DONE" or numeric_code == 10009:
                    return TradeResponse(
                        success=True,
                        trade_id=str(result.get("orderId", position_id)),
                        broker="mt5",
                        symbol=position.symbol,
                        side="sell" if position.side == "buy" else "buy",
                        quantity=quantity or position.size,
                        price=position.current_price,
                        pnl=position.unrealized_pnl,
                        commission=0.0,
                        timestamp=datetime.now(),
                    )
                else:
                    # MetaAPI returned an error in the response body
                    error_msg = result.get("message", f"MetaAPI error: {string_code} ({numeric_code})")
                    return TradeResponse(success=False, error=error_msg)
            else:
                error_msg = response.text
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_data.get("error", response.text))
                except:
                    pass
                return TradeResponse(success=False, error=f"REST close failed: {error_msg}")
        except Exception as e:
            logger.error(f"REST close_position failed: {e}")
            return TradeResponse(success=False, error=str(e))

    async def _close_position_sdk(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position via MetaAPI SDK."""
        try:
            # Get position info first for response details
            positions = await self._sdk_service.get_positions()
            position = None
            for pos in positions:
                if pos.get("id") == position_id:
                    position = pos
                    break

            result = await self._sdk_service.close_position(
                position_id=position_id,
                volume=quantity,
            )

            if result.get("success"):
                return TradeResponse(
                    success=True,
                    trade_id=result.get("order_id", position_id),
                    broker="mt5",
                    symbol=position.get("symbol", "") if position else "",
                    side="sell" if position and position.get("side") == "buy" else "buy",
                    quantity=quantity or (position.get("volume", 0) if position else 0),
                    price=position.get("current_price", 0) if position else 0,
                    pnl=position.get("unrealized_pnl", 0) if position else 0,
                    commission=0.0,
                    timestamp=datetime.now(),
                )
            else:
                return TradeResponse(
                    success=False,
                    error=result.get("error", "Close position failed"),
                )
        except Exception as e:
            logger.error(f"SDK close_position failed: {e}")
            return TradeResponse(success=False, error=str(e))

    async def _close_position_httpx(self, position_id: str, quantity: Optional[float] = None) -> TradeResponse:
        """Close position via httpx (Manager API fallback)."""
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
                "comment": truncate_comment(f"C_{position_id[:8]}", "mt5") or "",
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
        """Get specific account information."""
        logger.info(f"get_account_info called: is_using_rest_api={self.is_using_rest_api}, is_using_sdk={self.is_using_sdk}")
        # Try REST API first (most reliable)
        if self.is_using_rest_api:
            logger.info("get_account_info: using REST API path")
            accounts = await self._get_accounts_rest()
            return accounts[0] if accounts else None
        if self.is_using_sdk:
            logger.info("get_account_info: using SDK path")
            accounts = await self._get_accounts_sdk()
            return accounts[0] if accounts else None
        logger.info("get_account_info: using httpx fallback path")
        return await self._get_account_info_httpx(account_id)

    async def _get_account_info_httpx(self, account_id: str) -> Optional[Account]:
        """Get account info via httpx (Manager API fallback)."""
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

    async def get_deal_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get deal history (closed trades)."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.get_deal_history(start_time, end_time)
            except Exception as e:
                logger.error(f"SDK get_deal_history failed: {e}")
                return []
        
        # Manager API fallback - not implemented
        return []

    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get pending orders from MT5."""
        if self.is_using_sdk:
            try:
                return await self._sdk_service.get_orders()
            except Exception as e:
                logger.error(f"SDK get_orders failed: {e}")
                return []

        # Fallback to httpx - MT5 Manager API doesn't implement this
        return []

    async def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote for symbol from MT5."""
        # Try REST API first (most reliable)
        if self.is_using_rest_api:
            return await self._get_quote_rest(symbol)

        if self.is_using_sdk:
            return self._sdk_service.get_quote(symbol)

        # Fallback - not implemented in Manager API
        return None

    async def _get_quote_rest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get quote via MetaAPI REST API using current candle data."""
        if not self._rest_client:
            return None

        try:
            # MetaAPI endpoint for current candles (latest price data)
            # Per docs: GET /users/current/accounts/:accountId/symbols/:symbol/current-candles
            url = f"{self._metaapi_client_api}/users/current/accounts/{self._metaapi_account_id}/symbols/{symbol}/current-candles"
            params = {"timeframe": "1m"}  # 1-minute candle for current price

            response = await self._rest_client.get(url, params=params, timeout=10.0)

            if response.status_code == 200:
                candles = response.json()
                if candles and len(candles) > 0:
                    # Get the most recent candle
                    latest = candles[-1] if isinstance(candles, list) else candles
                    close_price = float(latest.get("close", 0))

                    if close_price > 0:
                        # Estimate bid/ask from close price (typical spread)
                        # For forex pairs, spread is typically 0.0001-0.0005
                        # For metals like XAUUSD, spread is typically 0.1-0.5
                        spread_estimate = 0.01 if "XAU" in symbol.upper() or "GOLD" in symbol.upper() else 0.0001

                        return {
                            "symbol": symbol,
                            "bid": close_price - spread_estimate / 2,
                            "ask": close_price + spread_estimate / 2,
                            "price": close_price,
                            "time": latest.get("time", datetime.now().isoformat())
                        }

            # Try alternative endpoint: market-data
            url_alt = f"{self._metaapi_client_api}/users/current/accounts/{self._metaapi_account_id}/symbols/{symbol}/current-price"
            response_alt = await self._rest_client.get(url_alt, timeout=10.0)

            if response_alt.status_code == 200:
                data = response_alt.json()
                bid = float(data.get("bid", 0))
                ask = float(data.get("ask", 0))

                if bid > 0 or ask > 0:
                    return {
                        "symbol": symbol,
                        "bid": bid,
                        "ask": ask,
                        "price": (bid + ask) / 2 if bid and ask else bid or ask,
                        "time": datetime.now().isoformat()
                    }

            logger.warning(f"MetaAPI REST get_quote failed for {symbol}: {response.status_code}")
            return None

        except Exception as e:
            logger.error(f"Error getting quote via REST for {symbol}: {e}")
            return None

    async def modify_position(
        self,
        position_id: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """Modify position in MT5."""
        if self.is_using_sdk:
            try:
                result = await self._sdk_service.modify_position(
                    position_id=position_id,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
                return result
            except Exception as e:
                logger.error(f"SDK modify_position failed: {e}")
                return {"error": str(e)}

        # Fallback - not implemented in Manager API
        return {"error": "Not implemented in Manager API"}

    def is_connected(self) -> bool:
        """Check if broker is connected."""
        if self._sdk_service:
            return self._sdk_service.is_connected
        return hasattr(self, 'session') and self.session is not None and not self.session.is_closed
