"""
FuturesContractService

Domain service for futures contract management, including:
- Contract code parsing (NQH25 -> NQ + March + 2025)
- Expiration date calculation (third Friday for index futures)
- Active contract lookup
- Next contract determination
- Rollover detection
"""

import calendar
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from app.domain.entities.futures_contract import FuturesContract

logger = logging.getLogger(__name__)


@dataclass
class ParsedContract:
    """Result of parsing a futures contract code."""
    root: str          # "NQ", "ES", "CL"
    month_code: str    # "H", "M", "U", "Z"
    month: int         # 3, 6, 9, 12
    year: int          # 2025
    full_year: int     # 2025


class FuturesContractService:
    """
    Domain service for futures contract management.

    Handles contract code parsing, expiration calculation, and rollover detection
    for common futures contracts traded on CME and other exchanges.

    Usage:
        service = FuturesContractService()

        # Parse contract code
        parsed = service.parse_contract_code("NQH25")
        # ParsedContract(root="NQ", month_code="H", month=3, year=25, full_year=2025)

        # Calculate expiration
        expiration = service.calculate_expiration("NQ", 3, 2025)
        # date(2025, 3, 21)  # Third Friday of March 2025

        # Get next quarterly contract
        next_code = service.get_next_quarterly_code("NQH25")
        # "NQM25" (next quarter)
    """

    # CME month codes
    MONTH_CODES: Dict[str, int] = {
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

    # Reverse mapping
    MONTH_TO_CODE: Dict[int, str] = {v: k for k, v in MONTH_CODES.items()}

    # Common quarterly futures (trade H, M, U, Z only)
    QUARTERLY_ROOTS: List[str] = ['ES', 'NQ', 'YM', 'RTY', 'EMD']

    # Common monthly futures
    MONTHLY_ROOTS: List[str] = ['CL', 'GC', 'SI', 'NG']

    # Default rollover days before expiration
    DEFAULT_ROLLOVER_DAYS = 3

    def __init__(self, rollover_days: int = DEFAULT_ROLLOVER_DAYS):
        """
        Initialize the service.

        Args:
            rollover_days: Days before expiration to suggest rollover (default: 3)
        """
        self.rollover_days = rollover_days

    def parse_contract_code(self, code: str) -> Optional[ParsedContract]:
        """
        Parse a futures contract code into components.

        Supports formats:
        - NQH25: Symbol root + month code + 2-digit year
        - NQH2025: Symbol root + month code + 4-digit year
        - ESM5: Symbol root + month code + 1-digit year

        Args:
            code: Contract code like "NQH25", "ESM25", "CLZ25"

        Returns:
            ParsedContract with root, month info, and year, or None if invalid
        """
        if not code or len(code) < 3:
            return None

        code = code.upper().strip()

        # Try to find month code position
        month_code = None
        month_pos = -1

        # Look for month code from the end (typically before the year digits)
        for i in range(len(code) - 1, -1, -1):
            if code[i] in self.MONTH_CODES:
                month_code = code[i]
                month_pos = i
                break

        if month_code is None or month_pos < 1:
            logger.warning(f"Could not parse contract code: {code}")
            return None

        # Extract root (everything before month code)
        root = code[:month_pos]

        # Extract year (everything after month code)
        year_str = code[month_pos + 1:]

        if not year_str.isdigit():
            logger.warning(f"Invalid year in contract code: {code}")
            return None

        year_int = int(year_str)

        # Convert to full year
        if year_int < 100:
            # 2-digit year
            if year_int > 50:
                full_year = 1900 + year_int
            else:
                full_year = 2000 + year_int
        else:
            full_year = year_int

        return ParsedContract(
            root=root,
            month_code=month_code,
            month=self.MONTH_CODES[month_code],
            year=year_int if year_int < 100 else year_int % 100,
            full_year=full_year
        )

    def calculate_expiration(self, root: str, month: int, year: int) -> date:
        """
        Calculate expiration date for a futures contract.

        For equity index futures (ES, NQ, YM, RTY), expiration is typically
        the third Friday of the contract month. For other products, rules vary.

        Args:
            root: Symbol root (e.g., "NQ", "ES", "CL")
            month: Contract month (1-12)
            year: Full year (e.g., 2025)

        Returns:
            Expiration date
        """
        root_upper = root.upper()

        # Equity index futures: third Friday of contract month
        if root_upper in self.QUARTERLY_ROOTS or root_upper in ['MES', 'MNQ', 'M2K', 'MYM']:
            return self._third_friday(year, month)

        # Oil futures (CL): third business day before 25th
        if root_upper == 'CL':
            return self._business_days_before(year, month, 25, 3)

        # Gold futures (GC): third last business day of month before contract month
        if root_upper == 'GC':
            # Delivery is in contract month, last trading day is earlier
            prev_month = month - 1 if month > 1 else 12
            prev_year = year if month > 1 else year - 1
            return self._last_business_day(prev_year, prev_month)

        # Default: third Friday
        return self._third_friday(year, month)

    def calculate_last_trading_day(self, root: str, expiration: date) -> date:
        """
        Calculate last trading day for a contract.

        Usually the day before or same day as expiration, depending on product.

        Args:
            root: Symbol root
            expiration: Contract expiration date

        Returns:
            Last trading day
        """
        root_upper = root.upper()

        # For equity index futures, last trading is usually at expiration
        if root_upper in self.QUARTERLY_ROOTS:
            return expiration

        # For most others, last trading is day before expiration
        return expiration - timedelta(days=1)

    def calculate_rollover_date(self, expiration: date, days_before: int = None) -> date:
        """
        Calculate suggested rollover date.

        Args:
            expiration: Contract expiration date
            days_before: Days before expiration to rollover (defaults to service setting)

        Returns:
            Suggested rollover date
        """
        days = days_before if days_before is not None else self.rollover_days
        return expiration - timedelta(days=days)

    def get_next_quarterly_code(self, current_code: str) -> Optional[str]:
        """
        Get the next quarterly contract code.

        For quarterly contracts (ES, NQ, YM, RTY), returns the next
        quarterly month (H->M->U->Z->H).

        Args:
            current_code: Current contract code (e.g., "NQH25")

        Returns:
            Next quarterly contract code (e.g., "NQM25") or None if invalid
        """
        parsed = self.parse_contract_code(current_code)
        if not parsed:
            return None

        # Quarterly month sequence
        quarterly_months = ['H', 'M', 'U', 'Z']

        try:
            current_idx = quarterly_months.index(parsed.month_code)
        except ValueError:
            # Not a quarterly month, find next quarterly
            for i, m in enumerate(quarterly_months):
                if self.MONTH_CODES[m] > parsed.month:
                    next_month = m
                    next_year = parsed.year
                    return f"{parsed.root}{next_month}{next_year:02d}"
            # Wrap to next year H
            return f"{parsed.root}H{(parsed.year + 1) % 100:02d}"

        # Move to next quarterly month
        next_idx = (current_idx + 1) % 4
        next_month = quarterly_months[next_idx]

        # Year rollover if moving from Z to H
        if next_idx == 0:
            next_year = (parsed.year + 1) % 100
        else:
            next_year = parsed.year

        return f"{parsed.root}{next_month}{next_year:02d}"

    def get_next_monthly_code(self, current_code: str) -> Optional[str]:
        """
        Get the next monthly contract code.

        Args:
            current_code: Current contract code

        Returns:
            Next monthly contract code or None if invalid
        """
        parsed = self.parse_contract_code(current_code)
        if not parsed:
            return None

        # Next month
        next_month_num = (parsed.month % 12) + 1
        next_year = parsed.year if next_month_num > 1 else (parsed.year + 1) % 100

        next_month_code = self.MONTH_TO_CODE[next_month_num]

        return f"{parsed.root}{next_month_code}{next_year:02d}"

    def get_next_contract_code(self, current_code: str) -> Optional[str]:
        """
        Get the next contract code based on contract type.

        Automatically determines if contract is quarterly or monthly.

        Args:
            current_code: Current contract code

        Returns:
            Next contract code or None if invalid
        """
        parsed = self.parse_contract_code(current_code)
        if not parsed:
            return None

        # Quarterly roots use quarterly sequence
        if parsed.root in self.QUARTERLY_ROOTS:
            return self.get_next_quarterly_code(current_code)

        # Otherwise use monthly sequence
        return self.get_next_monthly_code(current_code)

    def build_contract(self, code: str) -> Optional[FuturesContract]:
        """
        Build a FuturesContract entity from a contract code.

        Args:
            code: Contract code (e.g., "NQH25")

        Returns:
            FuturesContract entity or None if invalid code
        """
        parsed = self.parse_contract_code(code)
        if not parsed:
            return None

        expiration = self.calculate_expiration(parsed.root, parsed.month, parsed.full_year)
        last_trading = self.calculate_last_trading_day(parsed.root, expiration)
        rollover = self.calculate_rollover_date(expiration)
        next_code = self.get_next_contract_code(code)

        return FuturesContract(
            symbol_root=parsed.root,
            contract_code=code.upper(),
            month_code=parsed.month_code,
            year=parsed.full_year,
            expiration_date=expiration,
            last_trading_day=last_trading,
            rollover_date=rollover,
            is_active=True,
            next_contract=next_code
        )

    def check_rollover_needed(self, contract: FuturesContract) -> bool:
        """
        Check if a contract needs rollover.

        Returns True if current date is at or past the suggested rollover date.

        Args:
            contract: FuturesContract to check

        Returns:
            True if rollover is needed
        """
        return contract.needs_rollover

    def get_contracts_expiring_soon(
        self,
        contracts: List[FuturesContract],
        days: int = 7
    ) -> List[FuturesContract]:
        """
        Filter contracts expiring within N days.

        Args:
            contracts: List of contracts to filter
            days: Number of days threshold

        Returns:
            List of contracts expiring within N days
        """
        cutoff = date.today() + timedelta(days=days)
        return [
            c for c in contracts
            if c.is_active and c.expiration_date <= cutoff
        ]

    # Private helper methods

    def _third_friday(self, year: int, month: int) -> date:
        """Get the third Friday of a month."""
        # Get first day of month
        first_day = date(year, month, 1)

        # Find first Friday
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_until_friday)

        # Third Friday is 14 days after first Friday
        return first_friday + timedelta(days=14)

    def _business_days_before(self, year: int, month: int, day: int, count: int) -> date:
        """Get N business days before a specific date."""
        target = date(year, month, min(day, calendar.monthrange(year, month)[1]))
        business_days = 0

        while business_days < count:
            target -= timedelta(days=1)
            if target.weekday() < 5:  # Monday = 0, Friday = 4
                business_days += 1

        return target

    def _last_business_day(self, year: int, month: int) -> date:
        """Get last business day of a month."""
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        while last_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
            last_day -= timedelta(days=1)

        return last_day
