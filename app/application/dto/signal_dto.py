"""
Signal DTOs - Input/Output contracts for signal use cases.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from decimal import Decimal
from datetime import datetime

from app.domain.enums import SignalSource, SignalAction, SignalStatus


@dataclass(frozen=True)
class ProcessSignalRequest:
    """Input DTO for processing a trading signal"""
    source: SignalSource
    symbol: str
    action: SignalAction
    volume: Optional[Decimal] = None
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    target_account_ids: List[str] = field(default_factory=list)
    comment: Optional[str] = None
    strategy_id: Optional[str] = None
    strategy_name: Optional[str] = None
    raw_payload: Optional[dict] = None

    def __post_init__(self):
        # Validation
        if self.action in (SignalAction.BUY, SignalAction.SELL):
            if self.volume is None or self.volume <= 0:
                raise ValueError("Volume required and must be positive for BUY/SELL")
        if self.symbol is None or not self.symbol.strip():
            raise ValueError("Symbol is required")


@dataclass(frozen=True)
class ProcessSignalResponse:
    """Output DTO for signal processing result"""
    signal_id: str
    status: SignalStatus
    executions: int = 0
    errors: List[str] = field(default_factory=list)
    processed_at: Optional[datetime] = None


@dataclass(frozen=True)
class SignalDTO:
    """Read-only signal representation"""
    id: str
    source: SignalSource
    symbol: str
    action: SignalAction
    status: SignalStatus
    volume: Optional[Decimal] = None
    price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    comment: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


@dataclass(frozen=True)
class SignalListRequest:
    """Request for listing signals"""
    status: Optional[SignalStatus] = None
    user_id: Optional[int] = None
    limit: int = 100
    offset: int = 0


@dataclass(frozen=True)
class SignalListResponse:
    """Response containing signal list"""
    signals: List[SignalDTO]
    total: int
    limit: int
    offset: int
