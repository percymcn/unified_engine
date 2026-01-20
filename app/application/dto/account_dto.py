"""
Account DTOs - Input/Output contracts for account use cases.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.domain.enums import BrokerType, AccountType


@dataclass(frozen=True)
class AccountDTO:
    """Read-only account representation"""
    id: str
    user_id: int
    broker: BrokerType
    account_type: AccountType
    balance: Decimal
    equity: Decimal
    margin: Decimal
    free_margin: Decimal
    leverage: int
    currency: str
    is_active: bool
    is_connected: bool
    server: Optional[str] = None
    last_sync: Optional[datetime] = None


@dataclass(frozen=True)
class AccountSummaryDTO:
    """Lightweight account summary for lists"""
    id: str
    broker: BrokerType
    balance: Decimal
    equity: Decimal
    is_connected: bool


@dataclass(frozen=True)
class GetAccountsRequest:
    """Request for listing user accounts"""
    user_id: int
    broker: Optional[BrokerType] = None
    active_only: bool = True


@dataclass(frozen=True)
class GetAccountsResponse:
    """Response containing account list"""
    accounts: List[AccountSummaryDTO]
    total: int


@dataclass(frozen=True)
class ConnectAccountRequest:
    """Request to connect an account to broker"""
    account_id: str


@dataclass(frozen=True)
class ConnectAccountResponse:
    """Response for account connection"""
    account_id: str
    is_connected: bool
    balance: Optional[Decimal] = None
    equity: Optional[Decimal] = None
    error: Optional[str] = None


@dataclass(frozen=True)
class SyncAccountRequest:
    """Request to sync account data from broker"""
    account_id: str


@dataclass(frozen=True)
class SyncAccountResponse:
    """Response for account sync"""
    account_id: str
    balance: Decimal
    equity: Decimal
    margin: Decimal
    free_margin: Decimal
    synced_at: datetime
    positions_count: int = 0
    orders_count: int = 0
