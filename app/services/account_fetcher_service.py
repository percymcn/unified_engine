"""
Account Fetcher Service
Fetches available accounts from each broker SDK.

Enables users to select which accounts receive signals (ACCT-07 through ACCT-10, ACCT-13, ACCT-14).
Supports TradeLocker, ProjectX/TopStep, Tradovate, and MetaAPI (MT4/MT5).
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class BrokerAccountInfo:
    """
    Standardized broker account information.

    Represents account data from any supported broker in a unified format.
    """
    id: str  # Broker-specific account ID format
    name: str  # Human-readable account name
    account_type: str  # live, demo, evaluation, express, funded
    balance: Optional[float] = None
    equity: Optional[float] = None
    currency: Optional[str] = None
    server: Optional[str] = None  # For MT4/MT5
    login: Optional[str] = None  # For MT4/MT5
    broker_type: str = ""  # tradelocker, projectx, tradovate, mt4, mt5
    is_active: bool = True
    leverage: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AccountFetcherService:
    """
    Multi-broker account fetcher service.

    Provides unified interface to fetch available accounts from all supported
    broker SDKs. Each broker returns accounts in BrokerAccountInfo format.

    Broker ID Format Notes:
    - TradeLocker: Numeric IDs (e.g., "12345678")
    - ProjectX/TopStep: Alphanumeric IDs (e.g., "ABC-12345-XY")
    - Tradovate: Numeric IDs (e.g., "987654")
    - MetaAPI: UUID format (e.g., "a1b2c3d4-e5f6-7890-abcd-ef1234567890")
    """

    def __init__(self):
        self._executors = {}

    async def fetch_all_accounts(
        self,
        user_id: int,
        broker_type: str,
        credentials: Dict[str, Any]
    ) -> List[BrokerAccountInfo]:
        """
        Fetch all available accounts for a specific broker.

        Routes to the appropriate broker-specific fetcher based on broker_type.

        Args:
            user_id: User ID for logging/tracking
            broker_type: Broker type (tradelocker, projectx, tradovate, mt4, mt5)
            credentials: Broker-specific credentials dictionary

        Returns:
            List of BrokerAccountInfo objects
        """
        broker_type = broker_type.lower()

        fetcher_map = {
            "tradelocker": self.fetch_tradelocker_accounts,
            "projectx": self.fetch_projectx_accounts,
            "topstep": self.fetch_projectx_accounts,  # Alias
            "tradovate": self.fetch_tradovate_accounts,
            "mt4": self.fetch_metaapi_accounts,
            "mt5": self.fetch_metaapi_accounts,
        }

        fetcher = fetcher_map.get(broker_type)
        if not fetcher:
            logger.error(f"Unsupported broker type: {broker_type}")
            return []

        try:
            accounts = await fetcher(credentials, broker_type)
            logger.info(f"Fetched {len(accounts)} accounts for user {user_id} from {broker_type}")
            return accounts
        except Exception as e:
            logger.error(f"Error fetching accounts from {broker_type}: {e}")
            return []

    async def fetch_tradelocker_accounts(
        self,
        credentials: Dict[str, Any],
        broker_type: str = "tradelocker"
    ) -> List[BrokerAccountInfo]:
        """
        Fetch available accounts from TradeLocker SDK.

        TradeLocker uses numeric account IDs and supports live/demo account types.

        Args:
            credentials: Dict with keys: environment, username, password, server
            broker_type: Should be "tradelocker"

        Returns:
            List of BrokerAccountInfo objects
        """
        accounts = []

        try:
            from app.brokers.tradelocker_sdk_wrapper import TradeLockerSDKWrapper

            # Normalize environment URL to ensure it has proper scheme
            raw_env = credentials.get("environment", "https://demo.tradelocker.com")
            if raw_env:
                raw_env = raw_env.strip()
                if not raw_env.startswith("http://") and not raw_env.startswith("https://"):
                    if raw_env.lower() in ("demo", "live"):
                        raw_env = f"https://{raw_env.lower()}.tradelocker.com"
                    elif "." in raw_env:
                        raw_env = f"https://{raw_env}"
                    else:
                        raw_env = f"https://{raw_env}.tradelocker.com"

            wrapper = TradeLockerSDKWrapper(
                environment=raw_env,
                username=credentials.get("username", credentials.get("email", "")),
                password=credentials.get("password", ""),
                server=credentials.get("server", "")
            )

            if not await wrapper.initialize():
                logger.error("Failed to initialize TradeLocker SDK")
                return []

            try:
                # Get account state for balance/equity info
                account_state = await wrapper.get_account_state()

                # Use get_all_accounts() (v0.56.1+ compatible)
                # get_acc_nums/get_acc_ids don't exist in newer SDK versions
                all_accounts_df = None
                if wrapper._tl:
                    try:
                        loop = asyncio.get_event_loop()
                        all_accounts_df = await loop.run_in_executor(None, wrapper._tl.get_all_accounts)
                    except Exception as e:
                        logger.warning(f"Failed to get accounts via get_all_accounts: {e}")

                if all_accounts_df is not None and len(all_accounts_df) > 0:
                    for _, row in all_accounts_df.iterrows():
                        acc_id = row.get('id', row.get('accountId', None))
                        acc_num = row.get('accNum', row.get('accountNumber', acc_id))

                        # Determine account type from name/config
                        env = credentials.get("environment", "")
                        account_type = "demo" if "demo" in env.lower() else "live"

                        # Get balance from account state if available
                        balance = None
                        equity = None
                        currency = "USD"

                        if account_state:
                            balance = account_state.get("balance", account_state.get("Balance"))
                            equity = account_state.get("projectedBalance", account_state.get("equity", account_state.get("Equity")))
                            currency = account_state.get("currency", "USD")

                        account = BrokerAccountInfo(
                            id=str(acc_id),  # Numeric ID
                            name=f"Account {acc_num}",
                            account_type=account_type,
                            balance=float(balance) if balance else None,
                            equity=float(equity) if equity else None,
                            currency=currency,
                            broker_type=broker_type,
                            is_active=True,
                            metadata={
                                "account_number": acc_num,
                                "server": credentials.get("server", ""),
                            }
                        )
                        accounts.append(account)

            finally:
                wrapper.shutdown()

        except ImportError:
            logger.warning("TradeLocker SDK not available, using fallback")
            # Fallback using executor
            accounts = await self._fetch_tradelocker_fallback(credentials, broker_type)
        except Exception as e:
            logger.error(f"Error fetching TradeLocker accounts: {e}")

        return accounts

    async def _fetch_tradelocker_fallback(
        self,
        credentials: Dict[str, Any],
        broker_type: str
    ) -> List[BrokerAccountInfo]:
        """Fallback account fetching for TradeLocker using executor."""
        try:
            from app.brokers.tradelocker_executor import TradeLockerExecutor

            # Normalize environment URL
            raw_env = credentials.get("sdk_environment") or credentials.get("environment")
            if raw_env:
                raw_env = raw_env.strip()
                if not raw_env.startswith("http://") and not raw_env.startswith("https://"):
                    if raw_env.lower() in ("demo", "live"):
                        raw_env = f"https://{raw_env.lower()}.tradelocker.com"
                    else:
                        raw_env = f"https://{raw_env}.tradelocker.com"

            # Pass credentials through constructor - no env var fallback
            executor = TradeLockerExecutor(
                username=credentials.get("username"),
                password=credentials.get("password"),
                server=credentials.get("server"),
                sdk_environment=raw_env,
            )
            if not await executor.initialize():
                return []

            try:
                broker_accounts = await executor.get_accounts()
                return [
                    BrokerAccountInfo(
                        id=str(acc.id),
                        name=getattr(acc, 'name', f"Account {acc.id}"),
                        account_type=getattr(acc, 'account_type', 'live'),
                        balance=float(acc.balance) if hasattr(acc, 'balance') else None,
                        equity=float(acc.equity) if hasattr(acc, 'equity') else None,
                        currency=getattr(acc, 'currency', 'USD'),
                        broker_type=broker_type,
                        is_active=getattr(acc, 'is_active', True),
                    )
                    for acc in broker_accounts
                ]
            finally:
                await executor.disconnect()
        except Exception as e:
            logger.error(f"TradeLocker fallback failed: {e}")
            return []

    async def fetch_projectx_accounts(
        self,
        credentials: Dict[str, Any],
        broker_type: str = "projectx"
    ) -> List[BrokerAccountInfo]:
        """
        Fetch available accounts from ProjectX/TopStep SDK.

        ProjectX uses alphanumeric account IDs and supports:
        - live: Funded accounts
        - evaluation: Challenge/evaluation accounts
        - express: Express funded accounts

        Args:
            credentials: Dict with keys: username, api_key, account_name (optional)
            broker_type: Should be "projectx" or "topstep"

        Returns:
            List of BrokerAccountInfo objects
        """
        accounts = []

        try:
            from app.services.projectx_sdk_service import ProjectXSDKService, SDK_AVAILABLE

            if not SDK_AVAILABLE:
                logger.warning("ProjectX SDK not available")
                return await self._fetch_projectx_fallback(credentials, broker_type)

            service = ProjectXSDKService(
                username=credentials.get("username", credentials.get("email", "")),
                api_key=credentials.get("api_key", ""),
                account_name=credentials.get("account_name")
            )

            if not await service.connect():
                logger.error("Failed to connect to ProjectX")
                return []

            try:
                # Get current account info
                account_info = await service.get_account_info()

                if account_info:
                    # Determine account type from name or metadata
                    account_name = account_info.get("name", "")
                    account_type = self._detect_projectx_account_type(account_name)

                    account = BrokerAccountInfo(
                        id=str(account_info.get("id", "")),  # Alphanumeric ID
                        name=account_name,
                        account_type=account_type,
                        balance=account_info.get("balance"),
                        equity=account_info.get("equity"),
                        currency=account_info.get("currency", "USD"),
                        broker_type=broker_type,
                        is_active=True,
                        metadata={
                            "margin": account_info.get("margin"),
                            "free_margin": account_info.get("free_margin"),
                        }
                    )
                    accounts.append(account)

            finally:
                await service.disconnect()

        except ImportError:
            logger.warning("ProjectX SDK service not available")
            accounts = await self._fetch_projectx_fallback(credentials, broker_type)
        except Exception as e:
            logger.error(f"Error fetching ProjectX accounts: {e}")

        return accounts

    def _detect_projectx_account_type(self, account_name: str) -> str:
        """Detect ProjectX account type from name."""
        name_lower = account_name.lower()
        if "eval" in name_lower or "challenge" in name_lower:
            return "evaluation"
        elif "express" in name_lower:
            return "express"
        elif "funded" in name_lower or "live" in name_lower:
            return "live"
        return "evaluation"  # Default for TopStep

    async def _fetch_projectx_fallback(
        self,
        credentials: Dict[str, Any],
        broker_type: str
    ) -> List[BrokerAccountInfo]:
        """Fallback account fetching for ProjectX using executor."""
        try:
            from app.brokers.projectx_executor import ProjectXExecutor

            # Pass credentials through constructor - no env var fallback
            executor = ProjectXExecutor(
                username=credentials.get("username"),
                api_key=credentials.get("api_key") or credentials.get("api_token"),
            )
            if not await executor.initialize():
                return []

            try:
                broker_accounts = await executor.get_accounts()
                return [
                    BrokerAccountInfo(
                        id=str(acc.id),
                        name=getattr(acc, 'name', f"Account {acc.id}"),
                        account_type=self._detect_projectx_account_type(
                            getattr(acc, 'name', '')
                        ),
                        balance=float(acc.balance) if hasattr(acc, 'balance') else None,
                        equity=float(acc.equity) if hasattr(acc, 'equity') else None,
                        currency=getattr(acc, 'currency', 'USD'),
                        broker_type=broker_type,
                        is_active=getattr(acc, 'is_active', True),
                    )
                    for acc in broker_accounts
                ]
            finally:
                await executor.disconnect()
        except Exception as e:
            logger.error(f"ProjectX fallback failed: {e}")
            return []

    async def fetch_tradovate_accounts(
        self,
        credentials: Dict[str, Any],
        broker_type: str = "tradovate"
    ) -> List[BrokerAccountInfo]:
        """
        Fetch available accounts from Tradovate API.

        Tradovate uses numeric account IDs and supports live/demo environments.

        Args:
            credentials: Dict with keys: access_token, environment, OR
                        user_id, password, app_id, etc. for password auth
            broker_type: Should be "tradovate"

        Returns:
            List of BrokerAccountInfo objects
        """
        accounts = []

        try:
            from app.brokers.tradovate_executor import TradovateExecutor

            # Determine auth mode
            access_token = credentials.get("access_token")
            environment = credentials.get("environment", "demo")

            if access_token:
                # Pass credentials through constructor - no env var fallback
                executor = TradovateExecutor(
                    access_token=access_token,
                    environment=environment
                )
            else:
                # No OAuth token - cannot proceed without credentials
                logger.warning("Tradovate requires access_token credentials")
                return []

            if not await executor.initialize():
                logger.error("Failed to initialize Tradovate executor")
                return []

            try:
                broker_accounts = await executor.get_accounts()

                for acc in broker_accounts:
                    account = BrokerAccountInfo(
                        id=str(acc.id),  # Numeric ID
                        name=getattr(acc, 'name', f"Tradovate {acc.id}"),
                        account_type="live" if getattr(acc, 'is_live', False) else "demo",
                        balance=float(acc.balance) if hasattr(acc, 'balance') else None,
                        equity=float(acc.equity) if hasattr(acc, 'equity') else None,
                        currency=getattr(acc, 'currency', 'USD'),
                        broker_type=broker_type,
                        is_active=getattr(acc, 'is_active', True),
                        leverage=getattr(acc, 'leverage', None),
                        metadata={
                            "margin": float(acc.margin) if hasattr(acc, 'margin') else None,
                            "free_margin": float(acc.free_margin) if hasattr(acc, 'free_margin') else None,
                        }
                    )
                    accounts.append(account)

            finally:
                await executor.disconnect()

        except Exception as e:
            logger.error(f"Error fetching Tradovate accounts: {e}")

        return accounts

    async def fetch_metaapi_accounts(
        self,
        credentials: Dict[str, Any],
        broker_type: str = "mt4"
    ) -> List[BrokerAccountInfo]:
        """
        Fetch connected accounts from MetaAPI SDK.

        MetaAPI uses UUID format account IDs and supports both MT4 and MT5 platforms.

        Args:
            credentials: Dict with keys: token, account_id (for single account) OR
                        token only (to list all provisioned accounts)
            broker_type: Should be "mt4" or "mt5"

        Returns:
            List of BrokerAccountInfo objects
        """
        accounts = []

        try:
            from app.services.metaapi_sdk_service import MetaAPISDKService, SDK_AVAILABLE

            if not SDK_AVAILABLE:
                logger.warning("MetaAPI SDK not available")
                return await self._fetch_metaapi_fallback(credentials, broker_type)

            token = credentials.get("token", credentials.get("api_key", ""))
            account_id = credentials.get("account_id", credentials.get("metaapi_account_id", ""))

            if not token:
                logger.error("MetaAPI token not provided")
                return []

            if account_id:
                # Fetch specific account info
                service = MetaAPISDKService(
                    token=token,
                    account_id=account_id
                )

                if not await service.connect():
                    logger.error("Failed to connect to MetaAPI")
                    return []

                try:
                    account_info = await service.get_account_info()

                    if account_info:
                        platform = account_info.get("platform", broker_type).lower()

                        account = BrokerAccountInfo(
                            id=account_id,  # UUID format
                            name=account_info.get("name", f"MetaAPI {account_id[:8]}"),
                            account_type="live" if "live" in account_info.get("type", "").lower() else "demo",
                            balance=account_info.get("balance"),
                            equity=account_info.get("equity"),
                            currency=account_info.get("currency", "USD"),
                            server=account_info.get("server", ""),
                            login=str(account_info.get("login", "")),
                            broker_type=platform if platform in ["mt4", "mt5"] else broker_type,
                            is_active=account_info.get("trade_allowed", True),
                            leverage=account_info.get("leverage"),
                            metadata={
                                "broker": account_info.get("broker", ""),
                                "margin": account_info.get("margin"),
                                "free_margin": account_info.get("free_margin"),
                                "margin_level": account_info.get("margin_level"),
                            }
                        )
                        accounts.append(account)

                finally:
                    await service.disconnect()
            else:
                # List all provisioned accounts via MetaAPI account management API
                accounts = await self._list_metaapi_accounts(token, broker_type)

        except ImportError:
            logger.warning("MetaAPI SDK service not available")
            accounts = await self._fetch_metaapi_fallback(credentials, broker_type)
        except Exception as e:
            logger.error(f"Error fetching MetaAPI accounts: {e}")

        return accounts

    async def _list_metaapi_accounts(
        self,
        token: str,
        broker_type: str
    ) -> List[BrokerAccountInfo]:
        """
        List all provisioned MetaAPI accounts.

        Uses MetaAPI account management API to list all accounts
        provisioned for the token.
        """
        accounts = []

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts",
                    headers={"auth-token": token},
                    timeout=30.0
                )

                if response.status_code != 200:
                    logger.error(f"MetaAPI account list failed: {response.text}")
                    return []

                accounts_data = response.json()

                for acc_data in accounts_data:
                    # Filter by platform type if specified
                    platform = acc_data.get("platform", "").lower()
                    if broker_type in ["mt4", "mt5"] and platform != broker_type:
                        continue

                    account = BrokerAccountInfo(
                        id=acc_data.get("_id", ""),  # UUID format
                        name=acc_data.get("name", ""),
                        account_type=acc_data.get("type", "demo").lower(),
                        balance=None,  # Not available in list API
                        equity=None,
                        currency=acc_data.get("baseCurrency", "USD"),
                        server=acc_data.get("server", ""),
                        login=str(acc_data.get("login", "")),
                        broker_type=platform if platform in ["mt4", "mt5"] else broker_type,
                        is_active=acc_data.get("state") == "DEPLOYED",
                        metadata={
                            "broker": acc_data.get("broker", ""),
                            "state": acc_data.get("state", ""),
                            "connection_status": acc_data.get("connectionStatus", ""),
                        }
                    )
                    accounts.append(account)

        except Exception as e:
            logger.error(f"Error listing MetaAPI accounts: {e}")

        return accounts

    async def _fetch_metaapi_fallback(
        self,
        credentials: Dict[str, Any],
        broker_type: str
    ) -> List[BrokerAccountInfo]:
        """Fallback account fetching for MetaAPI using executor."""
        try:
            # Pass credentials through constructor - no env var fallback
            metaapi_token = credentials.get("metaapi_token") or credentials.get("api_token")
            metaapi_account_id = credentials.get("metaapi_account_id")

            if not metaapi_token or not metaapi_account_id:
                logger.warning(f"{broker_type.upper()} requires metaapi_token and metaapi_account_id")
                return []

            if broker_type == "mt4":
                from app.brokers.mt4_executor import MT4Executor
                executor = MT4Executor(
                    metaapi_token=metaapi_token,
                    metaapi_account_id=metaapi_account_id,
                )
            else:
                from app.brokers.mt5_executor import MT5Executor
                executor = MT5Executor(
                    metaapi_token=metaapi_token,
                    metaapi_account_id=metaapi_account_id,
                )

            if not await executor.initialize():
                return []

            try:
                broker_accounts = await executor.get_accounts()
                return [
                    BrokerAccountInfo(
                        id=str(acc.id),
                        name=getattr(acc, 'name', f"Account {acc.id}"),
                        account_type="live" if getattr(acc, 'is_live', False) else "demo",
                        balance=float(acc.balance) if hasattr(acc, 'balance') else None,
                        equity=float(acc.equity) if hasattr(acc, 'equity') else None,
                        currency=getattr(acc, 'currency', 'USD'),
                        server=getattr(acc, 'server', None),
                        login=str(getattr(acc, 'login', '')),
                        broker_type=broker_type,
                        is_active=getattr(acc, 'is_active', True),
                    )
                    for acc in broker_accounts
                ]
            finally:
                await executor.disconnect()
        except Exception as e:
            logger.error(f"MetaAPI fallback failed: {e}")
            return []

    def to_dict(self, account: BrokerAccountInfo) -> Dict[str, Any]:
        """Convert BrokerAccountInfo to dictionary for API response."""
        return {
            "id": account.id,
            "name": account.name,
            "account_type": account.account_type,
            "balance": account.balance,
            "equity": account.equity,
            "currency": account.currency,
            "server": account.server,
            "login": account.login,
            "broker_type": account.broker_type,
            "is_active": account.is_active,
            "leverage": account.leverage,
            "metadata": account.metadata,
        }
