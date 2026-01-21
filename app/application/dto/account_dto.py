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
    oauth_tokens: Optional[dict] = None  # For OAuth-based brokers (e.g., Tradovate)


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


@dataclass(frozen=True)
class CreateAccountRequest:
    """Request to create a new account"""
    user_id: int
    broker: BrokerType
    account_type: AccountType
    credentials: dict  # Will be encrypted via CredentialRepository
    account_id: str  # Broker account ID
    currency: str = "USD"
    leverage: int = 100
    server: Optional[str] = None
    # Symbol detection data (from connection test)
    detected_format: Optional[dict] = None  # From test-connection response
    symbol_map: Optional[dict] = None  # From test-connection response
    sample_symbols: Optional[List[str]] = None  # From test-connection response


@dataclass(frozen=True)
class CreateAccountResponse:
    """Response for account creation"""
    account_id: str
    broker: BrokerType
    is_active: bool
    error: Optional[str] = None
    auto_aliases_created: int = 0  # Number of auto-detected aliases created


@dataclass(frozen=True)
class UpdateAccountRequest:
    """Request to update account"""
    account_id: str
    credentials: Optional[dict] = None  # Will be re-encrypted if provided
    leverage: Optional[int] = None
    is_active: Optional[bool] = None


@dataclass(frozen=True)
class UpdateAccountResponse:
    """Response for account update"""
    account_id: str
    updated: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class DeleteAccountRequest:
    """Request to delete account"""
    account_id: str
    user_id: int  # For ownership verification


@dataclass(frozen=True)
class DeleteAccountResponse:
    """Response for account deletion"""
    account_id: str
    deleted: bool
    error: Optional[str] = None


@dataclass(frozen=True)
class TestConnectionRequest:
    """Request to test broker connection before saving account"""
    broker: BrokerType
    credentials: dict  # Credential fields vary by broker


@dataclass(frozen=True)
class TestConnectionResponse:
    """Response for connection test"""
    success: bool
    status: str  # "connected" | "failed" | "timeout"
    message: str
    details: Optional[dict] = None
    # Symbol detection fields (populated on successful connection)
    detected_format: Optional[dict] = None  # {"suffix": ".pro", "case": "upper", "confidence": 0.9}
    symbol_map: Optional[dict] = None  # {"EURUSD": "EURUSD.pro", "US30": "US30.pro"}
    sample_symbols: Optional[List[str]] = None  # First 20 symbols for UI preview
