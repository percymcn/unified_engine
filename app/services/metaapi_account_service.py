"""
MetaApi Account Service - BYOA (Bring Your Own Account)

Connects existing MT4/MT5 accounts to MetaApi Cloud for webhook execution.
This service NEVER stores passwords - only the metaapi_account_id is persisted.

Flow:
1. User provides platform, login, password, server
2. We create account in MetaApi Cloud
3. Deploy and wait for connection
4. Store metaapi_account_id (password discarded from memory)
5. Webhook execution uses stored metaapi_account_id
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import SDK
try:
    from metaapi_cloud_sdk import MetaApi
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    MetaApi = None
    logger.warning("metaapi-cloud-sdk not installed - MetaApi account service unavailable")


class MetaApiAccountStatus(str, Enum):
    """Status of a MetaApi-connected account"""
    CREATING = "creating"
    DEPLOYING = "deploying"
    CONNECTING = "connecting"
    SYNCING = "syncing"
    READY = "ready"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


class MetaApiAccountError(Exception):
    """Base exception for MetaApi account operations"""
    pass


class AuthenticationError(MetaApiAccountError):
    """Invalid credentials"""
    pass


class ServerNotFoundError(MetaApiAccountError):
    """Broker server not found"""
    pass


class AccountBlockedError(MetaApiAccountError):
    """Account is blocked or disabled"""
    pass


class ConnectionTimeoutError(MetaApiAccountError):
    """Connection timed out"""
    pass


class MetaApiAccountService:
    """
    Service for connecting existing MT4/MT5 accounts via MetaApi Cloud.

    Security guarantees:
    - Passwords are NEVER logged
    - Passwords are NEVER stored in DB
    - Passwords are discarded from memory after MetaApi call
    - Only metaapi_account_id is persisted
    """

    def __init__(self, master_token: str, application: str = "tradeflow"):
        """
        Initialize service with master API token.

        Args:
            master_token: MetaAPI API token with provisioning access
            application: Application name for MetaApi accounts
        """
        self.master_token = master_token
        self.application = application
        self._api: Optional[Any] = None

    async def _get_api(self) -> Any:
        """Get or create MetaApi instance."""
        if not SDK_AVAILABLE:
            raise RuntimeError("metaapi-cloud-sdk not installed. Install with: pip install metaapi-cloud-sdk")

        if self._api is None:
            self._api = MetaApi(token=self.master_token)
        return self._api

    async def connect_existing_account(
        self,
        platform: str,
        login: str,
        password: str,
        server: str,
        nickname: Optional[str] = None,
        deploy_timeout: int = 120,
    ) -> Dict[str, Any]:
        """
        Connect an existing MT4/MT5 account via MetaApi Cloud.

        IMPORTANT: Password is discarded after this call completes.

        Args:
            platform: "mt4" or "mt5"
            login: MT4/MT5 login number
            password: MT4/MT5 password (NEVER stored/logged)
            server: Broker server name (e.g., "ICMarkets-Demo")
            nickname: Optional friendly name for the account
            deploy_timeout: Max seconds to wait for deployment (default 120)

        Returns:
            Dict with:
                - metaapi_account_id: The MetaApi account ID to store
                - status: Current status (deploying, connected, etc.)
                - platform: mt4 or mt5
                - login: Account login (for display only)
                - server: Server name
                - connection_status: MetaApi connection status
                - account_info: Balance/equity if available

        Raises:
            AuthenticationError: Invalid login/password
            ServerNotFoundError: Broker server not found
            AccountBlockedError: Account disabled
            ConnectionTimeoutError: Connection timed out
            MetaApiAccountError: Other errors
        """
        if not SDK_AVAILABLE:
            raise RuntimeError("metaapi-cloud-sdk not installed")

        platform = platform.lower()
        if platform not in ("mt4", "mt5"):
            raise ValueError(f"Platform must be 'mt4' or 'mt5', got '{platform}'")

        api = await self._get_api()

        # Generate account name
        name = nickname or f"{platform.upper()}-{login}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        logger.info(f"Connecting existing {platform.upper()} account: login={login}, server={server}")

        try:
            # Create account in MetaApi
            account = await api.metatrader_account_api.create_account({
                "name": name,
                "type": "cloud",
                "login": login,
                "password": password,  # Sent to MetaApi only, never stored by us
                "server": server,
                "platform": platform,
                "application": self.application,
            })

            metaapi_account_id = account.id
            logger.info(f"MetaApi account created: {metaapi_account_id}")

            # Deploy the account
            if account.state != "DEPLOYED":
                logger.info(f"Deploying MetaApi account {metaapi_account_id}...")
                await account.deploy()

            # Wait for connection with timeout
            connection_status = "deploying"
            account_info = {}

            try:
                await asyncio.wait_for(
                    account.wait_connected(),
                    timeout=float(deploy_timeout)
                )
                connection_status = "connected"
                logger.info(f"MetaApi account {metaapi_account_id} connected to broker")

                # Try to get account info
                try:
                    connection = account.get_streaming_connection()
                    await connection.connect()
                    await asyncio.wait_for(
                        connection.wait_synchronized(),
                        timeout=60.0
                    )

                    terminal_state = connection.terminal_state
                    if terminal_state and terminal_state.account_information:
                        info = terminal_state.account_information
                        account_info = {
                            "balance": float(info.get("balance", 0)),
                            "equity": float(info.get("equity", 0)),
                            "margin": float(info.get("margin", 0)),
                            "free_margin": float(info.get("freeMargin", 0)),
                            "leverage": int(info.get("leverage", 1)),
                            "currency": info.get("currency", "USD"),
                            "trade_allowed": info.get("tradeAllowed", True),
                        }

                    await connection.close()
                except asyncio.TimeoutError:
                    logger.warning(f"Sync timeout for {metaapi_account_id} - basic info only")
                except Exception as e:
                    logger.warning(f"Could not get account info: {e}")

            except asyncio.TimeoutError:
                connection_status = "deploying"
                logger.warning(f"Connection timeout for {metaapi_account_id} - may still connect later")

            # Get final state
            await account.reload()

            return {
                "metaapi_account_id": metaapi_account_id,
                "status": MetaApiAccountStatus.READY.value if connection_status == "connected" else MetaApiAccountStatus.DEPLOYING.value,
                "platform": platform,
                "login": login,
                "server": server,
                "name": name,
                "state": account.state,
                "connection_status": account.connection_status,
                "account_info": account_info,
                "connected_at": datetime.utcnow().isoformat() if connection_status == "connected" else None,
            }

        except Exception as e:
            error_msg = str(e).lower()

            # Map to specific errors
            if "e_auth" in error_msg or "invalid login" in error_msg or "authentication" in error_msg:
                raise AuthenticationError(f"Invalid {platform.upper()} credentials. Check login and password.")
            elif "e_server_not_found" in error_msg or "server not found" in error_msg:
                raise ServerNotFoundError(f"Broker server '{server}' not found. Check the server name.")
            elif "blocked" in error_msg or "disabled" in error_msg:
                raise AccountBlockedError(f"Account {login} is blocked or disabled.")
            elif "timeout" in error_msg:
                raise ConnectionTimeoutError(f"Connection timed out. The broker may be unavailable.")
            elif "401" in error_msg or "unauthorized" in error_msg:
                raise MetaApiAccountError("Invalid METAAPI_TOKEN. Check your MetaApi token configuration.")
            else:
                logger.error(f"MetaApi connect failed: {e}")
                raise MetaApiAccountError(f"Failed to connect account: {str(e)}")

    async def get_account_status(self, metaapi_account_id: str) -> Dict[str, Any]:
        """
        Get current status of a MetaApi account.

        Args:
            metaapi_account_id: The MetaApi account ID

        Returns:
            Dict with status, state, connection_status, account_info
        """
        if not SDK_AVAILABLE:
            return {"error": "SDK not available"}

        try:
            api = await self._get_api()
            account = await api.metatrader_account_api.get_account(metaapi_account_id)

            # Map state to our status enum
            state = account.state
            conn_status = account.connection_status

            if state == "DEPLOYED" and conn_status == "CONNECTED":
                status = MetaApiAccountStatus.READY.value
            elif state == "DEPLOYED" and conn_status == "DISCONNECTED":
                status = MetaApiAccountStatus.DISCONNECTED.value
            elif state == "DEPLOYING":
                status = MetaApiAccountStatus.DEPLOYING.value
            elif state == "UNDEPLOYED":
                status = MetaApiAccountStatus.DISCONNECTED.value
            else:
                status = MetaApiAccountStatus.CONNECTING.value

            return {
                "metaapi_account_id": metaapi_account_id,
                "status": status,
                "state": state,
                "connection_status": conn_status,
                "name": account.name,
                "platform": account.platform,
                "server": account.server,
            }
        except Exception as e:
            logger.error(f"Failed to get account status: {e}")
            return {
                "metaapi_account_id": metaapi_account_id,
                "status": MetaApiAccountStatus.FAILED.value,
                "error": str(e),
            }

    async def deploy_account(self, metaapi_account_id: str, timeout: int = 120) -> Dict[str, Any]:
        """
        Deploy/redeploy a MetaApi account.

        Args:
            metaapi_account_id: The MetaApi account ID
            timeout: Max seconds to wait for deployment

        Returns:
            Dict with deployment result
        """
        if not SDK_AVAILABLE:
            raise RuntimeError("SDK not available")

        try:
            api = await self._get_api()
            account = await api.metatrader_account_api.get_account(metaapi_account_id)

            if account.state != "DEPLOYED":
                logger.info(f"Deploying account {metaapi_account_id}...")
                await account.deploy()

            try:
                await asyncio.wait_for(
                    account.wait_connected(),
                    timeout=float(timeout)
                )
                logger.info(f"Account {metaapi_account_id} deployed and connected")
                return {
                    "metaapi_account_id": metaapi_account_id,
                    "status": MetaApiAccountStatus.READY.value,
                    "deployed": True,
                }
            except asyncio.TimeoutError:
                logger.warning(f"Deploy timeout for {metaapi_account_id}")
                return {
                    "metaapi_account_id": metaapi_account_id,
                    "status": MetaApiAccountStatus.DEPLOYING.value,
                    "deployed": True,
                    "connected": False,
                    "message": "Deployed but connection still in progress",
                }
        except Exception as e:
            logger.error(f"Deploy failed: {e}")
            return {
                "metaapi_account_id": metaapi_account_id,
                "status": MetaApiAccountStatus.FAILED.value,
                "deployed": False,
                "error": str(e),
            }

    async def ensure_synchronized(
        self,
        metaapi_account_id: str,
        timeout: int = 30
    ) -> Tuple[bool, Optional[str]]:
        """
        Ensure account is synchronized and ready for trading.

        Used by webhook executor before placing trades.
        Does NOT retry infinitely - returns error if sync fails.

        Args:
            metaapi_account_id: The MetaApi account ID
            timeout: Max seconds to wait for sync

        Returns:
            Tuple of (is_ready, error_message)
        """
        if not SDK_AVAILABLE:
            return False, "SDK not available"

        try:
            api = await self._get_api()
            account = await api.metatrader_account_api.get_account(metaapi_account_id)

            # Check if deployed
            if account.state != "DEPLOYED":
                return False, f"Account not deployed (state: {account.state})"

            # Check if connected
            if account.connection_status != "CONNECTED":
                return False, f"Account not connected (status: {account.connection_status})"

            # Try to sync
            try:
                connection = account.get_streaming_connection()
                await connection.connect()
                await asyncio.wait_for(
                    connection.wait_synchronized(),
                    timeout=float(timeout)
                )
                await connection.close()
                return True, None
            except asyncio.TimeoutError:
                return False, f"Sync timeout ({timeout}s)"
            except Exception as e:
                return False, f"Sync failed: {str(e)}"

        except Exception as e:
            return False, f"Account check failed: {str(e)}"

    async def undeploy_account(self, metaapi_account_id: str) -> bool:
        """
        Undeploy a MetaApi account (stop cloud connection).

        Args:
            metaapi_account_id: The MetaApi account ID

        Returns:
            True if successful
        """
        if not SDK_AVAILABLE:
            return False

        try:
            api = await self._get_api()
            account = await api.metatrader_account_api.get_account(metaapi_account_id)

            if account.state == "DEPLOYED":
                await account.undeploy()
                await account.wait_undeployed()

            logger.info(f"Account {metaapi_account_id} undeployed")
            return True
        except Exception as e:
            logger.error(f"Undeploy failed: {e}")
            return False

    async def remove_account(self, metaapi_account_id: str) -> bool:
        """
        Remove a MetaApi account completely.

        Args:
            metaapi_account_id: The MetaApi account ID

        Returns:
            True if successful
        """
        if not SDK_AVAILABLE:
            return False

        try:
            api = await self._get_api()
            account = await api.metatrader_account_api.get_account(metaapi_account_id)

            # Undeploy first if needed
            if account.state == "DEPLOYED":
                await account.undeploy()
                await account.wait_undeployed()

            await account.remove()
            logger.info(f"Account {metaapi_account_id} removed")
            return True
        except Exception as e:
            logger.error(f"Remove failed: {e}")
            return False


# Singleton instance
_service: Optional[MetaApiAccountService] = None


def get_metaapi_account_service() -> Optional[MetaApiAccountService]:
    """
    Get the MetaApi account service singleton.

    Returns:
        MetaApiAccountService instance or None if not configured
    """
    global _service

    if _service is None:
        from app.core.config import settings

        token = settings.METAAPI_TOKEN
        if not token:
            logger.warning("METAAPI_TOKEN not configured - MetaApi account service disabled")
            return None

        _service = MetaApiAccountService(
            master_token=token,
            application=settings.METAAPI_APPLICATION or "tradeflow",
        )

    return _service
