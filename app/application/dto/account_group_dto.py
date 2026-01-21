"""
Account Group DTOs - Input/Output contracts for account group use cases.

Handles CRUD operations for organizing trading accounts into groups.
"""
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass(frozen=True)
class CreateAccountGroupRequest:
    """Request to create a new account group"""
    user_id: int
    name: str  # "Prop Firm Accounts", "Personal", etc.
    description: Optional[str] = None
    color: str = "#6366f1"  # Hex color for UI
    icon: str = "folder"  # Icon name for UI


@dataclass(frozen=True)
class UpdateAccountGroupRequest:
    """Request to update an account group"""
    group_id: int
    user_id: int  # For ownership verification
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None


@dataclass(frozen=True)
class DeleteAccountGroupRequest:
    """Request to delete an account group"""
    group_id: int
    user_id: int  # For ownership verification


@dataclass(frozen=True)
class GetAccountGroupsRequest:
    """Request to list account groups for a user"""
    user_id: int
    active_only: bool = True


@dataclass(frozen=True)
class AddAccountToGroupRequest:
    """Request to add an account to a group"""
    group_id: int
    account_id: int
    user_id: int  # For ownership verification


@dataclass(frozen=True)
class RemoveAccountFromGroupRequest:
    """Request to remove an account from a group"""
    group_id: int
    account_id: int
    user_id: int  # For ownership verification


@dataclass(frozen=True)
class AccountGroupResponse:
    """Response with account group details"""
    id: int
    name: str
    description: Optional[str]
    color: str
    icon: str
    account_count: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AccountGroupListResponse:
    """Response with list of account groups"""
    groups: List[AccountGroupResponse]
    total: int


@dataclass(frozen=True)
class AccountGroupOperationResponse:
    """Response for group operations (create/update/delete)"""
    success: bool
    group_id: Optional[int] = None
    error: Optional[str] = None
