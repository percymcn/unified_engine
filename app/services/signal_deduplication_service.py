"""
Signal Deduplication Service

Prevents duplicate entry signals when a position is already open for the same symbol.
Protects users from accidental double entries (SIGNAL-06).
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
from sqlalchemy.orm import Session
import logging

from app.models.models import Position
from app.models.database_models import TradingAccount

logger = logging.getLogger(__name__)


class DeduplicationScope(str, Enum):
    """Scope of deduplication checks"""
    PER_ACCOUNT = "per_account"  # Check per individual account
    GLOBAL = "global"  # Check across all user's accounts


@dataclass
class DuplicateCheckResult:
    """Result of a duplicate entry check"""
    is_duplicate: bool
    reason: Optional[str] = None
    existing_position_id: Optional[int] = None
    existing_direction: Optional[str] = None  # "long" or "short"


class SignalDeduplicationService:
    """
    Detects and prevents duplicate entry signals.

    Checks if a position already exists for a symbol before allowing
    a new entry signal. Close/exit signals always bypass this check.

    Supports two scopes:
    - per_account: Only checks positions within the same account
    - global: Checks positions across all user's accounts
    """

    def __init__(self, db: Session):
        """
        Initialize deduplication service.

        Args:
            db: SQLAlchemy session
        """
        self.db = db

    def check_duplicate_entry(
        self,
        account_id: int,
        symbol: str,
        action: str,
        user_id: Optional[int] = None,
        scope: DeduplicationScope = DeduplicationScope.PER_ACCOUNT
    ) -> DuplicateCheckResult:
        """
        Check if signal is a duplicate entry for an already-open position.

        Args:
            account_id: Target account ID
            symbol: Trading symbol
            action: Signal action (buy, sell, close, etc.)
            user_id: User ID (required for global scope)
            scope: Deduplication scope (per_account or global)

        Returns:
            DuplicateCheckResult with is_duplicate flag and details
        """
        # Close/exit signals always bypass deduplication
        if self._is_close_action(action):
            logger.debug(f"Bypassing deduplication for close action: {action}")
            return DuplicateCheckResult(is_duplicate=False)

        # Get open positions based on scope
        if scope == DeduplicationScope.GLOBAL and user_id:
            positions = self._get_user_positions_for_symbol(user_id, symbol)
        else:
            positions = self._get_account_positions_for_symbol(account_id, symbol)

        if not positions:
            # No existing positions - not a duplicate
            return DuplicateCheckResult(is_duplicate=False)

        # Determine signal direction
        signal_direction = self._get_direction(action)

        # Check each position
        for position in positions:
            position_direction = self._get_position_direction(position)

            if position_direction == signal_direction:
                # Same direction = duplicate entry (pyramid attempt)
                logger.info(
                    f"Duplicate entry detected: {action} on {symbol} - "
                    f"position {position.id} already open in same direction"
                )
                return DuplicateCheckResult(
                    is_duplicate=True,
                    reason="position_already_open",
                    existing_position_id=position.id,
                    existing_direction=position_direction
                )

        # Opposite direction = reversal, allow it
        logger.debug(
            f"Reversal signal allowed: {action} on {symbol} - "
            f"existing position in opposite direction"
        )
        return DuplicateCheckResult(is_duplicate=False)

    def _is_close_action(self, action: str) -> bool:
        """Check if action is a close/exit action"""
        close_actions = {
            'close', 'close_all', 'flatten', 'exit',
            'close_long', 'close_short', 'close_buy', 'close_sell'
        }
        return action.lower() in close_actions

    def _get_direction(self, action: str) -> str:
        """Get signal direction from action"""
        action_lower = action.lower()
        if action_lower in ('buy', 'buy_limit', 'buy_stop', 'long'):
            return "long"
        elif action_lower in ('sell', 'sell_limit', 'sell_stop', 'short'):
            return "short"
        return "unknown"

    def _get_position_direction(self, position: Position) -> str:
        """Get direction from position type"""
        if hasattr(position, 'type'):
            pos_type = str(position.type).upper() if position.type else ""
            if 'BUY' in pos_type or 'LONG' in pos_type:
                return "long"
            elif 'SELL' in pos_type or 'SHORT' in pos_type:
                return "short"
        return "unknown"

    def _get_account_positions_for_symbol(
        self,
        account_id: int,
        symbol: str
    ) -> List[Position]:
        """Get open positions for account and symbol"""
        try:
            # Normalize symbol for comparison
            normalized_symbol = symbol.upper().replace(" ", "")

            positions = self.db.query(Position).filter(
                Position.account_id == account_id,
                Position.is_active == True
            ).all()

            # Filter by symbol (case-insensitive, handle variations)
            matching = []
            for pos in positions:
                pos_symbol = pos.symbol.upper().replace(" ", "") if pos.symbol else ""
                if pos_symbol == normalized_symbol or self._symbols_match(pos_symbol, normalized_symbol):
                    matching.append(pos)

            return matching

        except Exception as e:
            logger.error(f"Error fetching positions for account {account_id}: {e}")
            return []

    def _get_user_positions_for_symbol(
        self,
        user_id: int,
        symbol: str
    ) -> List[Position]:
        """Get open positions across all user's accounts for symbol"""
        try:
            # Get all user's account IDs
            accounts = self.db.query(TradingAccount).filter(
                TradingAccount.user_id == user_id,
                TradingAccount.is_active == True
            ).all()

            account_ids = [acc.id for acc in accounts]

            if not account_ids:
                return []

            # Normalize symbol
            normalized_symbol = symbol.upper().replace(" ", "")

            positions = self.db.query(Position).filter(
                Position.account_id.in_(account_ids),
                Position.is_active == True
            ).all()

            # Filter by symbol
            matching = []
            for pos in positions:
                pos_symbol = pos.symbol.upper().replace(" ", "") if pos.symbol else ""
                if pos_symbol == normalized_symbol or self._symbols_match(pos_symbol, normalized_symbol):
                    matching.append(pos)

            return matching

        except Exception as e:
            logger.error(f"Error fetching positions for user {user_id}: {e}")
            return []

    def _symbols_match(self, symbol1: str, symbol2: str) -> bool:
        """Check if two symbols match (handles suffixes like .pro, micro, etc.)"""
        # Strip common suffixes for comparison
        suffixes = ['.pro', '.raw', 'micro', '.mini', '_micro', '_mini']

        clean1 = symbol1
        clean2 = symbol2

        for suffix in suffixes:
            if clean1.lower().endswith(suffix):
                clean1 = clean1[:-len(suffix)]
            if clean2.lower().endswith(suffix):
                clean2 = clean2[:-len(suffix)]

        return clean1.upper() == clean2.upper()

    def get_open_positions(
        self,
        account_id: int,
        symbol: Optional[str] = None
    ) -> List[Position]:
        """
        Get open positions for account, optionally filtered by symbol.

        Args:
            account_id: Target account ID
            symbol: Optional symbol filter

        Returns:
            List of open Position objects
        """
        try:
            query = self.db.query(Position).filter(
                Position.account_id == account_id,
                Position.is_active == True
            )

            if symbol:
                # Case-insensitive symbol match
                positions = query.all()
                normalized = symbol.upper().replace(" ", "")
                return [p for p in positions if self._symbols_match(
                    p.symbol.upper() if p.symbol else "", normalized
                )]

            return query.all()

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
