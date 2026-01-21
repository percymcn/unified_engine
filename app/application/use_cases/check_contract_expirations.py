"""
Check Contract Expirations Use Case

Scheduled task that checks for expiring contracts and sends
notifications to users who are trading them.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.services.contract_tracker import ContractTracker, ExpiringPosition
from app.domain.services.futures_contract_service import FuturesContractService
from app.models.models import FuturesContract as FuturesContractModel
from app.models.models import UserContractPosition

logger = logging.getLogger(__name__)


@dataclass
class RolloverNotification:
    """Notification data for contract rollover."""
    user_id: int
    account_id: int
    contract_code: str
    symbol_root: str
    expiration_date: date
    rollover_date: date
    suggested_rollover: date
    next_contract: Optional[str]
    days_until_expiration: int
    notification_type: str  # "warning", "urgent", "critical"
    message: str
    sent_at: Optional[datetime] = None


class CheckContractExpirationsUseCase:
    """
    Use case for checking contract expirations and sending notifications.

    This should be run as a scheduled task (daily) to alert users about
    upcoming contract expirations and suggest rollovers.

    Notification schedule:
    - 7 days before: Initial warning
    - 3 days before: Urgent reminder
    - 1 day before: Critical alert

    Usage:
        use_case = CheckContractExpirationsUseCase(db_session)
        notifications = await use_case.execute()
    """

    # Days before expiration to send notifications
    NOTIFICATION_DAYS = [7, 3, 1]

    def __init__(self, db: Session, notification_service=None):
        """
        Initialize the use case.

        Args:
            db: SQLAlchemy database session
            notification_service: Optional notification service for sending alerts
        """
        self.db = db
        self._tracker = ContractTracker(db)
        self._futures_service = FuturesContractService()
        self._notification_service = notification_service

    async def execute(self) -> List[RolloverNotification]:
        """
        Check all users for expiring contracts and create notifications.

        Returns:
            List of notifications created
        """
        notifications = []

        try:
            # Get all contracts expiring in next 7 days
            expiring_contracts = await self._tracker.get_all_expiring_contracts(days=7)

            if not expiring_contracts:
                logger.debug("No contracts expiring in the next 7 days")
                return notifications

            for contract in expiring_contracts:
                # Find users trading this contract
                users = await self._tracker.get_users_trading(contract.contract_code)

                for user_data in users:
                    notification = await self._create_notification(
                        user_id=user_data["user_id"],
                        account_id=user_data["account_id"],
                        contract=contract
                    )

                    if notification:
                        notifications.append(notification)

                        # Send via notification service if available
                        if self._notification_service:
                            await self._send_notification(notification)

            # Cleanup: deactivate expired contracts
            await self._tracker.deactivate_expired_contracts()

            logger.info(f"Created {len(notifications)} rollover notifications")
            return notifications

        except Exception as e:
            logger.error(f"Error checking contract expirations: {e}")
            return notifications

    async def _create_notification(
        self,
        user_id: int,
        account_id: int,
        contract: FuturesContractModel
    ) -> Optional[RolloverNotification]:
        """Create a notification for an expiring contract."""
        try:
            # Get expiration date
            exp_date = contract.expiration_date
            if hasattr(exp_date, 'date'):
                exp_date = exp_date.date()

            roll_date = contract.rollover_date
            if hasattr(roll_date, 'date'):
                roll_date = roll_date.date()

            days_until = (exp_date - date.today()).days

            # Skip if not on notification schedule
            if days_until not in self.NOTIFICATION_DAYS and days_until > 7:
                return None

            # Determine notification type and message
            if days_until <= 1:
                notification_type = "critical"
                message = (
                    f"CRITICAL: Your {contract.contract_code} contract expires TOMORROW! "
                    f"Roll to {contract.next_contract or 'next contract'} immediately to avoid "
                    f"forced liquidation."
                )
            elif days_until <= 3:
                notification_type = "urgent"
                message = (
                    f"URGENT: Your {contract.contract_code} contract expires in {days_until} days "
                    f"({exp_date.strftime('%b %d')}). "
                    f"Recommended: Roll to {contract.next_contract or 'next contract'} now."
                )
            else:
                notification_type = "warning"
                message = (
                    f"Heads up: Your {contract.contract_code} contract expires in {days_until} days "
                    f"({exp_date.strftime('%b %d')}). "
                    f"Consider rolling to {contract.next_contract or 'next contract'} soon."
                )

            return RolloverNotification(
                user_id=user_id,
                account_id=account_id,
                contract_code=contract.contract_code,
                symbol_root=contract.symbol_root,
                expiration_date=exp_date,
                rollover_date=roll_date,
                suggested_rollover=roll_date,
                next_contract=contract.next_contract,
                days_until_expiration=days_until,
                notification_type=notification_type,
                message=message,
                sent_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error creating notification for {contract.contract_code}: {e}")
            return None

    async def _send_notification(self, notification: RolloverNotification) -> bool:
        """Send notification via notification service."""
        try:
            if not self._notification_service:
                return False

            # Import here to avoid circular imports
            from app.models.enhanced_models import NotificationType, NotificationChannel

            # Map notification type to priority
            priority_map = {
                "critical": "urgent",
                "urgent": "high",
                "warning": "normal"
            }

            await self._notification_service.create_notification(
                user_id=notification.user_id,
                notification_type=NotificationType.ALERT,
                title=f"Contract Expiration: {notification.contract_code}",
                message=notification.message,
                channel=NotificationChannel.IN_APP,
                priority=priority_map.get(notification.notification_type, "normal"),
                metadata={
                    "contract_code": notification.contract_code,
                    "symbol_root": notification.symbol_root,
                    "expiration_date": notification.expiration_date.isoformat(),
                    "next_contract": notification.next_contract,
                    "days_until_expiration": notification.days_until_expiration,
                    "notification_type": notification.notification_type
                },
                action_url="/dashboard/settings/accounts",
                db=self.db
            )

            logger.debug(
                f"Sent {notification.notification_type} notification to user "
                f"{notification.user_id} for {notification.contract_code}"
            )
            return True

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False

    async def check_single_user(self, user_id: int) -> List[RolloverNotification]:
        """
        Check expiring contracts for a single user.

        Useful for on-demand checking (e.g., when user logs in).

        Args:
            user_id: User ID to check

        Returns:
            List of notifications for this user
        """
        try:
            expiring = await self._tracker.get_expiring_positions(user_id, days=7)
            notifications = []

            for position in expiring:
                # Get contract record
                contract = self.db.query(FuturesContractModel).filter(
                    FuturesContractModel.contract_code == position.contract_code
                ).first()

                if not contract:
                    continue

                notification = await self._create_notification(
                    user_id=user_id,
                    account_id=position.account_id,
                    contract=contract
                )

                if notification:
                    notifications.append(notification)

            return notifications

        except Exception as e:
            logger.error(f"Error checking user {user_id} contracts: {e}")
            return []


async def run_scheduled_check(db: Session, notification_service=None) -> int:
    """
    Convenience function for running scheduled expiration check.

    Can be called from a scheduler (e.g., APScheduler, Celery).

    Args:
        db: Database session
        notification_service: Optional notification service

    Returns:
        Number of notifications sent
    """
    use_case = CheckContractExpirationsUseCase(db, notification_service)
    notifications = await use_case.execute()
    return len(notifications)
