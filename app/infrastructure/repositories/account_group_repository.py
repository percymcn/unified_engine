"""
Account Group Repository

SQLAlchemy implementation for account group persistence.
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database_models import AccountGroup, TradingAccount

logger = logging.getLogger(__name__)


class AccountGroupRepository:
    """Repository for account group operations"""

    def __init__(self, session: Session):
        self._session = session

    async def create(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        color: str = "#6366f1",
        icon: str = "folder",
    ) -> AccountGroup:
        """Create a new account group."""
        group = AccountGroup(
            user_id=user_id,
            name=name,
            description=description,
            color=color,
            icon=icon,
            is_active=True,
        )
        self._session.add(group)
        self._session.commit()
        self._session.refresh(group)
        logger.info(f"Created account group: {group.id} ({name}) for user {user_id}")
        return group

    async def get_by_id(self, group_id: int, user_id: int) -> Optional[AccountGroup]:
        """Get group by ID, verifying ownership."""
        return self._session.query(AccountGroup).filter(
            AccountGroup.id == group_id,
            AccountGroup.user_id == user_id,
        ).first()

    async def get_by_user(
        self,
        user_id: int,
        active_only: bool = True,
    ) -> List[AccountGroup]:
        """Get all groups for a user."""
        query = self._session.query(AccountGroup).filter(
            AccountGroup.user_id == user_id
        )
        if active_only:
            query = query.filter(AccountGroup.is_active == True)
        return query.order_by(AccountGroup.name).all()

    async def update(
        self,
        group_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[AccountGroup]:
        """Update a group's properties."""
        group = await self.get_by_id(group_id, user_id)
        if not group:
            return None

        if name is not None:
            group.name = name
            # Update cached name in accounts
            self._session.query(TradingAccount).filter(
                TradingAccount.group_id == group_id
            ).update({"group_name": name})

        if description is not None:
            group.description = description
        if color is not None:
            group.color = color
            # Update cached color in accounts
            self._session.query(TradingAccount).filter(
                TradingAccount.group_id == group_id
            ).update({"group_color": color})

        if icon is not None:
            group.icon = icon
        if is_active is not None:
            group.is_active = is_active

        self._session.commit()
        self._session.refresh(group)
        logger.info(f"Updated account group: {group_id}")
        return group

    async def delete(self, group_id: int, user_id: int) -> bool:
        """
        Delete a group.

        Sets group_id to NULL for all accounts in this group (cascade handling).
        """
        group = await self.get_by_id(group_id, user_id)
        if not group:
            return False

        # Clear group references in accounts
        self._session.query(TradingAccount).filter(
            TradingAccount.group_id == group_id
        ).update({
            "group_id": None,
            "group_name": None,
            "group_color": None,
        })

        self._session.delete(group)
        self._session.commit()
        logger.info(f"Deleted account group: {group_id}")
        return True

    async def get_account_count(self, group_id: int) -> int:
        """Get the number of accounts in a group."""
        return self._session.query(func.count(TradingAccount.id)).filter(
            TradingAccount.group_id == group_id
        ).scalar() or 0

    async def add_account_to_group(
        self,
        group_id: int,
        account_id: int,
        user_id: int,
    ) -> bool:
        """Add an account to a group."""
        # Verify group exists and belongs to user
        group = await self.get_by_id(group_id, user_id)
        if not group:
            return False

        # Verify account exists and belongs to user
        account = self._session.query(TradingAccount).filter(
            TradingAccount.id == account_id,
            TradingAccount.user_id == user_id,
        ).first()
        if not account:
            return False

        # Update account
        account.group_id = group_id
        account.group_name = group.name
        account.group_color = group.color

        self._session.commit()
        logger.info(f"Added account {account_id} to group {group_id}")
        return True

    async def remove_account_from_group(
        self,
        account_id: int,
        user_id: int,
    ) -> bool:
        """Remove an account from its group."""
        account = self._session.query(TradingAccount).filter(
            TradingAccount.id == account_id,
            TradingAccount.user_id == user_id,
        ).first()
        if not account:
            return False

        previous_group_id = account.group_id
        account.group_id = None
        account.group_name = None
        account.group_color = None

        self._session.commit()
        logger.info(f"Removed account {account_id} from group {previous_group_id}")
        return True
