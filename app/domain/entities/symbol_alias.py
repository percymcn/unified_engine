"""
SymbolAlias Domain Entity

Represents a mapping between TradingView symbols and broker-specific formats.
Enables symbol normalization and alias resolution for cross-broker trading.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.domain.exceptions import ValidationError


@dataclass
class SymbolAlias:
    """
    Domain entity representing a symbol alias mapping.

    Maps TradingView symbols (e.g., "US30") to broker-specific formats
    (e.g., "US30.pro" for TradeLocker, "YM" for Tradovate).

    Attributes:
        id: Unique identifier (None for new aliases)
        user_id: Owner of this alias mapping
        source_symbol: TradingView symbol (normalized uppercase)
        broker_type: Target broker (tradelocker, mt5, tradovate, etc.)
        target_symbol: Broker's symbol format
        is_auto_detected: True if system-generated via fuzzy matching
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    user_id: int
    source_symbol: str
    broker_type: str
    target_symbol: str
    id: Optional[int] = None
    is_auto_detected: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate and normalize on creation"""
        self.validate()
        # Normalize source symbol to uppercase
        self.source_symbol = self.source_symbol.upper().strip()
        # Normalize broker type to lowercase
        self.broker_type = self.broker_type.lower().strip()
        # Preserve target symbol case (some brokers are case-sensitive)
        self.target_symbol = self.target_symbol.strip()

    def validate(self) -> None:
        """Validate alias invariants"""
        if not self.source_symbol or len(self.source_symbol.strip()) == 0:
            raise ValidationError(
                "Source symbol cannot be empty",
                field="source_symbol"
            )

        if len(self.source_symbol) > 50:
            raise ValidationError(
                "Source symbol cannot exceed 50 characters",
                field="source_symbol",
                context={"length": len(self.source_symbol)}
            )

        if not self.broker_type or len(self.broker_type.strip()) == 0:
            raise ValidationError(
                "Broker type cannot be empty",
                field="broker_type"
            )

        valid_brokers = {"tradelocker", "mt4", "mt5", "tradovate", "projectx", "topstep"}
        if self.broker_type.lower().strip() not in valid_brokers:
            raise ValidationError(
                f"Invalid broker type: {self.broker_type}",
                field="broker_type",
                context={"valid_brokers": list(valid_brokers)}
            )

        if not self.target_symbol or len(self.target_symbol.strip()) == 0:
            raise ValidationError(
                "Target symbol cannot be empty",
                field="target_symbol"
            )

        if len(self.target_symbol) > 50:
            raise ValidationError(
                "Target symbol cannot exceed 50 characters",
                field="target_symbol",
                context={"length": len(self.target_symbol)}
            )

        if self.user_id is None or self.user_id <= 0:
            raise ValidationError(
                "User ID must be a positive integer",
                field="user_id",
                context={"user_id": self.user_id}
            )

    def update_target(self, new_target: str) -> None:
        """Update the target symbol mapping"""
        if not new_target or len(new_target.strip()) == 0:
            raise ValidationError(
                "Target symbol cannot be empty",
                field="target_symbol"
            )
        self.target_symbol = new_target.strip()
        self.is_auto_detected = False  # User override
        self.updated_at = datetime.utcnow()

    def mark_auto_detected(self) -> None:
        """Mark this alias as auto-detected by the system"""
        self.is_auto_detected = True
        self.updated_at = datetime.utcnow()

    @property
    def is_user_defined(self) -> bool:
        """Check if this alias was created by user (not auto-detected)"""
        return not self.is_auto_detected

    def __repr__(self) -> str:
        return (
            f"SymbolAlias(id={self.id}, "
            f"source='{self.source_symbol}', "
            f"broker='{self.broker_type}', "
            f"target='{self.target_symbol}', "
            f"auto={self.is_auto_detected})"
        )
