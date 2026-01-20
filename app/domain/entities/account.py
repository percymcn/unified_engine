"""
Account Domain Entity

Manages account balance, equity, margin, and trading operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from decimal import Decimal

from app.domain.enums import BrokerType, AccountType
from app.domain.value_objects import AccountId, Money
from app.domain.exceptions import InsufficientBalanceError, AccountDisabledError, BusinessRuleViolation


@dataclass
class Account:
    """
    Domain entity representing a trading account.

    Manages balance, equity, margin calculations.
    """
    id: AccountId
    user_id: int
    broker: BrokerType
    account_type: AccountType
    balance: Money
    equity: Money
    margin: Money = field(default_factory=lambda: Money(Decimal("0")))
    leverage: int = 100
    is_active: bool = True
    is_connected: bool = False
    currency: str = "USD"
    server: Optional[str] = None
    last_sync: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def free_margin(self) -> Decimal:
        """Calculate free margin = equity - margin (can be negative during margin calls)"""
        return self.equity.amount - self.margin.amount

    def update_balance(self, new_balance: Money) -> None:
        """Update account balance (from broker sync)"""
        if not self.is_active:
            raise AccountDisabledError(self.id.value)
        object.__setattr__(self, 'balance', new_balance)
        object.__setattr__(self, 'last_sync', datetime.utcnow())

    def update_equity(self, new_equity: Money) -> None:
        """Update account equity (balance + unrealized P&L)"""
        if not self.is_active:
            raise AccountDisabledError(self.id.value)
        object.__setattr__(self, 'equity', new_equity)
        object.__setattr__(self, 'last_sync', datetime.utcnow())

    def update_margin(self, new_margin: Money) -> None:
        """Update used margin"""
        object.__setattr__(self, 'margin', new_margin)

    def check_margin_for_trade(self, required_margin: Money) -> bool:
        """Check if account has sufficient margin for a trade"""
        return self.free_margin >= required_margin.amount

    def reserve_margin(self, amount: Money) -> None:
        """Reserve margin for a new trade"""
        if not self.check_margin_for_trade(amount):
            raise InsufficientBalanceError(
                required=float(amount.amount),
                available=float(self.free_margin),
                account_id=self.id.value
            )
        new_margin = Money(self.margin.amount + amount.amount, self.currency)
        self.update_margin(new_margin)

    def release_margin(self, amount: Money) -> None:
        """Release margin when trade closes"""
        new_margin = Money(max(Decimal("0"), self.margin.amount - amount.amount), self.currency)
        self.update_margin(new_margin)

    def realize_pnl(self, pnl: Money) -> None:
        """Apply realized P&L to balance"""
        new_balance = Money(self.balance.amount + pnl.amount, self.currency)
        object.__setattr__(self, 'balance', new_balance)
        new_equity = Money(self.equity.amount + pnl.amount, self.currency)
        object.__setattr__(self, 'equity', new_equity)

    def deactivate(self) -> None:
        """Deactivate account"""
        object.__setattr__(self, 'is_active', False)
        object.__setattr__(self, 'is_connected', False)

    def activate(self) -> None:
        """Activate account"""
        object.__setattr__(self, 'is_active', True)

    def connect(self) -> None:
        """Mark account as connected to broker"""
        if not self.is_active:
            raise AccountDisabledError(self.id.value)
        object.__setattr__(self, 'is_connected', True)
        object.__setattr__(self, 'last_sync', datetime.utcnow())

    def disconnect(self) -> None:
        """Mark account as disconnected"""
        object.__setattr__(self, 'is_connected', False)

    @property
    def margin_level(self) -> Optional[Decimal]:
        """Calculate margin level percentage (equity / margin * 100)"""
        if self.margin.amount == 0:
            return None
        return (self.equity.amount / self.margin.amount) * Decimal("100")

    @property
    def is_margin_call(self) -> bool:
        """Check if account is in margin call (< 100% margin level)"""
        level = self.margin_level
        return level is not None and level < 100

    @property
    def is_stop_out(self) -> bool:
        """Check if account is at stop out level (< 50% margin level)"""
        level = self.margin_level
        return level is not None and level < 50
