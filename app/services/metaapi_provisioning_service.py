"""
MetaAPI Provisioning Service

Automatically provisions MetaAPI accounts for users based on their
MT4/MT5 broker credentials. This allows users to simply enter their
broker login/password/server and the platform handles MetaAPI integration.

Requires METAAPI_TOKEN environment variable with provisioning API access.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import SDK
try:
    from metaapi_cloud_sdk import MetaApi
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    MetaApi = None
    logger.warning("metaapi-cloud-sdk not installed, provisioning unavailable")


class MetaAPIProvisioningService:
    """
    Service for provisioning MetaAPI accounts from user broker credentials.

    This allows users to enter MT4/MT5 login/password/server and
    automatically creates and configures the MetaAPI account.
    """

    def __init__(self, master_token: str, application: str = "tradeflow"):
        """
        Initialize provisioning service with master API token.

        Args:
            master_token: MetaAPI API token with provisioning access
            application: Application name for MetaAPI accounts
        """
        self.master_token = master_token
        self.application = application
        self._api: Optional[Any] = None

    async def _get_api(self) -> Any:
        """Get or create MetaApi instance."""
        if not SDK_AVAILABLE:
            raise RuntimeError("metaapi-cloud-sdk not installed")

        if self._api is None:
            # MetaAPI SDK v29+ uses token only - application is set per-account
            self._api = MetaApi(token=self.master_token)
        return self._api

    async def provision_account(
        self,
        login: str,
        password: str,
        server: str,
        platform: str = "mt4",
        name: Optional[str] = None,
        magic: Optional[int] = None,
        copy_factory_roles: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Provision a new MetaAPI account from broker credentials.

        Args:
            login: MT4/MT5 account login number
            password: MT4/MT5 account password (investor or master)
            server: Broker server name (e.g., ICMarkets-Demo)
            platform: Platform type - "mt4" or "mt5"
            name: Optional friendly name for the account
            magic: Optional magic number for trade identification
            copy_factory_roles: Optional roles for CopyFactory (e.g., ["SUBSCRIBER"])

        Returns:
            Dict with:
                - account_id: MetaAPI account ID
                - state: Account state (DEPLOYED, etc.)
                - connection_status: Connection status
                - account_info: Account information (balance, equity, etc.)

        Raises:
            RuntimeError: If SDK not available or provisioning fails
        """
        if not SDK_AVAILABLE:
            raise RuntimeError("metaapi-cloud-sdk not installed. Install with: pip install metaapi-cloud-sdk")

        api = await self._get_api()

        # Generate account name if not provided
        if not name:
            name = f"{platform.upper()}-{login}-{datetime.now().strftime('%Y%m%d')}"

        logger.info(f"Provisioning MetaAPI account: {name} (login={login}, server={server}, platform={platform})")

        try:
            # First, check if an account already exists for this login/server
            login_str = str(login)
            existing_account = None
            try:
                # Use the paginated API (SDK v29+)
                accounts_page = await api.metatrader_account_api.get_accounts_with_infinite_scroll_pagination()
                accounts = accounts_page.get('items', []) if isinstance(accounts_page, dict) else accounts_page
                logger.info(f"Checking {len(accounts) if accounts else 0} existing accounts for login={login}, server={server}")

                for acc in accounts:
                    acc_login = str(getattr(acc, 'login', ''))
                    acc_server = getattr(acc, 'server', '')
                    acc_platform = getattr(acc, 'platform', '')

                    # Match by login and server (case-insensitive server match)
                    if (acc_login == login_str and
                        acc_server.lower() == server.lower() and
                        acc_platform == platform):
                        existing_account = acc
                        logger.info(f"Found existing MetaAPI account: {acc.id} for login={login}, server={server}")
                        break
            except Exception as e:
                logger.warning(f"Could not check for existing accounts: {e}")

            if existing_account:
                # Use existing account - ensure it's deployed
                account = existing_account
                account_id = account.id

                if account.state != 'DEPLOYED':
                    logger.info(f"Deploying existing MetaAPI account {account_id}...")
                    await account.deploy()
                    await asyncio.sleep(2)  # Brief wait for deployment
                    await account.reload()

                logger.info(f"Using existing MetaAPI account: {account_id}")
            else:
                # Create new account in MetaAPI
                # Note: login MUST be a string, not integer
                # Magic number is required - use provided or generate default
                magic_number = magic if magic else 123456  # Default magic number for Tradeflow

                account_config = {
                    "name": name,
                    "type": "cloud",  # Cloud account (MetaAPI manages connection)
                    "login": login_str,  # Must be string
                    "password": password,
                    "server": server,
                    "platform": platform,
                    "application": self.application,
                    "magic": magic_number,  # Required by MetaAPI
                }

                # Add optional fields
                if copy_factory_roles:
                    account_config["copyFactoryRoles"] = copy_factory_roles

                logger.info(f"Creating new MetaAPI account with config: name={name}, type=cloud, login={login}, server={server}, platform={platform}")

                account = await api.metatrader_account_api.create_account(account_config)
                account_id = account.id
                logger.info(f"MetaAPI account created: {account_id}")

            # Deploy the account (starts the cloud connection)
            if account.state != 'DEPLOYED':
                logger.info(f"Deploying MetaAPI account {account_id}...")
                await account.deploy()

            # Wait for account to connect to broker (with timeout)
            logger.info(f"Waiting for MetaAPI account to connect to broker...")
            try:
                await asyncio.wait_for(
                    account.wait_connected(),
                    timeout=120.0  # 2 minute timeout for initial connection
                )
            except asyncio.TimeoutError:
                logger.warning(f"Account {account_id} connection timeout - may still connect later")

            # Get account info
            account_info = {}
            try:
                # Create a streaming connection to get account info
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
                        "broker": info.get("broker", ""),
                        "server": info.get("server", server),
                        "trade_allowed": info.get("tradeAllowed", True),
                    }

                await connection.close()

            except asyncio.TimeoutError:
                logger.warning(f"Account {account_id} sync timeout - basic info only")
            except Exception as e:
                logger.warning(f"Could not get account info: {e}")

            # Reload account to get latest state
            await account.reload()

            result = {
                "account_id": account_id,
                "name": name,
                "state": account.state,
                "connection_status": account.connection_status,
                "platform": platform,
                "login": login,
                "server": server,
                "account_info": account_info,
                "provisioned_at": datetime.utcnow().isoformat(),
            }

            logger.info(f"MetaAPI account provisioned successfully: {account_id}")
            return result

        except Exception as e:
            error_msg = str(e)

            # Try to extract error details if available
            error_details = None
            if hasattr(e, 'details'):
                error_details = e.details
                logger.error(f"MetaAPI validation error details: {error_details}")
            if hasattr(e, 'stringCode'):
                logger.error(f"MetaAPI error code: {e.stringCode}")

            # Parse common errors for better messages
            if "E_AUTH" in error_msg or "401" in error_msg:
                raise RuntimeError(f"Invalid MetaAPI master token. Check METAAPI_TOKEN configuration.")
            elif "E_SERVER_NOT_FOUND" in error_msg or "server not found" in error_msg.lower():
                raise RuntimeError(f"Broker server '{server}' not found. Please check the server name.")
            elif "E_LOGIN" in error_msg or "invalid login" in error_msg.lower():
                raise RuntimeError(f"Invalid MT{platform[-1]} credentials. Please check login and password.")
            elif "E_TIMEOUT" in error_msg or "timeout" in error_msg.lower():
                raise RuntimeError(f"Connection timeout. The broker server may be unavailable.")
            elif "Validation failed" in error_msg:
                details_str = f" Details: {error_details}" if error_details else ""
                logger.error(f"MetaAPI validation failed for account config: login={login}, server={server}, platform={platform}.{details_str}")
                raise RuntimeError(f"Account configuration validation failed. Check login, password, and server name.{details_str}")
            else:
                logger.error(f"MetaAPI provisioning failed: {e}")
                raise RuntimeError(f"Failed to provision account: {error_msg}")

    async def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a provisioned account.

        Args:
            account_id: MetaAPI account ID

        Returns:
            Dict with account information or None if not found
        """
        if not SDK_AVAILABLE:
            return None

        try:
            api = await self._get_api()
            account = await api.metatrader_account_api.get_account(account_id)

            return {
                "account_id": account.id,
                "name": account.name,
                "state": account.state,
                "connection_status": account.connection_status,
                "platform": account.platform,
                "server": account.server,
            }
        except Exception as e:
            logger.error(f"Failed to get account {account_id}: {e}")
            return None

    async def remove_account(self, account_id: str) -> bool:
        """
        Remove a provisioned MetaAPI account.

        Args:
            account_id: MetaAPI account ID to remove

        Returns:
            True if successfully removed
        """
        if not SDK_AVAILABLE:
            return False

        try:
            api = await self._get_api()
            account = await api.metatrader_account_api.get_account(account_id)

            # Undeploy first if deployed
            if account.state == 'DEPLOYED':
                logger.info(f"Undeploying MetaAPI account {account_id}...")
                await account.undeploy()
                await account.wait_undeployed()

            # Remove the account
            logger.info(f"Removing MetaAPI account {account_id}...")
            await account.remove()

            logger.info(f"MetaAPI account {account_id} removed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to remove account {account_id}: {e}")
            return False

    async def redeploy_account(self, account_id: str) -> bool:
        """
        Redeploy a MetaAPI account (useful if connection was lost).

        Args:
            account_id: MetaAPI account ID

        Returns:
            True if successfully redeployed
        """
        if not SDK_AVAILABLE:
            return False

        try:
            api = await self._get_api()
            account = await api.metatrader_account_api.get_account(account_id)

            if account.state != 'DEPLOYED':
                logger.info(f"Deploying MetaAPI account {account_id}...")
                await account.deploy()

            await account.wait_connected()
            logger.info(f"MetaAPI account {account_id} redeployed and connected")
            return True

        except Exception as e:
            logger.error(f"Failed to redeploy account {account_id}: {e}")
            return False


# Singleton instance (created on first use)
_provisioning_service: Optional[MetaAPIProvisioningService] = None


def get_provisioning_service() -> Optional[MetaAPIProvisioningService]:
    """
    Get the provisioning service singleton.

    Returns:
        MetaAPIProvisioningService instance or None if not configured
    """
    global _provisioning_service

    if _provisioning_service is None:
        from app.core.config import settings

        master_token = settings.METAAPI_TOKEN
        if not master_token:
            logger.warning("METAAPI_TOKEN not configured - provisioning disabled")
            return None

        _provisioning_service = MetaAPIProvisioningService(
            master_token=master_token,
            application=settings.METAAPI_APPLICATION or "tradeflow",
        )

    return _provisioning_service
