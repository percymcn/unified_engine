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

            # Get broker adapter
            broker = self._brokers.get(account.broker)
            if broker is None:
                raise BrokerConnectionError(f"No adapter for broker: {account.broker}")

            # Connect to broker
            connected = await broker.connect()
            if not connected:
                raise BrokerConnectionError("Failed to connect to broker")

            # Update account state
            account.connect()

            # Get account info from broker
            info = await broker.get_account_info()
            account.update_balance(Money(Decimal(str(info.get("balance", 0))), account.currency))
            account.update_equity(Money(Decimal(str(info.get("equity", 0))), account.currency))
            account.update_margin(Money(Decimal(str(info.get("margin", 0))), account.currency))

            # Save updated account
            await self._account_repo.save(account)

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
            raise BrokerConnectionError(f"No adapter for broker: {account.broker}")

        # Sync account info
        info = await broker.get_account_info()
        account.update_balance(Money(Decimal(str(info.get("balance", 0))), account.currency))
        account.update_equity(Money(Decimal(str(info.get("equity", 0))), account.currency))
        account.update_margin(Money(Decimal(str(info.get("margin", 0))), account.currency))

        # Get positions and orders count
        positions = await broker.get_positions()
        orders = await broker.get_orders()

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
