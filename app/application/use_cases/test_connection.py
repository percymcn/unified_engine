"""
Test Connection Use Case

Tests broker connections with provided credentials before saving accounts.
"""
import asyncio
import logging
from typing import Dict, Any, Optional

from app.domain.enums import BrokerType
from app.application.dto.account_dto import (
    TestConnectionRequest,
    TestConnectionResponse,
)

logger = logging.getLogger(__name__)

# Connection test timeout in seconds
CONNECTION_TIMEOUT = 10


class TestConnectionUseCase:
    """
    Use case for testing broker connections before saving account.

    Tests credentials by attempting to authenticate with the broker
    and returns detailed status information.
    """

    def __init__(self):
        """Initialize with no dependencies - creates temporary connections."""
        pass

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

    async def _test_tradelocker(self, credentials: dict) -> TestConnectionResponse:
        """Test TradeLocker connection."""
        try:
            # Check for required credentials
            username = credentials.get("username")
            password = credentials.get("password")
            server = credentials.get("server")
            api_key = credentials.get("api_key")

            # SDK mode (user credentials)
            if username and password and server:
                try:
                    from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

                    environment = credentials.get("environment", "https://demo.tradelocker.com")
                    wrapper = TradeLockerSDKWrapper(
                        environment=environment,
                        username=username,
                        password=password,
                        server=server
                    )

                    success = await wrapper.initialize()
                    if success:
                        wrapper.shutdown()
                        return TestConnectionResponse(
                            success=True,
                            status="connected",
                            message="Successfully connected to TradeLocker via SDK",
                            details={"mode": "sdk", "server": server}
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
                            return TestConnectionResponse(
                                success=True,
                                status="connected",
                                message="Successfully connected to TradeLocker via Brand API",
                                details={"mode": "brand_api"}
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

            return TestConnectionResponse(
                success=False,
                status="failed",
                message="Missing TradeLocker credentials. Provide either (username, password, server) for SDK mode or (api_key) for Brand API mode.",
                details={"required_sdk": ["username", "password", "server"], "required_brand": ["api_key"]}
            )

        except Exception as e:
            return TestConnectionResponse(
                success=False,
                status="failed",
                message=f"TradeLocker connection error: {str(e)}",
                details={"error": str(e)}
            )

    async def _test_tradovate(self, credentials: dict) -> TestConnectionResponse:
        """Test Tradovate connection."""
        try:
            # Tradovate uses OAuth - direct password testing not recommended
            # Check for API credentials instead
            user_id = credentials.get("user_id") or credentials.get("username")
            password = credentials.get("password")
            app_id = credentials.get("app_id")
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
                        if result.get("accessToken"):
                            return TestConnectionResponse(
                                success=True,
                                status="connected",
                                message="Successfully authenticated with Tradovate",
                                details={"environment": environment, "mode": "password"}
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
                        await service.disconnect()
                        return TestConnectionResponse(
                            success=True,
                            status="connected",
                            message="Successfully connected to ProjectX/TopStep via SDK",
                            details={"mode": "sdk"}
                        )
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"ProjectX SDK test failed: {e}")

            # Fallback to httpx
            try:
                import httpx

                api_url = "https://gateway-api.s2f.projectx.com/api"

                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{api_url}/Auth/loginKey",
                        json={"userName": username, "apiKey": api_key},
                        headers={"Content-Type": "application/json", "Accept": "text/plain"}
                    )

                    if response.status_code == 200:
                        return TestConnectionResponse(
                            success=True,
                            status="connected",
                            message="Successfully authenticated with ProjectX/TopStep",
                            details={"mode": "httpx"}
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
                return TestConnectionResponse(
                    success=False,
                    status="failed",
                    message=f"ProjectX/TopStep connection error: {str(e)}",
                    details={"error": str(e)}
                )

        except Exception as e:
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
                            await service.disconnect()
                            return TestConnectionResponse(
                                success=True,
                                status="connected",
                                message=f"Successfully connected to {platform_upper} via MetaAPI SDK",
                                details={"mode": "metaapi_sdk", "platform": platform}
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
                            return TestConnectionResponse(
                                success=True,
                                status="connected",
                                message=f"Successfully connected to {platform_upper} via Manager API",
                                details={"mode": "manager_api", "platform": platform}
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
