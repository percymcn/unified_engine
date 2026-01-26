"""
Test Connection Use Case

Tests broker connections with provided credentials before saving accounts.
Includes symbol format detection for successful connections.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List

from app.domain.enums import BrokerType
from app.application.dto.account_dto import (
    TestConnectionRequest,
    TestConnectionResponse,
)
from app.domain.services.symbol_format_detector import SymbolFormatDetector

logger = logging.getLogger(__name__)

# Connection test timeout in seconds
CONNECTION_TIMEOUT = 10


class TestConnectionUseCase:
    """
    Use case for testing broker connections before saving account.

    Tests credentials by attempting to authenticate with the broker
    and returns detailed status information. On successful connection,
    also detects symbol format patterns for auto-configuration.
    """

    def __init__(self):
        """Initialize with symbol format detector."""
        self._format_detector = SymbolFormatDetector()

    def _detect_symbols(
        self,
        symbols: List[str]
    ) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]], Optional[List[str]]]:
        """
        Detect symbol format from available symbols.

        Returns:
            Tuple of (detected_format, symbol_map, sample_symbols)
        """
        if not symbols:
            return None, None, None

        try:
            detected_format = self._format_detector.detect_format(symbols)
            symbol_map = self._format_detector.build_symbol_map(symbols, detected_format)
            sample_symbols = symbols[:20]  # First 20 for UI preview

            logger.info(
                f"Detected symbol format: {detected_format.get('suffix', 'none')}, "
                f"mapped {len(symbol_map)} common symbols"
            )

            return detected_format, symbol_map, sample_symbols
        except Exception as e:
            logger.warning(f"Symbol format detection failed: {e}")
            return None, None, symbols[:20] if symbols else None

    async def execute(self, request: TestConnectionRequest) -> TestConnectionResponse:
        """
        Test broker connection with provided credentials.

        Args:
            request: Contains broker type and credentials to test

        Returns:
            TestConnectionResponse with success status and detailed message
        """
        try:
            # Add timeout to connection test
            result = await asyncio.wait_for(
                self._test_broker_connection(request.broker, request.credentials),
                timeout=CONNECTION_TIMEOUT
            )
            return result

        except asyncio.TimeoutError:
            logger.warning(f"Connection test timeout for {request.broker.value}")
            return TestConnectionResponse(
                success=False,
                status="timeout",
                message=f"Connection to {request.broker.value} timed out after {CONNECTION_TIMEOUT} seconds. "
                        "Please check your network connection and try again.",
                details={"timeout_seconds": CONNECTION_TIMEOUT}
            )
        except Exception as e:
            logger.exception(f"Unexpected error testing {request.broker.value} connection: {e}")
            return TestConnectionResponse(
                success=False,
                status="failed",
                message=f"Unexpected error: {str(e)}",
                details={"error_type": type(e).__name__}
            )

    async def _test_broker_connection(
        self,
        broker: BrokerType,
        credentials: dict
    ) -> TestConnectionResponse:
        """Route to broker-specific test method."""
        testers = {
            BrokerType.TRADELOCKER: self._test_tradelocker,
            BrokerType.TRADOVATE: self._test_tradovate,
            BrokerType.PROJECTX: self._test_projectx,
            BrokerType.TOPSTEP: self._test_projectx,  # TopStep uses ProjectX
            BrokerType.MT4: self._test_mt4,
            BrokerType.MT5: self._test_mt5,
        }

        tester = testers.get(broker)
        if not tester:
            return TestConnectionResponse(
                success=False,
                status="failed",
                message=f"Unsupported broker type: {broker.value}",
                details={"supported_brokers": [b.value for b in BrokerType]}
            )

        return await tester(credentials)

    def _normalize_tradelocker_environment(self, environment: str) -> str:
        """
        Normalize TradeLocker environment to ensure it has proper URL scheme.

        Handles common user input patterns:
        - "demo" -> "https://demo.tradelocker.com"
        - "live" -> "https://live.tradelocker.com"
        - "demo.tradelocker.com" -> "https://demo.tradelocker.com"
        - "https://demo.tradelocker.com" -> "https://demo.tradelocker.com" (unchanged)
        """
        if not environment:
            return "https://demo.tradelocker.com"

        environment = environment.strip()

        # Already has scheme - return as-is
        if environment.startswith("http://") or environment.startswith("https://"):
            return environment

        # Common shorthand: "demo" or "live"
        if environment.lower() in ("demo", "live"):
            return f"https://{environment.lower()}.tradelocker.com"

        # Domain without scheme
        if "." in environment:
            return f"https://{environment}"

        # Fallback: assume it's a subdomain of tradelocker.com
        return f"https://{environment}.tradelocker.com"

    async def _test_tradelocker(self, credentials: dict) -> TestConnectionResponse:
        """Test TradeLocker connection."""
        try:
            # Check for required credentials
            username = credentials.get("username")
            password = credentials.get("password")
            server = credentials.get("server")
            api_key = credentials.get("api_key")
            # Accept sdk_environment (new) or environment_url or environment (legacy)
            environment_url = credentials.get("sdk_environment") or credentials.get("environment_url") or credentials.get("environment")

            # Check if broker requires Brand API (e.g., GATESFX)
            requires_brand_api = self._requires_brand_api(server)

            # If Brand API is required but only username/password provided, return clear error
            if requires_brand_api and not api_key and (username or password):
                return TestConnectionResponse(
                    success=False,
                    status="failed",
                    message=f"Broker '{server}' requires Brand API Key mode; username/password authentication is not supported. Please provide an API key.",
                    details={
                        "mode": "brand_api_required",
                        "server": server,
                        "required": ["api_key", "environment_url"],
                        "optional": ["server"]
                    }
                )

            # Brand API mode (api_key) - check first if required or if api_key provided
            if api_key or requires_brand_api:
                if not api_key:
                    return TestConnectionResponse(
                        success=False,
                        status="failed",
                        message=f"Broker '{server}' requires Brand API Key. Please provide an API key.",
                        details={
                            "mode": "brand_api_required",
                            "server": server,
                            "required": ["api_key"]
                        }
                    )

                try:
                    import httpx
                    from app.core.config import settings

                    # Use environment_url if provided, otherwise default API URL
                    if environment_url:
                        # Extract base URL from environment_url if it's a full URL
                        if environment_url.startswith("http"):
                            # For Brand API, we typically use api.tradelocker.com or broker-specific domain
                            # If environment_url is provided, try to construct API URL
                            # Common pattern: https://live.tradelocker.com -> https://api.tradelocker.com
                            # But some brokers may have custom API endpoints
                            api_url = environment_url.replace("live.", "api.").replace("demo.", "api.")
                            if not api_url.startswith("http"):
                                api_url = f"https://{api_url}"
                        else:
                            api_url = f"https://{environment_url}"
                    else:
                        config = settings.get_broker_config("tradelocker")
                        api_url = config.get("api_url", "https://api.tradelocker.com")

                    async with httpx.AsyncClient(
                        base_url=api_url,
                        headers={"brand-api-key": api_key},
                        timeout=10.0
                    ) as client:
                        response = await client.get("/accounts")
                        if response.status_code == 200:
                            # Get symbols for format detection
                            symbols = []
                            try:
                                sym_response = await client.get("/instruments")
                                if sym_response.status_code == 200:
                                    instruments_data = sym_response.json()
                                    symbols = [inst.get("symbol", "") for inst in instruments_data]
                            except Exception as e:
                                logger.warning(f"Failed to get TradeLocker symbols: {e}")

                            # Detect symbol format
                            detected_format, symbol_map, sample_symbols = self._detect_symbols(symbols)

                            return TestConnectionResponse(
                                success=True,
                                status="connected",
                                message="Successfully connected to TradeLocker via Brand API",
                                details={
                                    "mode": "brand_api",
                                    "api_url": api_url,
                                    "server": server
                                },
                                detected_format=detected_format,
                                symbol_map=symbol_map,
                                sample_symbols=sample_symbols,
                            )
                        elif response.status_code == 401:
                            return TestConnectionResponse(
                                success=False,
                                status="failed",
                                message="Invalid TradeLocker API key. Please check your credentials.",
                                details={"mode": "brand_api", "http_status": 401}
                            )
                        else:
                            error_text = response.text[:200] if response.text else ""
                            return TestConnectionResponse(
                                success=False,
                                status="failed",
                                message=f"TradeLocker API error: {response.status_code}. {error_text}",
                                details={"mode": "brand_api", "http_status": response.status_code}
                            )
                except Exception as e:
                    return TestConnectionResponse(
                        success=False,
                        status="failed",
                        message=f"TradeLocker Brand API error: {str(e)}",
                        details={"mode": "brand_api", "error": str(e)}
                    )

            # SDK mode (user credentials) - only if Brand API not required
            if username and password and server:
                try:
                    from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

                    # Normalize environment URL to ensure it has proper scheme
                    # Accept sdk_environment (new) or environment (legacy)
                    raw_environment = credentials.get("sdk_environment") or credentials.get("environment", "https://demo.tradelocker.com")
                    environment = self._normalize_tradelocker_environment(raw_environment)
                    wrapper = TradeLockerSDKWrapper(
                        environment=environment,
                        username=username,
                        password=password,
                        server=server
                    )

                    success = await wrapper.initialize()
                    if success:
                        # Verify accounts are fetchable (required for signal execution)
                        acc_num = wrapper.account_number
                        acc_id = wrapper.account_id

                        if not acc_num and not acc_id:
                            wrapper.shutdown()
                            return TestConnectionResponse(
                                success=False,
                                status="failed",
                                message="TradeLocker SDK connected but no accounts found. Please verify your account has trading permissions.",
                                details={"mode": "sdk", "server": server}
                            )

                        # Get symbols for format detection
                        symbols = []
                        try:
                            instruments = await wrapper.get_all_instruments()
                            if instruments is not None and hasattr(instruments, 'to_dict'):
                                records = instruments.to_dict('records')
                                symbols = [inst.get('name', inst.get('symbol', '')) for inst in records]
                        except Exception as e:
                            logger.warning(f"Failed to get TradeLocker symbols: {e}")

                        wrapper.shutdown()

                        # Detect symbol format
                        detected_format, symbol_map, sample_symbols = self._detect_symbols(symbols)

                        return TestConnectionResponse(
                            success=True,
                            status="connected",
                            message="Successfully connected to TradeLocker via SDK",
                            details={
                                "mode": "sdk",
                                "server": server,
                                "environment": environment,
                                "account_id": str(acc_id) if acc_id else None,
                                "account_number": str(acc_num) if acc_num else None,
                            },
                            detected_format=detected_format,
                            symbol_map=symbol_map,
                            sample_symbols=sample_symbols,
                        )
                    else:
                        return TestConnectionResponse(
                            success=False,
                            status="failed",
                            message="TradeLocker SDK authentication failed. Please verify your username, password, and server.",
                            details={"mode": "sdk"}
                        )
                except ImportError:
                    logger.warning("TradeLocker SDK not available")
                except Exception as e:
                    return TestConnectionResponse(
                        success=False,
                        status="failed",
                        message=f"TradeLocker SDK error: {str(e)}",
                        details={"mode": "sdk", "error": str(e)}
                    )

            # Brand API mode (api_key)
            if api_key:
                try:
                    import httpx
                    from app.core.config import settings

                    config = settings.get_broker_config("tradelocker")
                    api_url = config.get("api_url", "https://api.tradelocker.com")

                    async with httpx.AsyncClient(
                        base_url=api_url,
                        headers={"brand-api-key": api_key},
                        timeout=10.0
                    ) as client:
                        response = await client.get("/accounts")
                        if response.status_code == 200:
                            # Get symbols for format detection
                            symbols = []
                            try:
                                sym_response = await client.get("/instruments")
                                if sym_response.status_code == 200:
                                    instruments_data = sym_response.json()
                                    symbols = [inst.get("symbol", "") for inst in instruments_data]
                            except Exception as e:
                                logger.warning(f"Failed to get TradeLocker symbols: {e}")

                            # Detect symbol format
                            detected_format, symbol_map, sample_symbols = self._detect_symbols(symbols)

                            return TestConnectionResponse(
                                success=True,
                                status="connected",
                                message="Successfully connected to TradeLocker via Brand API",
                                details={"mode": "brand_api"},
                                detected_format=detected_format,
                                symbol_map=symbol_map,
                                sample_symbols=sample_symbols,
                            )
                        elif response.status_code == 401:
                            return TestConnectionResponse(
                                success=False,
                                status="failed",
                                message="Invalid TradeLocker API key. Please check your credentials.",
                                details={"mode": "brand_api", "http_status": 401}
                            )
                        else:
                            return TestConnectionResponse(
                                success=False,
                                status="failed",
                                message=f"TradeLocker API error: {response.status_code}",
                                details={"mode": "brand_api", "http_status": response.status_code}
                            )
                except Exception as e:
                    return TestConnectionResponse(
                        success=False,
                        status="failed",
                        message=f"TradeLocker Brand API error: {str(e)}",
                        details={"mode": "brand_api", "error": str(e)}
                    )

            # Determine required fields based on server
            if requires_brand_api:
                return TestConnectionResponse(
                    success=False,
                    status="failed",
                    message=f"Broker '{server}' requires Brand API Key mode. Please provide api_key and optionally environment_url.",
                    details={
                        "mode": "brand_api_required",
                        "server": server,
                        "required": ["api_key"],
                        "optional": ["environment_url", "server"]
                    }
                )
            else:
                return TestConnectionResponse(
                    success=False,
                    status="failed",
                    message="Missing TradeLocker credentials. Provide either (username, password, server) for SDK mode or (api_key) for Brand API mode.",
                    details={
                        "required_sdk": ["username", "password", "server"],
                        "required_brand": ["api_key"],
                        "optional_brand": ["environment_url", "server"]
                    }
                )

        except Exception as e:
            return TestConnectionResponse(
                success=False,
                status="failed",
                message=f"TradeLocker connection error: {str(e)}",
                details={"error": str(e)}
            )

    def _requires_brand_api(self, server: Optional[str]) -> bool:
        """
        Check if a broker server requires Brand API authentication.
        
        Some brokers (e.g., GATESFX) only support Brand API and don't allow
        username/password SDK authentication.
        
        Args:
            server: Broker server name (e.g., "GATESFX", "gatesfx")
            
        Returns:
            True if Brand API is required, False otherwise
        """
        if not server:
            return False
        
        # Normalize server name for comparison
        server_upper = server.upper()
        
        # List of servers that require Brand API
        BRAND_API_REQUIRED_SERVERS = [
            "GATESFX",
            "GATES FX",
        ]
        
        return server_upper in BRAND_API_REQUIRED_SERVERS

    async def _test_tradovate(self, credentials: dict) -> TestConnectionResponse:
        """Test Tradovate connection."""
        try:
            # Tradovate uses OAuth - direct password testing not recommended
            # Check for API credentials instead
            user_id = credentials.get("user_id") or credentials.get("username")
            password = credentials.get("password")
            app_id = credentials.get("app_id")
            app_version = credentials.get("app_version")
            cid = credentials.get("cid")
            sec = credentials.get("sec")
            environment = credentials.get("environment", "demo")

            if not (user_id and password):
                return TestConnectionResponse(
                    success=False,
                    status="failed",
                    message="Missing Tradovate credentials. Provide user_id and password. "
                            "Note: OAuth authentication is recommended for production.",
                    details={"required": ["user_id", "password"], "optional": ["app_id", "cid", "sec"]}
                )

            try:
                import httpx

                api_url = (
                    "https://live.tradovate.com/v1"
                    if environment == "live"
                    else "https://demo.tradovate.com/v1"
                )

                async with httpx.AsyncClient(timeout=10.0) as client:
                    auth_data = {
                        "username": user_id,
                        "password": password,
                    }
                    if app_id:
                        auth_data["appId"] = app_id
                    if app_version:
                        auth_data["appVersion"] = app_version
                    if cid:
                        auth_data["cid"] = cid
                    if sec:
                        auth_data["sec"] = sec

                    response = await client.post(
                        f"{api_url}/auth/accesstokenrequest",
                        json=auth_data
                    )

                    if response.status_code == 200:
                        result = response.json()
                        access_token = result.get("accessToken")
                        if access_token:
                            # Get symbols for format detection
                            symbols = []
                            try:
                                sym_response = await client.get(
                                    f"{api_url}/contract/find",
                                    headers={"Authorization": f"Bearer {access_token}"}
                                )
                                if sym_response.status_code == 200:
                                    contracts = sym_response.json()
                                    symbols = [c.get("name", c.get("symbol", "")) for c in contracts]
                            except Exception as e:
                                logger.warning(f"Failed to get Tradovate symbols: {e}")

                            # Detect symbol format
                            detected_format, symbol_map, sample_symbols = self._detect_symbols(symbols)

                            return TestConnectionResponse(
                                success=True,
                                status="connected",
                                message="Successfully authenticated with Tradovate",
                                details={"environment": environment, "mode": "password"},
                                detected_format=detected_format,
                                symbol_map=symbol_map,
                                sample_symbols=sample_symbols,
                            )
                        else:
                            return TestConnectionResponse(
                                success=False,
                                status="failed",
                                message="Tradovate authentication failed: No access token received",
                                details={"environment": environment}
                            )
                    elif response.status_code == 401:
                        return TestConnectionResponse(
                            success=False,
                            status="failed",
                            message="Invalid Tradovate credentials. Please verify your username and password.",
                            details={"http_status": 401, "environment": environment}
                        )
                    else:
                        error_text = response.text[:200] if response.text else "Unknown error"
                        return TestConnectionResponse(
                            success=False,
                            status="failed",
                            message=f"Tradovate authentication error: {error_text}",
                            details={"http_status": response.status_code, "environment": environment}
                        )

            except Exception as e:
                return TestConnectionResponse(
                    success=False,
                    status="failed",
                    message=f"Tradovate connection error: {str(e)}",
                    details={"error": str(e)}
                )

        except Exception as e:
            return TestConnectionResponse(
                success=False,
                status="failed",
                message=f"Tradovate test error: {str(e)}",
                details={"error": str(e)}
            )

    async def _test_projectx(self, credentials: dict) -> TestConnectionResponse:
        """Test ProjectX/TopStep connection."""
        try:
            username = credentials.get("username")
            api_key = credentials.get("api_key") or credentials.get("api_token")

            if not (username and api_key):
                return TestConnectionResponse(
                    success=False,
                    status="failed",
                    message="Missing ProjectX/TopStep credentials. Provide username and api_key.",
                    details={"required": ["username", "api_key"]}
                )

            # Try SDK first
            try:
                from app.services.projectx_sdk_service import ProjectXSDKService, SDK_AVAILABLE

                if SDK_AVAILABLE:
                    service = ProjectXSDKService(
                        username=username,
                        api_key=api_key,
                    )

                    success = await service.connect()
                    if success:
                        # Get symbols for format detection
                        symbols = []
                        try:
                            # Use search_instruments to get available contracts
                            # Search for common futures symbols
                            common_symbols = ["MNQ", "MES", "M2K", "MYM", "MCL", "MGC"]
                            all_contracts = []
                            for sym in common_symbols:
                                try:
                                    contracts = await service.search_instruments(sym)
                                    if contracts:
                                        all_contracts.extend(contracts)
                                except Exception:
                                    continue
                            
                            if all_contracts:
                                symbols = [c.get("symbol", c.get("name", "")) for c in all_contracts]
                        except Exception as e:
                            logger.warning(f"Failed to get ProjectX symbols: {e}")

                        await service.disconnect()

                        # Detect symbol format
                        detected_format, symbol_map, sample_symbols = self._detect_symbols(symbols)

                        return TestConnectionResponse(
                            success=True,
                            status="connected",
                            message="Successfully connected to ProjectX/TopStep via SDK",
                            details={"mode": "sdk"},
                            detected_format=detected_format,
                            symbol_map=symbol_map,
                            sample_symbols=sample_symbols,
                        )
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"ProjectX SDK test failed: {e}")

            # Fallback to httpx
            try:
                import httpx

                api_url = "https://api.topstepx.com"

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{api_url}/api/Auth/loginKey",
                        json={"userName": username, "apiKey": api_key},
                        headers={"Content-Type": "application/json", "Accept": "text/plain"}
                    )

                    if response.status_code == 200:
                        # Get auth token from response
                        auth_token = None
                        try:
                            auth_data = response.json()
                            auth_token = auth_data.get("token")
                        except Exception:
                            # Response might be plain text token
                            auth_token = response.text.strip()

                        # Get symbols for format detection
                        symbols = []
                        if auth_token:
                            try:
                                sym_response = await client.get(
                                    f"{api_url}/api/Contract/Search",
                                    headers={"Authorization": f"Bearer {auth_token}"}
                                )
                                if sym_response.status_code == 200:
                                    contracts = sym_response.json()
                                    symbols = [c.get("name", c.get("symbol", "")) for c in contracts]
                            except Exception as e:
                                logger.warning(f"Failed to get ProjectX symbols: {e}")

                        # Detect symbol format
                        detected_format, symbol_map, sample_symbols = self._detect_symbols(symbols)

                        return TestConnectionResponse(
                            success=True,
                            status="connected",
                            message="Successfully authenticated with ProjectX/TopStep",
                            details={"mode": "httpx"},
                            detected_format=detected_format,
                            symbol_map=symbol_map,
                            sample_symbols=sample_symbols,
                        )
                    elif response.status_code == 401:
                        return TestConnectionResponse(
                            success=False,
                            status="failed",
                            message="Invalid ProjectX/TopStep credentials. Please verify your username and API key.",
                            details={"http_status": 401}
                        )
                    else:
                        return TestConnectionResponse(
                            success=False,
                            status="failed",
                            message=f"ProjectX/TopStep authentication failed: {response.status_code}",
                            details={"http_status": response.status_code}
                        )

            except Exception as e:
                error_str = str(e)
                # Check if it's a DNS/network error vs auth error
                if "Name or service not known" in error_str or "getaddrinfo failed" in error_str:
                    return TestConnectionResponse(
                        success=False,
                        status="failed",
                        message="ProjectX/TopStep API endpoint unreachable. Check network connectivity and API URL configuration.",
                        details={"error": "DNS resolution failed", "suggestion": "Verify PROJECTX_API_URL environment variable or network access"}
                    )
                return TestConnectionResponse(
                    success=False,
                    status="failed",
                    message=f"ProjectX/TopStep connection error: {str(e)}",
                    details={"error": str(e)}
                )

        except Exception as e:
            error_str = str(e)
            # Check if it's a DNS/network error vs auth error
            if "Name or service not known" in error_str or "getaddrinfo failed" in error_str:
                return TestConnectionResponse(
                    success=False,
                    status="failed",
                    message="ProjectX/TopStep API endpoint unreachable. Check network connectivity and API URL configuration.",
                    details={"error": "DNS resolution failed", "suggestion": "Verify PROJECTX_API_URL environment variable or network access"}
                )
            return TestConnectionResponse(
                success=False,
                status="failed",
                message=f"ProjectX/TopStep test error: {str(e)}",
                details={"error": str(e)}
            )

    async def _test_mt4(self, credentials: dict) -> TestConnectionResponse:
        """Test MT4 connection (MetaAPI or Manager API)."""
        return await self._test_metatrader(credentials, "mt4")

    async def _test_mt5(self, credentials: dict) -> TestConnectionResponse:
        """Test MT5 connection (MetaAPI or Manager API)."""
        return await self._test_metatrader(credentials, "mt5")

    async def _test_metatrader(self, credentials: dict, platform: str) -> TestConnectionResponse:
        """Test MetaTrader (MT4/MT5) connection."""
        try:
            metaapi_token = credentials.get("metaapi_token")
            metaapi_account_id = credentials.get("metaapi_account_id")
            manager_login = credentials.get("manager_login") or credentials.get("login")
            manager_password = credentials.get("manager_password") or credentials.get("password")

            platform_upper = platform.upper()

            # MetaAPI SDK mode (preferred)
            if metaapi_token and metaapi_account_id:
                try:
                    from app.services.metaapi_sdk_service import MetaAPISDKService, SDK_AVAILABLE

                    if SDK_AVAILABLE:
                        service = MetaAPISDKService(
                            token=metaapi_token,
                            account_id=metaapi_account_id,
                            application="tradeflow",
                        )

                        success = await service.connect()
                        if success:
                            # Get symbols for format detection
                            symbols = []
                            try:
                                symbol_list = await service.get_symbols()
                                if symbol_list:
                                    symbols = [s.get("symbol", s.get("name", "")) for s in symbol_list]
                            except Exception as e:
                                logger.warning(f"Failed to get {platform_upper} symbols: {e}")

                            await service.disconnect()

                            # Detect symbol format
                            detected_format, symbol_map, sample_symbols = self._detect_symbols(symbols)

                            return TestConnectionResponse(
                                success=True,
                                status="connected",
                                message=f"Successfully connected to {platform_upper} via MetaAPI SDK",
                                details={"mode": "metaapi_sdk", "platform": platform},
                                detected_format=detected_format,
                                symbol_map=symbol_map,
                                sample_symbols=sample_symbols,
                            )
                        else:
                            return TestConnectionResponse(
                                success=False,
                                status="failed",
                                message=f"MetaAPI SDK connection failed for {platform_upper}. "
                                        "Please verify your token and account ID.",
                                details={"mode": "metaapi_sdk", "platform": platform}
                            )
                except ImportError:
                    logger.warning("MetaAPI SDK not available, trying Manager API")
                except Exception as e:
                    return TestConnectionResponse(
                        success=False,
                        status="failed",
                        message=f"MetaAPI SDK error: {str(e)}",
                        details={"mode": "metaapi_sdk", "error": str(e)}
                    )

            # Manager API mode (fallback)
            if manager_login and manager_password:
                try:
                    import httpx
                    from app.core.config import settings

                    config = settings.get_broker_config(platform)
                    api_url = config.get("api_url")

                    if not api_url:
                        return TestConnectionResponse(
                            success=False,
                            status="failed",
                            message=f"{platform_upper} Manager API URL not configured. "
                                    "Please set up the API URL in your configuration.",
                            details={"mode": "manager_api", "platform": platform}
                        )

                    async with httpx.AsyncClient(
                        base_url=api_url,
                        timeout=10.0
                    ) as client:
                        response = await client.post(
                            "/auth/login",
                            json={
                                "login": manager_login,
                                "password": manager_password
                            }
                        )

                        if response.status_code == 200:
                            # Get auth token from response
                            auth_token = None
                            try:
                                auth_data = response.json()
                                auth_token = auth_data.get("token") or auth_data.get("access_token")
                            except Exception:
                                pass

                            # Get symbols for format detection
                            symbols = []
                            if auth_token:
                                try:
                                    sym_response = await client.get(
                                        "/symbols",
                                        headers={"Authorization": f"Bearer {auth_token}"}
                                    )
                                    if sym_response.status_code == 200:
                                        symbols_data = sym_response.json()
                                        symbols = [s.get("symbol", s.get("name", "")) for s in symbols_data]
                                except Exception as e:
                                    logger.warning(f"Failed to get {platform_upper} symbols: {e}")

                            # Detect symbol format
                            detected_format, symbol_map, sample_symbols = self._detect_symbols(symbols)

                            return TestConnectionResponse(
                                success=True,
                                status="connected",
                                message=f"Successfully connected to {platform_upper} via Manager API",
                                details={"mode": "manager_api", "platform": platform},
                                detected_format=detected_format,
                                symbol_map=symbol_map,
                                sample_symbols=sample_symbols,
                            )
                        elif response.status_code == 401:
                            return TestConnectionResponse(
                                success=False,
                                status="failed",
                                message=f"Invalid {platform_upper} Manager credentials. "
                                        "Please verify your login and password.",
                                details={"mode": "manager_api", "http_status": 401}
                            )
                        else:
                            return TestConnectionResponse(
                                success=False,
                                status="failed",
                                message=f"{platform_upper} Manager API error: {response.status_code}",
                                details={"mode": "manager_api", "http_status": response.status_code}
                            )

                except Exception as e:
                    return TestConnectionResponse(
                        success=False,
                        status="failed",
                        message=f"{platform_upper} Manager API connection error: {str(e)}",
                        details={"mode": "manager_api", "error": str(e)}
                    )

            return TestConnectionResponse(
                success=False,
                status="failed",
                message=f"Missing {platform_upper} credentials. Provide either (metaapi_token, metaapi_account_id) "
                        "for MetaAPI mode or (manager_login, manager_password) for Manager API mode.",
                details={
                    "required_metaapi": ["metaapi_token", "metaapi_account_id"],
                    "required_manager": ["manager_login", "manager_password"],
                    "platform": platform
                }
            )

        except Exception as e:
            return TestConnectionResponse(
                success=False,
                status="failed",
                message=f"{platform.upper()} test error: {str(e)}",
                details={"error": str(e)}
            )
