"""
ContractTracker Service

Tracks which futures contracts users are trading per account.
Monitors expiring positions and suggests rollovers.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.models import FuturesContract as FuturesContractModel
from app.models.models import UserContractPosition
from app.domain.services.futures_contract_service import FuturesContractService

logger = logging.getLogger(__name__)


@dataclass
class ExpiringPosition:
    """Information about a position that is expiring soon."""
    user_id: int
    account_id: int
    contract_code: str
    symbol_root: str
    expiration_date: date
    days_until_expiration: int
    rollover_date: date
    days_until_rollover: int
    next_contract: Optional[str]
    last_traded_at: Optional[datetime]


@dataclass
class RolloverSuggestion:
    """Rollover action suggestion for an expiring position."""
    user_id: int
    account_id: int
    current_contract: str
    next_contract: str
    expiration_date: date
    days_until_expiration: int
    urgency: str  # "normal", "urgent", "critical"
    message: str


class ContractTracker:
    """
    Service for tracking user contract positions and detecting expirations.

    Monitors which contracts users are actively trading and sends alerts
    when contracts approach expiration. Suggests rollover to the next contract.

    Usage:
        tracker = ContractTracker(db_session)

        # Update position when user trades a contract
        await tracker.update_position(user_id=1, account_id=5, contract_code="NQH25")

        # Get expiring positions for a user
        expiring = await tracker.get_expiring_positions(user_id=1, days=7)

        # Get rollover suggestions
        suggestion = await tracker.suggest_rollover(position)
    """

    def __init__(self, db: Session):
        """
        Initialize the tracker.

        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self._futures_service = FuturesContractService()

    async def update_position(
        self,
        user_id: int,
        account_id: int,
        contract_code: str
    ) -> Optional[UserContractPosition]:
        """
        Update tracking when user trades a futures contract.

        Creates a new position record if one doesn't exist, or updates
        the last_traded_at timestamp if it does.

        Args:
            user_id: User ID
            account_id: Account ID
            contract_code: Contract code (e.g., "NQH25")

        Returns:
            Updated or created position, or None on error
        """
        try:
            contract_code = contract_code.upper().strip()

            # Parse contract to get root
            parsed = self._futures_service.parse_contract_code(contract_code)
            if not parsed:
                logger.warning(f"Could not parse contract code: {contract_code}")
                return None

            # Check if position already exists
            existing = self.db.query(UserContractPosition).filter(
                UserContractPosition.user_id == user_id,
                UserContractPosition.account_id == account_id,
                UserContractPosition.contract_code == contract_code
            ).first()

            if existing:
                # Update last traded time
                existing.last_traded_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(existing)
                logger.debug(f"Updated position tracking: {contract_code} for user {user_id}")
                return existing

            # Create new position record
            position = UserContractPosition(
                user_id=user_id,
                account_id=account_id,
                contract_code=contract_code,
                symbol_root=parsed.root,
                last_traded_at=datetime.utcnow()
            )

            self.db.add(position)
            self.db.commit()
            self.db.refresh(position)

            logger.info(f"Created position tracking: {contract_code} for user {user_id}")

            # Ensure contract exists in futures_contracts table
            await self._ensure_contract_exists(contract_code)

            return position

        except Exception as e:
            logger.error(f"Error updating contract position: {e}")
            self.db.rollback()
            return None

    async def _ensure_contract_exists(self, contract_code: str) -> None:
        """Ensure the contract exists in the futures_contracts table."""
        try:
            existing = self.db.query(FuturesContractModel).filter(
                FuturesContractModel.contract_code == contract_code.upper()
            ).first()

            if existing:
                return

            # Build contract from code
            contract = self._futures_service.build_contract(contract_code)
            if not contract:
                return

            # Create database record
            db_contract = FuturesContractModel(
                symbol_root=contract.symbol_root,
                contract_code=contract.contract_code,
                month_code=contract.month_code,
                year=contract.year,
                expiration_date=datetime.combine(contract.expiration_date, datetime.min.time()),
                last_trading_day=datetime.combine(contract.last_trading_day, datetime.min.time()),
                rollover_date=datetime.combine(contract.rollover_date, datetime.min.time()),
                is_active=contract.is_active,
                next_contract=contract.next_contract
            )

            self.db.add(db_contract)
            self.db.commit()
            logger.info(f"Created futures contract record: {contract_code}")

        except Exception as e:
            logger.warning(f"Could not create contract record for {contract_code}: {e}")
            self.db.rollback()

    async def get_expiring_positions(
        self,
        user_id: int,
        days: int = 7
    ) -> List[ExpiringPosition]:
        """
        Get user's positions that are expiring within N days.

        Args:
            user_id: User ID
            days: Number of days to look ahead

        Returns:
            List of expiring positions with details
        """
        try:
            # Get user's tracked positions
            positions = self.db.query(UserContractPosition).filter(
                UserContractPosition.user_id == user_id
            ).all()

            if not positions:
                return []

            expiring = []
            cutoff = date.today() + timedelta(days=days)

            for pos in positions:
                # Get contract details
                contract = self.db.query(FuturesContractModel).filter(
                    FuturesContractModel.contract_code == pos.contract_code
                ).first()

                if not contract:
                    # Try to build contract if not in DB
                    built = self._futures_service.build_contract(pos.contract_code)
                    if built:
                        exp_date = built.expiration_date
                        roll_date = built.rollover_date
                        next_code = built.next_contract
                    else:
                        continue
                else:
                    exp_date = contract.expiration_date.date() if hasattr(contract.expiration_date, 'date') else contract.expiration_date
                    roll_date = contract.rollover_date.date() if hasattr(contract.rollover_date, 'date') else contract.rollover_date
                    next_code = contract.next_contract

                # Check if expiring within window
                if exp_date <= cutoff:
                    days_until_exp = (exp_date - date.today()).days
                    days_until_roll = (roll_date - date.today()).days

                    expiring.append(ExpiringPosition(
                        user_id=pos.user_id,
                        account_id=pos.account_id,
                        contract_code=pos.contract_code,
                        symbol_root=pos.symbol_root,
                        expiration_date=exp_date,
                        days_until_expiration=days_until_exp,
                        rollover_date=roll_date,
                        days_until_rollover=days_until_roll,
                        next_contract=next_code,
                        last_traded_at=pos.last_traded_at
                    ))

            # Sort by days until expiration
            expiring.sort(key=lambda x: x.days_until_expiration)

            return expiring

        except Exception as e:
            logger.error(f"Error getting expiring positions: {e}")
            return []

    async def get_users_trading(self, contract_code: str) -> List[Dict[str, Any]]:
        """
        Get all users trading a specific contract.

        Args:
            contract_code: Contract code to look up

        Returns:
            List of dicts with user_id and account_id
        """
        try:
            positions = self.db.query(UserContractPosition).filter(
                UserContractPosition.contract_code == contract_code.upper()
            ).all()

            return [
                {
                    "user_id": pos.user_id,
                    "account_id": pos.account_id,
                    "last_traded_at": pos.last_traded_at
                }
                for pos in positions
            ]

        except Exception as e:
            logger.error(f"Error getting users trading {contract_code}: {e}")
            return []

    async def suggest_rollover(
        self,
        position: ExpiringPosition
    ) -> Optional[RolloverSuggestion]:
        """
        Generate a rollover suggestion for an expiring position.

        Args:
            position: Expiring position information

        Returns:
            Rollover suggestion or None if not applicable
        """
        if not position.next_contract:
            return None

        # Determine urgency based on days until expiration
        if position.days_until_expiration <= 1:
            urgency = "critical"
            message = (
                f"URGENT: {position.contract_code} expires TOMORROW! "
                f"Roll to {position.next_contract} immediately."
            )
        elif position.days_until_expiration <= 3:
            urgency = "urgent"
            message = (
                f"{position.contract_code} expires in {position.days_until_expiration} days. "
                f"Recommend rolling to {position.next_contract} now."
            )
        else:
            urgency = "normal"
            message = (
                f"{position.contract_code} expires on {position.expiration_date.strftime('%b %d')}. "
                f"Consider rolling to {position.next_contract}."
            )

        return RolloverSuggestion(
            user_id=position.user_id,
            account_id=position.account_id,
            current_contract=position.contract_code,
            next_contract=position.next_contract,
            expiration_date=position.expiration_date,
            days_until_expiration=position.days_until_expiration,
            urgency=urgency,
            message=message
        )

    async def get_all_expiring_contracts(
        self,
        days: int = 7
    ) -> List[FuturesContractModel]:
        """
        Get all contracts expiring within N days.

        Args:
            days: Number of days to look ahead

        Returns:
            List of expiring contract records
        """
        try:
            cutoff = datetime.combine(
                date.today() + timedelta(days=days),
                datetime.max.time()
            )

            contracts = self.db.query(FuturesContractModel).filter(
                FuturesContractModel.is_active == True,
                FuturesContractModel.expiration_date <= cutoff
            ).order_by(FuturesContractModel.expiration_date).all()

            return contracts

        except Exception as e:
            logger.error(f"Error getting expiring contracts: {e}")
            return []

    async def deactivate_expired_contracts(self) -> int:
        """
        Mark all expired contracts as inactive.

        Returns:
            Number of contracts deactivated
        """
        try:
            today = datetime.combine(date.today(), datetime.min.time())

            count = self.db.query(FuturesContractModel).filter(
                FuturesContractModel.is_active == True,
                FuturesContractModel.expiration_date < today
            ).update({"is_active": False})

            self.db.commit()

            if count > 0:
                logger.info(f"Deactivated {count} expired contracts")

            return count

        except Exception as e:
            logger.error(f"Error deactivating expired contracts: {e}")
            self.db.rollback()
            return 0

    async def cleanup_old_positions(self, days_old: int = 90) -> int:
        """
        Remove position tracking records older than N days.

        Args:
            days_old: Remove positions not traded in this many days

        Returns:
            Number of positions removed
        """
        try:
            cutoff = datetime.utcnow() - timedelta(days=days_old)

            count = self.db.query(UserContractPosition).filter(
                UserContractPosition.last_traded_at < cutoff
            ).delete()

            self.db.commit()

            if count > 0:
                logger.info(f"Cleaned up {count} old position tracking records")

            return count

        except Exception as e:
            logger.error(f"Error cleaning up old positions: {e}")
            self.db.rollback()
            return 0
