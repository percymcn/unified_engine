"""
Account Group Management Use Cases

CRUD use cases for organizing trading accounts into groups.
"""
import logging
from typing import List

from app.infrastructure.repositories.account_group_repository import AccountGroupRepository
from app.application.dto.account_group_dto import (
    CreateAccountGroupRequest,
    UpdateAccountGroupRequest,
    DeleteAccountGroupRequest,
    GetAccountGroupsRequest,
    AddAccountToGroupRequest,
    RemoveAccountFromGroupRequest,
    AccountGroupResponse,
    AccountGroupListResponse,
    AccountGroupOperationResponse,
)

logger = logging.getLogger(__name__)


class CreateAccountGroupUseCase:
    """Use case for creating a new account group"""

    def __init__(self, group_repository: AccountGroupRepository):
        self._group_repo = group_repository

    async def execute(self, request: CreateAccountGroupRequest) -> AccountGroupOperationResponse:
        """Create a new account group."""
        try:
            group = await self._group_repo.create(
                user_id=request.user_id,
                name=request.name,
                description=request.description,
                color=request.color,
                icon=request.icon,
            )

            logger.info(f"Created account group '{request.name}' for user {request.user_id}")

            return AccountGroupOperationResponse(
                success=True,
                group_id=group.id,
            )

        except Exception as e:
            logger.exception(f"Failed to create account group: {e}")
            return AccountGroupOperationResponse(
                success=False,
                error=str(e),
            )


class GetAccountGroupsUseCase:
    """Use case for listing account groups"""

    def __init__(self, group_repository: AccountGroupRepository):
        self._group_repo = group_repository

    async def execute(self, request: GetAccountGroupsRequest) -> AccountGroupListResponse:
        """Get all account groups for a user."""
        groups = await self._group_repo.get_by_user(
            user_id=request.user_id,
            active_only=request.active_only,
        )

        responses = []
        for group in groups:
            account_count = await self._group_repo.get_account_count(group.id)
            responses.append(AccountGroupResponse(
                id=group.id,
                name=group.name,
                description=group.description,
                color=group.color,
                icon=group.icon,
                account_count=account_count,
                is_active=group.is_active,
                created_at=group.created_at,
                updated_at=group.updated_at,
            ))

        return AccountGroupListResponse(
            groups=responses,
            total=len(responses),
        )


class GetAccountGroupUseCase:
    """Use case for getting a single account group"""

    def __init__(self, group_repository: AccountGroupRepository):
        self._group_repo = group_repository

    async def execute(self, group_id: int, user_id: int) -> AccountGroupResponse:
        """Get a single account group by ID."""
        group = await self._group_repo.get_by_id(group_id, user_id)
        if not group:
            raise ValueError(f"Group {group_id} not found")

        account_count = await self._group_repo.get_account_count(group.id)

        return AccountGroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            color=group.color,
            icon=group.icon,
            account_count=account_count,
            is_active=group.is_active,
            created_at=group.created_at,
            updated_at=group.updated_at,
        )


class UpdateAccountGroupUseCase:
    """Use case for updating an account group"""

    def __init__(self, group_repository: AccountGroupRepository):
        self._group_repo = group_repository

    async def execute(self, request: UpdateAccountGroupRequest) -> AccountGroupOperationResponse:
        """Update an account group."""
        try:
            group = await self._group_repo.update(
                group_id=request.group_id,
                user_id=request.user_id,
                name=request.name,
                description=request.description,
                color=request.color,
                icon=request.icon,
                is_active=request.is_active,
            )

            if not group:
                return AccountGroupOperationResponse(
                    success=False,
                    error=f"Group {request.group_id} not found",
                )

            logger.info(f"Updated account group {request.group_id}")

            return AccountGroupOperationResponse(
                success=True,
                group_id=group.id,
            )

        except Exception as e:
            logger.exception(f"Failed to update account group: {e}")
            return AccountGroupOperationResponse(
                success=False,
                error=str(e),
            )


class DeleteAccountGroupUseCase:
    """Use case for deleting an account group"""

    def __init__(self, group_repository: AccountGroupRepository):
        self._group_repo = group_repository

    async def execute(self, request: DeleteAccountGroupRequest) -> AccountGroupOperationResponse:
        """Delete an account group."""
        try:
            deleted = await self._group_repo.delete(
                group_id=request.group_id,
                user_id=request.user_id,
            )

            if not deleted:
                return AccountGroupOperationResponse(
                    success=False,
                    error=f"Group {request.group_id} not found",
                )

            logger.info(f"Deleted account group {request.group_id}")

            return AccountGroupOperationResponse(
                success=True,
                group_id=request.group_id,
            )

        except Exception as e:
            logger.exception(f"Failed to delete account group: {e}")
            return AccountGroupOperationResponse(
                success=False,
                error=str(e),
            )


class AddAccountToGroupUseCase:
    """Use case for adding an account to a group"""

    def __init__(self, group_repository: AccountGroupRepository):
        self._group_repo = group_repository

    async def execute(self, request: AddAccountToGroupRequest) -> AccountGroupOperationResponse:
        """Add an account to a group."""
        try:
            added = await self._group_repo.add_account_to_group(
                group_id=request.group_id,
                account_id=request.account_id,
                user_id=request.user_id,
            )

            if not added:
                return AccountGroupOperationResponse(
                    success=False,
                    error="Account or group not found",
                )

            logger.info(f"Added account {request.account_id} to group {request.group_id}")

            return AccountGroupOperationResponse(
                success=True,
                group_id=request.group_id,
            )

        except Exception as e:
            logger.exception(f"Failed to add account to group: {e}")
            return AccountGroupOperationResponse(
                success=False,
                error=str(e),
            )


class RemoveAccountFromGroupUseCase:
    """Use case for removing an account from a group"""

    def __init__(self, group_repository: AccountGroupRepository):
        self._group_repo = group_repository

    async def execute(self, request: RemoveAccountFromGroupRequest) -> AccountGroupOperationResponse:
        """Remove an account from its group."""
        try:
            removed = await self._group_repo.remove_account_from_group(
                account_id=request.account_id,
                user_id=request.user_id,
            )

            if not removed:
                return AccountGroupOperationResponse(
                    success=False,
                    error="Account not found",
                )

            logger.info(f"Removed account {request.account_id} from group")

            return AccountGroupOperationResponse(
                success=True,
                group_id=request.group_id,
            )

        except Exception as e:
            logger.exception(f"Failed to remove account from group: {e}")
            return AccountGroupOperationResponse(
                success=False,
                error=str(e),
            )
