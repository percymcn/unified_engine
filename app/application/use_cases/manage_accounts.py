"""
Account Management Use Cases

Use cases for account queries and connection management.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
from decimal import Decimal

from app.domain.entities.account import Account
from app.domain.value_objects import AccountId, Money
from app.domain.enums import BrokerType
from app.domain.ports.broker_port import BrokerPort
from app.domain.ports.repository_port import AccountRepository, PositionRepository, OrderRepository
from app.domain.exceptions import AccountNotFoundError, AccountDisabledError, BrokerConnectionError

from app.application.dto.account_dto import (
    AccountDTO,
    AccountSummaryDTO,
    GetAccountsRequest,
    GetAccountsResponse,
    ConnectAccountRequest,
    ConnectAccountResponse,
    SyncAccountRequest,
    SyncAccountResponse,
    CreateAccountRequest,
    CreateAccountResponse,
    UpdateAccountRequest,
    UpdateAccountResponse,
    DeleteAccountRequest,
    DeleteAccountResponse,
)

logger = logging.getLogger(__name__)


class GetAccountsUseCase:
    """Use case for listing user accounts"""

    def __init__(self, account_repository: AccountRepository):
        self._account_repo = account_repository

    async def execute(self, request: GetAccountsRequest) -> GetAccountsResponse:
        """Get accounts for user with optional filtering"""
        if request.broker:
            all_accounts = await self._account_repo.get_by_broker(request.broker)
            accounts = [a for a in all_accounts if a.user_id == request.user_id]
        else:
            accounts = await self._account_repo.get_by_user(request.user_id)

        if request.active_only:
            accounts = [a for a in accounts if a.is_active]

        summaries = [self._to_summary_dto(a) for a in accounts]

        return GetAccountsResponse(
            accounts=summaries,
            total=len(summaries),
        )

    def _to_summary_dto(self, account: Account) -> AccountSummaryDTO:
        return AccountSummaryDTO(
            id=account.id.value,
            broker=account.broker,
            balance=account.balance.amount,
            equity=account.equity.amount,
            is_connected=account.is_connected,
        )


class GetAccountUseCase:
    """Use case for getting a single account"""

    def __init__(self, account_repository: AccountRepository):
        self._account_repo = account_repository

    async def execute(self, account_id: str) -> Optional[AccountDTO]:
        """Get account by ID"""
        account = await self._account_repo.get_by_id(AccountId(account_id))
        if account is None:
            return None
        return self._to_dto(account)

    def _to_dto(self, account: Account) -> AccountDTO:
        return AccountDTO(
            id=account.id.value,
            user_id=account.user_id,
            broker=account.broker,
            account_type=account.account_type,
            balance=account.balance.amount,
            equity=account.equity.amount,
            margin=account.margin.amount,
            free_margin=account.free_margin,
            leverage=account.leverage,
            currency=account.currency,
            is_active=account.is_active,
            is_connected=account.is_connected,
            server=account.server,
            last_sync=account.last_sync,
        )


class ConnectAccountUseCase:
    """Use case for connecting account to broker"""

    def __init__(
        self,
        account_repository: AccountRepository,
        brokers: Dict[BrokerType, BrokerPort],
    ):
        self._account_repo = account_repository
        self._brokers = brokers

    async def execute(self, request: ConnectAccountRequest) -> ConnectAccountResponse:
        """Connect account to its broker"""
        try:
            # Get account
            account = await self._account_repo.get_by_id(AccountId(request.account_id))
            if account is None:
                raise AccountNotFoundError(request.account_id)

            if not account.is_active:
                raise AccountDisabledError("Account is disabled")

            # Handle Tradovate OAuth specially
            if account.broker == BrokerType.TRADOVATE and request.oauth_tokens:
                from app.infrastructure.adapters.tradovate_adapter import TradovateAdapter
                from app.services.tradovate_token_service import TradovateTokenService
                from app.db.database import SessionLocal
                from app.models.database_models import TradingAccount

                # Store OAuth tokens
                db = SessionLocal()
                try:
                    db_account = db.query(TradingAccount).filter(
                        TradingAccount.id == int(request.account_id)
                    ).first()
                    if db_account:
                        service = TradovateTokenService(db)
                        service.store_tokens(
                            account=db_account,
                            access_token=request.oauth_tokens["access_token"],
                            refresh_token=request.oauth_tokens.get("refresh_token"),
                            expires_in=request.oauth_tokens.get("expires_in", 3600),
                            environment=request.oauth_tokens.get("environment", "demo"),
                        )
                finally:
                    db.close()

                # Create adapter with OAuth
                broker = TradovateAdapter(
                    account_id=int(request.account_id),
                    access_token=request.oauth_tokens["access_token"],
                    environment=request.oauth_tokens.get("environment", "demo"),
                )
            else:
                # Get broker adapter from pre-configured pool
                broker = self._brokers.get(account.broker)
                if broker is None:
                    raise BrokerConnectionError(
                        broker=str(account.broker.value) if hasattr(account.broker, 'value') else str(account.broker),
                        message=f"No adapter for broker: {account.broker}",
                        account_id=request.account_id
                    )

            # Connect to broker
            connected = await broker.connect()
            if not connected:
                raise BrokerConnectionError(
                    broker=str(account.broker.value) if hasattr(account.broker, 'value') else str(account.broker),
                    message="Failed to connect to broker",
                    account_id=request.account_id
                )

            # Update account state
            account.connect()

            # Get account info from broker
            info = await broker.get_account_info()
            account.update_balance(Money(Decimal(str(info.get("balance", 0))), account.currency))
            account.update_equity(Money(Decimal(str(info.get("equity", 0))), account.currency))
            account.update_margin(Money(Decimal(str(info.get("margin", 0))), account.currency))

            # Save updated account
            await self._account_repo.save(account)
            
            # Generate webhook key if missing (Patch 1.2.1)
            try:
                from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository
                if isinstance(self._account_repo, SQLAlchemyAccountRepository):
                    import secrets
                    from app.models.database_models import TradingAccount
                    from sqlalchemy import select
                    session = self._account_repo._session
                    stmt = select(TradingAccount).where(TradingAccount.id == int(account.id.value))
                    result = await session.execute(stmt)
                    orm_account = result.scalar_one_or_none()
                    if orm_account and not orm_account.webhook_key:
                        broker_slug = account.broker.value.lower()
                        short_random = secrets.token_urlsafe(6)[:8]
                        orm_account.webhook_key = f"webhook_{broker_slug}_user{account.user_id}_{short_random}"
                        await session.commit()
                        logger.info(f"Generated webhook key on connect for account {account.id.value}: {orm_account.webhook_key[:20]}...")
            except Exception as e:
                # Don't fail connection if webhook key generation fails
                logger.warning(f"Failed to generate webhook key on connect (non-critical): {e}")

            return ConnectAccountResponse(
                account_id=account.id.value,
                is_connected=True,
                balance=account.balance.amount,
                equity=account.equity.amount,
            )

        except AccountNotFoundError as e:
            return ConnectAccountResponse(
                account_id=request.account_id,
                is_connected=False,
                error=f"Account not found: {request.account_id}",
            )
        except AccountDisabledError as e:
            return ConnectAccountResponse(
                account_id=request.account_id,
                is_connected=False,
                error=str(e),
            )
        except BrokerConnectionError as e:
            return ConnectAccountResponse(
                account_id=request.account_id,
                is_connected=False,
                error=str(e),
            )
        except Exception as e:
            logger.exception(f"Unexpected error connecting account: {e}")
            return ConnectAccountResponse(
                account_id=request.account_id,
                is_connected=False,
                error=f"Internal error: {str(e)}",
            )


class SyncAccountUseCase:
    """Use case for syncing account data from broker"""

    def __init__(
        self,
        account_repository: AccountRepository,
        position_repository: PositionRepository,
        order_repository: OrderRepository,
        brokers: Dict[BrokerType, BrokerPort],
    ):
        self._account_repo = account_repository
        self._position_repo = position_repository
        self._order_repo = order_repository
        self._brokers = brokers

    async def execute(self, request: SyncAccountRequest) -> SyncAccountResponse:
        """Sync account data from broker"""
        # Get account
        account = await self._account_repo.get_by_id(AccountId(request.account_id))
        if account is None:
            raise AccountNotFoundError(request.account_id)

        if not account.is_connected:
            raise AccountDisabledError("Account is not connected")

        # Get broker adapter
        broker = self._brokers.get(account.broker)
        if broker is None:
            raise BrokerConnectionError(
                broker=str(account.broker.value) if hasattr(account.broker, 'value') else str(account.broker),
                message=f"No adapter for broker: {account.broker}",
                account_id=str(request.account_id)
            )

        logger.info(f"Broker type: {type(broker).__name__}, account: {account.broker}")

        # Sync account info
        # get_account_info returns Account Pydantic model (not dict)
        # Some adapters require account_id, some don't - try without params first
        try:
            # Try without account_id first (most adapters)
            logger.info("Calling get_account_info() without args")
            info = await broker.get_account_info()
            logger.info(f"Got info: {info}")
        except TypeError as e:
            logger.warning(f"TypeError: {e}, trying with account_id")
            # Fallback for adapters that require account_id (use server field which often has broker account ID)
            broker_account_id = account.server or str(account.id.value)
            info = await broker.get_account_info(broker_account_id)

        if info:
            # Account is a Pydantic model with attributes, not dict
            account.update_balance(Money(Decimal(str(info.balance)), account.currency))
            account.update_equity(Money(Decimal(str(info.equity)), account.currency))
            account.update_margin(Money(Decimal(str(info.margin)), account.currency))
            # Update free_margin if available
            if hasattr(info, 'free_margin') and info.free_margin is not None:
                account.free_margin = Decimal(str(info.free_margin))
        else:
            logger.warning(f"get_account_info returned None for account {account.id.value}")

        # Get positions and orders count
        try:
            try:
                positions = await broker.get_positions()
            except TypeError:
                # Fallback with account ID
                broker_account_id = account.server or str(account.id.value)
                positions = await broker.get_positions(broker_account_id)
        except Exception as e:
            logger.warning(f"Could not get positions: {e}")
            positions = []

        try:
            try:
                orders = await broker.get_orders()
            except TypeError:
                # Fallback with account ID
                broker_account_id = account.server or str(account.id.value)
                orders = await broker.get_orders(broker_account_id)
        except Exception as e:
            logger.warning(f"Could not get orders: {e}")
            orders = []

        # Save updated account
        await self._account_repo.save(account)

        return SyncAccountResponse(
            account_id=account.id.value,
            balance=account.balance.amount,
            equity=account.equity.amount,
            margin=account.margin.amount,
            free_margin=account.free_margin,
            synced_at=datetime.utcnow(),
            positions_count=len(positions),
            orders_count=len(orders),
        )


class CreateAccountUseCase:
    """Use case for creating a new account with encrypted credentials"""

    def __init__(
        self,
        account_repository: AccountRepository,
        credential_repository,  # CredentialRepository from infrastructure
        symbol_alias_repository=None,  # Optional: for auto-alias creation
    ):
        self._account_repo = account_repository
        self._credential_repo = credential_repository
        self._alias_repo = symbol_alias_repository

    async def execute(self, request: CreateAccountRequest) -> CreateAccountResponse:
        """Create new account with encrypted credentials and auto-detected aliases"""
        try:
            import uuid

            # Create domain account entity
            # Use request.account_id (broker account ID) for account_number
            # Generate UUID for domain ID (will be mapped to database integer ID)
            account = Account(
                id=AccountId(str(uuid.uuid4())),
                user_id=request.user_id,
                broker=request.broker,
                account_type=request.account_type,
                balance=Money(Decimal("0"), request.currency),
                equity=Money(Decimal("0"), request.currency),
                margin=Money(Decimal("0"), request.currency),
                leverage=request.leverage,
                currency=request.currency,
                server=request.server or request.account_id,  # Use broker account_id as server/account_name if server not provided
                is_active=True,
                is_connected=False,
            )

            # Save account to repository
            saved_account = await self._account_repo.save(account)
            
            # Generate webhook key for this broker connection (Patch 1.2.1)
            # We need to update the ORM model directly after save
            # This is a workaround since domain entity doesn't include webhook_key
            try:
                from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository
                if isinstance(self._account_repo, SQLAlchemyAccountRepository):
                    import secrets
                    from app.models.database_models import TradingAccount
                    from sqlalchemy import select
                    # Access session via repository
                    session = self._account_repo._session
                    # Use account_number to find the account (broker account ID) instead of trying to convert UUID to int
                    # After save, saved_account.id.value should be the integer DB ID as string, but to be safe,
                    # we'll query by account_number which contains the broker account ID
                    account_number = request.account_id if request.account_id else saved_account.id.value
                    stmt = select(TradingAccount).where(
                        TradingAccount.account_number == account_number,
                        TradingAccount.user_id == request.user_id
                    ).order_by(TradingAccount.created_at.desc()).limit(1)
                    result = await session.execute(stmt)
                    orm_account = result.scalar_one_or_none()
                    if orm_account and not orm_account.webhook_key:
                        broker_slug = request.broker.value.lower()
                        short_random = secrets.token_urlsafe(6)[:8]
                        orm_account.webhook_key = f"webhook_{broker_slug}_user{request.user_id}_{short_random}"
                        await session.commit()
                        logger.info(f"Generated webhook key for account {orm_account.id}: {orm_account.webhook_key[:20]}...")
            except Exception as e:
                # Don't fail account creation if webhook key generation fails
                logger.warning(f"Failed to generate webhook key (non-critical): {e}")

            # Store credentials encrypted in separate table
            credential_id = str(uuid.uuid4())
            credential_data = {
                "account_id": request.account_id,
                **request.credentials,
            }

            # Include OAuth tokens if provided
            if hasattr(request, 'oauth_tokens') and request.oauth_tokens:
                credential_data.update(request.oauth_tokens)

            # Store credentials first (without metaapi_account_id)
            # For MT4/MT5, provisioning happens async via background job
            # to avoid HTTP timeouts during the 1-3 minute provisioning process
            await self._credential_repo.create(
                credential_id=credential_id,
                user_id=request.user_id,
                name=f"{request.broker.value} - {request.account_id}",
                credential_type="broker",
                service=request.broker.value,
                credential_data=credential_data,
                description=f"Credentials for {request.broker.value} account {request.account_id}",
            )
            
            # Auto-create default account settings
            try:
                from app.models.database_models import AccountSettings, TradingAccount
                from sqlalchemy import select
                
                # Get the newly created ORM account
                session = self._account_repo._session
                stmt = select(TradingAccount).where(
                    TradingAccount.account_number == request.account_id,
                    TradingAccount.user_id == request.user_id
                ).order_by(TradingAccount.created_at.desc()).limit(1)
                result = await session.execute(stmt)
                orm_account = result.scalar_one_or_none()
                
                if orm_account:
                    # Check if settings already exist
                    settings_stmt = select(AccountSettings).where(
                        AccountSettings.account_id == orm_account.id
                    )
                    settings_result = await session.execute(settings_stmt)
                    existing_settings = settings_result.scalar_one_or_none()
                    
                    if not existing_settings:
                        # Create default settings
                        default_settings = AccountSettings(
                            account_id=orm_account.id,
                            position_sizing_mode="fixed",
                            fixed_lot_size=0.01,
                            percent_of_balance=1.0,
                            percent_of_equity=1.0,
                            risk_percent_per_trade=1.0,
                            max_open_positions=10,
                            max_daily_trades=50,
                            max_risk_per_day=10.0,
                            is_trading_enabled=True,
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        session.add(default_settings)
                        await session.commit()
                        logger.info(f"Created default account settings for account {orm_account.id}")
            except Exception as e:
                logger.warning(f"Failed to create default account settings (non-critical): {e}")

            try:
                await self._account_repo._session.commit()
            except Exception as commit_error:
                logger.warning(f"Failed to commit account creation transaction: {commit_error}")

            # Create auto-detected aliases if symbol_map provided
            auto_aliases_created = 0
            if request.symbol_map and self._alias_repo:
                try:
                    auto_aliases_created = await self._alias_repo.bulk_create_auto_aliases(
                        user_id=request.user_id,
                        broker_type=request.broker.value,
                        symbol_map=request.symbol_map
                    )
                    logger.info(
                        f"Created {auto_aliases_created} auto-detected aliases "
                        f"for {request.broker.value} account"
                    )
                except Exception as e:
                    # Don't fail account creation if alias creation fails
                    logger.warning(f"Failed to create auto-aliases: {e}")

            logger.info(f"Account created: {saved_account.id.value} with encrypted credentials")

            return CreateAccountResponse(
                account_id=saved_account.id.value,
                broker=saved_account.broker,
                is_active=saved_account.is_active,
                auto_aliases_created=auto_aliases_created,
            )

        except Exception as e:
            logger.exception(f"Failed to create account: {e}")
            return CreateAccountResponse(
                account_id="",
                broker=request.broker,
                is_active=False,
                error=str(e),
            )

    async def _provision_metaapi_account(
        self,
        credentials: Dict,
        platform: str,
        account_name: str,
    ) -> Optional[str]:
        """
        Provision MetaAPI account from broker credentials.

        Args:
            credentials: Dict with login, password, server
            platform: "mt4" or "mt5"
            account_name: Friendly name for the account

        Returns:
            MetaAPI account_id if successful, None otherwise
        """
        try:
            from app.services.metaapi_provisioning_service import get_provisioning_service

            service = get_provisioning_service()
            if not service:
                logger.warning("MetaAPI provisioning service not configured - skipping auto-provision")
                return None

            login = credentials.get("login")
            password = credentials.get("password")
            server = credentials.get("server")

            if not all([login, password, server]):
                logger.warning("Missing MT4/MT5 credentials (login, password, server) - skipping auto-provision")
                return None

            result = await service.provision_account(
                login=login,
                password=password,
                server=server,
                platform=platform,
                name=account_name,
            )

            return result.get("account_id")

        except Exception as e:
            logger.error(f"MetaAPI provisioning failed: {e}")
            # Don't fail account creation if provisioning fails
            # User can retry via account settings later
            return None


class UpdateAccountUseCase:
    """Use case for updating account"""

    def __init__(
        self,
        account_repository: AccountRepository,
        credential_repository,  # CredentialRepository from infrastructure
    ):
        self._account_repo = account_repository
        self._credential_repo = credential_repository

    async def execute(self, request: UpdateAccountRequest) -> UpdateAccountResponse:
        """Update account metadata and optionally re-encrypt credentials"""
        try:
            # Get account
            account = await self._account_repo.get_by_id(AccountId(request.account_id))
            if account is None:
                return UpdateAccountResponse(
                    account_id=request.account_id,
                    updated=False,
                    error="Account not found",
                )

            # Update account fields
            if request.leverage is not None:
                object.__setattr__(account, 'leverage', request.leverage)

            if request.is_active is not None:
                if request.is_active:
                    account.activate()
                else:
                    account.deactivate()

            # Save account
            await self._account_repo.save(account)

            # Update credentials if provided
            if request.credentials is not None:
                # Find credential for this account/broker
                credentials = await self._credential_repo.list_by_user(
                    user_id=account.user_id,
                    service=account.broker.value,
                    active_only=True,
                )

                if credentials:
                    # Rotate the first matching credential
                    await self._credential_repo.rotate(
                        credential_id=credentials[0].id,
                        new_credential_data=request.credentials,
                    )

            logger.info(f"Account updated: {request.account_id}")

            return UpdateAccountResponse(
                account_id=request.account_id,
                updated=True,
            )

        except Exception as e:
            logger.exception(f"Failed to update account: {e}")
            return UpdateAccountResponse(
                account_id=request.account_id,
                updated=False,
                error=str(e),
            )


class DeleteAccountUseCase:
    """Use case for deleting account and its credentials"""

    def __init__(
        self,
        account_repository: AccountRepository,
        credential_repository,  # CredentialRepository from infrastructure
    ):
        self._account_repo = account_repository
        self._credential_repo = credential_repository

    async def execute(self, request: DeleteAccountRequest) -> DeleteAccountResponse:
        """Delete account and soft-delete its credentials"""
        try:
            # Get account
            account = await self._account_repo.get_by_id(AccountId(request.account_id))
            if account is None:
                return DeleteAccountResponse(
                    account_id=request.account_id,
                    deleted=False,
                    error="Account not found",
                )

            # Verify ownership
            if account.user_id != request.user_id:
                return DeleteAccountResponse(
                    account_id=request.account_id,
                    deleted=False,
                    error="Unauthorized",
                )

            # Soft delete credentials first
            credentials = await self._credential_repo.list_by_user(
                user_id=account.user_id,
                service=account.broker.value,
                active_only=True,
            )

            for cred in credentials:
                await self._credential_repo.soft_delete(cred.id)

            # Delete account
            await self._account_repo.delete(AccountId(request.account_id))

            logger.info(f"Account deleted: {request.account_id}")

            return DeleteAccountResponse(
                account_id=request.account_id,
                deleted=True,
            )

        except Exception as e:
            logger.exception(f"Failed to delete account: {e}")
            return DeleteAccountResponse(
                account_id=request.account_id,
                deleted=False,
                error=str(e),
            )
