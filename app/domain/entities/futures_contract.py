"""
FuturesContract Domain Entity

Represents a futures contract with expiration tracking and rollover support.
Used for TopStep/ProjectX and other futures brokers to handle contract
lifecycle management.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from app.domain.exceptions import ValidationError


@dataclass
class FuturesContract:
    """
    Domain entity representing a futures contract.

    Tracks contract specifications including expiration dates, rollover timing,
    and the relationship to the next contract in the chain.

    Contract Code Format:
        - NQH25 = Nasdaq (NQ) + March (H) + 2025 (25)
        - Month codes: F(Jan), G(Feb), H(Mar), J(Apr), K(May), M(Jun),
                      N(Jul), Q(Aug), U(Sep), V(Oct), X(Nov), Z(Dec)

    Attributes:
        id: Unique identifier (None for new contracts)
        symbol_root: Base symbol without contract month (e.g., "NQ", "ES")
        contract_code: Full contract code (e.g., "NQH25")
        month_code: Single letter month code (e.g., "H" for March)
        year: Contract year (e.g., 2025)
        expiration_date: Date when contract expires
        last_trading_day: Last day contract can be traded (usually before expiration)
        rollover_date: Suggested date to roll to next contract
        is_active: Whether contract is currently tradeable
        next_contract: Code of the next contract in sequence (e.g., "NQM25")
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """
    symbol_root: str
    contract_code: str
    month_code: str
    year: int
    expiration_date: date
    last_trading_day: date
    rollover_date: date
    id: Optional[int] = None
    is_active: bool = True
    next_contract: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # CME month codes mapping
    MONTH_CODES = {
        'F': 1,   # January
        'G': 2,   # February
        'H': 3,   # March
        'J': 4,   # April
        'K': 5,   # May
        'M': 6,   # June
        'N': 7,   # July
        'Q': 8,   # August
        'U': 9,   # September
        'V': 10,  # October
        'X': 11,  # November
        'Z': 12,  # December
    }

    # Reverse mapping for month to code
    MONTH_TO_CODE = {v: k for k, v in MONTH_CODES.items()}

    # Quarterly contract months (front months for index futures)
    QUARTERLY_MONTHS = {'H', 'M', 'U', 'Z'}  # Mar, Jun, Sep, Dec

    def __post_init__(self):
        """Validate and normalize on creation."""
        self.validate()
        # Normalize
        self.symbol_root = self.symbol_root.upper().strip()
        self.contract_code = self.contract_code.upper().strip()
        self.month_code = self.month_code.upper().strip()
        if self.next_contract:
            self.next_contract = self.next_contract.upper().strip()

    def validate(self) -> None:
        """Validate contract invariants."""
        if not self.symbol_root or len(self.symbol_root.strip()) == 0:
            raise ValidationError(
                "Symbol root cannot be empty",
                field="symbol_root"
            )

        if len(self.symbol_root) > 10:
            raise ValidationError(
                "Symbol root cannot exceed 10 characters",
                field="symbol_root",
                context={"length": len(self.symbol_root)}
            )

        if not self.contract_code or len(self.contract_code.strip()) == 0:
            raise ValidationError(
                "Contract code cannot be empty",
                field="contract_code"
            )

        if len(self.contract_code) > 20:
            raise ValidationError(
                "Contract code cannot exceed 20 characters",
                field="contract_code",
                context={"length": len(self.contract_code)}
            )

        month_upper = self.month_code.upper().strip()
        if month_upper not in self.MONTH_CODES:
            raise ValidationError(
                f"Invalid month code: {self.month_code}",
                field="month_code",
                context={"valid_codes": list(self.MONTH_CODES.keys())}
            )

        if self.year < 2000 or self.year > 2100:
            raise ValidationError(
                f"Year must be between 2000 and 2100, got {self.year}",
                field="year",
                context={"year": self.year}
            )

        if self.rollover_date > self.expiration_date:
            raise ValidationError(
                "Rollover date cannot be after expiration date",
                field="rollover_date",
                context={
                    "rollover_date": str(self.rollover_date),
                    "expiration_date": str(self.expiration_date)
                }
            )

        if self.last_trading_day > self.expiration_date:
            raise ValidationError(
                "Last trading day cannot be after expiration date",
                field="last_trading_day",
                context={
                    "last_trading_day": str(self.last_trading_day),
                    "expiration_date": str(self.expiration_date)
                }
            )

    @property
    def month(self) -> int:
        """Get numeric month from month code."""
        return self.MONTH_CODES.get(self.month_code.upper(), 0)

    @property
    def days_until_expiration(self) -> int:
        """Days remaining until contract expires."""
        return (self.expiration_date - date.today()).days

    @property
    def days_until_rollover(self) -> int:
        """Days remaining until suggested rollover."""
        return (self.rollover_date - date.today()).days

    @property
    def is_expiring_soon(self) -> bool:
        """Check if contract expires within 7 days."""
        return 0 <= self.days_until_expiration <= 7

    @property
    def needs_rollover(self) -> bool:
        """Check if contract is at or past rollover date."""
        return date.today() >= self.rollover_date

    @property
    def is_expired(self) -> bool:
        """Check if contract has expired."""
        return date.today() > self.expiration_date

    @property
    def is_quarterly(self) -> bool:
        """Check if this is a quarterly contract (H, M, U, Z)."""
        return self.month_code.upper() in self.QUARTERLY_MONTHS

    def deactivate(self) -> None:
        """Mark contract as no longer active."""
        self.is_active = False
        self.updated_at = datetime.utcnow()

    def set_next_contract(self, next_code: str) -> None:
        """Set the next contract code."""
        if not next_code or len(next_code.strip()) == 0:
            raise ValidationError(
                "Next contract code cannot be empty",
                field="next_contract"
            )
        self.next_contract = next_code.upper().strip()
        self.updated_at = datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"FuturesContract(id={self.id}, "
            f"code='{self.contract_code}', "
            f"root='{self.symbol_root}', "
            f"expires={self.expiration_date}, "
            f"active={self.is_active})"
        )
