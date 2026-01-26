"""
Signal Domain Entity

Encapsulates trading signal business logic including validation,
state transitions, and processing lifecycle.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from decimal import Decimal

from app.domain.enums import SignalSource, SignalAction, SignalStatus
from app.domain.value_objects import SignalId, Symbol, Volume, Price, StopLoss, TakeProfit, AccountId
from app.domain.exceptions import SignalValidationError, BusinessRuleViolation


@dataclass
class Signal:
    """
    Domain entity representing a trading signal.

    A signal is an instruction to execute a trading action.
    It encapsulates validation and processing logic.
    """
    id: SignalId
    source: SignalSource
    symbol: Symbol
    action: SignalAction
    volume: Optional[Volume] = None
    price: Optional[Price] = None
    stop_loss: Optional[StopLoss] = None
    take_profit: Optional[TakeProfit] = None
    target_accounts: List[AccountId] = field(default_factory=list)
    status: SignalStatus = SignalStatus.PENDING
    comment: Optional[str] = None
    strategy_id: Optional[str] = None
    strategy_name: Optional[str] = None
    raw_payload: Optional[dict] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_details: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate signal invariants"""
        if self.action in (SignalAction.BUY, SignalAction.SELL):
            if self.volume is None:
                raise SignalValidationError("Volume required for BUY/SELL signals")

        if self.stop_loss and self.take_profit:
            # Validate SL/TP make sense for the action
            if self.action == SignalAction.BUY:
                if self.price and self.stop_loss.price.value >= self.price.value:
                    raise SignalValidationError("Stop loss must be below entry for BUY")
            elif self.action == SignalAction.SELL:
                if self.price and self.stop_loss.price.value <= self.price.value:
                    raise SignalValidationError("Stop loss must be above entry for SELL")

    def mark_processing(self) -> None:
        """Mark signal as being processed"""
        if self.status != SignalStatus.PENDING:
            raise BusinessRuleViolation(
                "cannot_process_signal",
                f"Cannot process signal in {self.status} status"
            )
        self.status = SignalStatus.PROCESSING

    def mark_processed(self) -> None:
        """Mark signal as successfully processed"""
        if self.status != SignalStatus.PROCESSING:
            raise BusinessRuleViolation(
                "cannot_complete_signal",
                f"Cannot complete signal in {self.status} status"
            )
        self.status = SignalStatus.PROCESSED
        self.processed_at = datetime.utcnow()

    def mark_failed(self, error: str) -> None:
        """Mark signal as failed"""
        self.status = SignalStatus.FAILED
        self.error_message = error
        self.processed_at = datetime.utcnow()

    def mark_skipped(self, reason: str) -> None:
        """Mark signal as skipped"""
        self.status = SignalStatus.SKIPPED
        self.error_message = reason
        self.processed_at = datetime.utcnow()

    def add_target_account(self, account_id: AccountId) -> None:
        """Add account to signal targets"""
        if account_id not in self.target_accounts:
            self.target_accounts.append(account_id)

    @property
    def is_pending(self) -> bool:
        return self.status == SignalStatus.PENDING

    @property
    def is_processed(self) -> bool:
        return self.status == SignalStatus.PROCESSED

    @property
    def is_failed(self) -> bool:
        return self.status == SignalStatus.FAILED
