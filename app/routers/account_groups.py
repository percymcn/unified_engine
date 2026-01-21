"""
Account Groups API Router

REST endpoints for managing account groups (CRUD operations).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.models import User
from app.routers.auth import get_current_user
from app.dependencies import get_container
from app.application.dto.account_group_dto import (
    CreateAccountGroupRequest,
    UpdateAccountGroupRequest,
    DeleteAccountGroupRequest,
    GetAccountGroupsRequest,
    AddAccountToGroupRequest,
    RemoveAccountFromGroupRequest,
)


router = APIRouter()


# Pydantic request/response models for API
class CreateGroupBody(BaseModel):
    """Request body for creating an account group"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: str = Field("#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str = Field("folder", max_length=50)


class UpdateGroupBody(BaseModel):
    """Request body for updating an account group"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class GroupResponse(BaseModel):
    """Response model for account group"""
    id: int
    name: str
    description: Optional[str]
    color: str
    icon: str
    account_count: int
    is_active: bool
    created_at: str
    updated_at: str


@router.get("/")
async def get_account_groups(
    request: Request,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user),
) -> List[GroupResponse]:
    """
    Get all account groups for the current user.

    Query params:
    - include_inactive: Include deactivated groups (default: false)
    """
    container = get_container(request)
    use_case = container.get_account_groups_use_case()

    dto_request = GetAccountGroupsRequest(
        user_id=current_user.id,
        active_only=not include_inactive,
    )

    response = await use_case.execute(dto_request)

    return [
        GroupResponse(
            id=g.id,
            name=g.name,
            description=g.description,
            color=g.color,
            icon=g.icon,
            account_count=g.account_count,
            is_active=g.is_active,
            created_at=g.created_at.isoformat(),
            updated_at=g.updated_at.isoformat(),
        )
        for g in response.groups
    ]


@router.get("/{group_id}")
async def get_account_group(
    request: Request,
    group_id: int,
    current_user: User = Depends(get_current_user),
) -> GroupResponse:
    """Get a specific account group by ID."""
    container = get_container(request)
    use_case = container.get_account_group_use_case()

    try:
        response = await use_case.execute(group_id, current_user.id)
        return GroupResponse(
            id=response.id,
            name=response.name,
            description=response.description,
            color=response.color,
            icon=response.icon,
            account_count=response.account_count,
            is_active=response.is_active,
            created_at=response.created_at.isoformat(),
            updated_at=response.updated_at.isoformat(),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_account_group(
    request: Request,
    body: CreateGroupBody,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new account group.

    Groups help organize trading accounts (e.g., "Prop Firm Accounts", "Personal").
    """
    container = get_container(request)
    use_case = container.create_account_group_use_case()

    dto_request = CreateAccountGroupRequest(
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        color=body.color,
        icon=body.icon,
    )

    response = await use_case.execute(dto_request)

    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.error,
        )

    return {
        "message": "Account group created successfully",
        "group_id": response.group_id,
    }


@router.put("/{group_id}")
async def update_account_group(
    request: Request,
    group_id: int,
    body: UpdateGroupBody,
    current_user: User = Depends(get_current_user),
):
    """
    Update an account group.

    Only provided fields will be updated.
    """
    container = get_container(request)
    use_case = container.update_account_group_use_case()

    dto_request = UpdateAccountGroupRequest(
        group_id=group_id,
        user_id=current_user.id,
        name=body.name,
        description=body.description,
        color=body.color,
        icon=body.icon,
        is_active=body.is_active,
    )

    response = await use_case.execute(dto_request)

    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.error,
        )

    return {
        "message": "Account group updated successfully",
        "group_id": response.group_id,
    }


@router.delete("/{group_id}")
async def delete_account_group(
    request: Request,
    group_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Delete an account group.

    Accounts in this group will be unassigned (group_id set to NULL).
    """
    container = get_container(request)
    use_case = container.delete_account_group_use_case()

    dto_request = DeleteAccountGroupRequest(
        group_id=group_id,
        user_id=current_user.id,
    )

    response = await use_case.execute(dto_request)

    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.error,
        )

    return {
        "message": "Account group deleted successfully",
        "group_id": response.group_id,
    }


@router.post("/{group_id}/accounts/{account_id}")
async def add_account_to_group(
    request: Request,
    group_id: int,
    account_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Add an account to a group.

    The account will be removed from any existing group.
    """
    container = get_container(request)
    use_case = container.add_account_to_group_use_case()

    dto_request = AddAccountToGroupRequest(
        group_id=group_id,
        account_id=account_id,
        user_id=current_user.id,
    )

    response = await use_case.execute(dto_request)

    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.error,
        )

    return {
        "message": f"Account {account_id} added to group {group_id}",
        "group_id": response.group_id,
    }


@router.delete("/{group_id}/accounts/{account_id}")
async def remove_account_from_group(
    request: Request,
    group_id: int,
    account_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Remove an account from a group.

    The account's group_id will be set to NULL.
    """
    container = get_container(request)
    use_case = container.remove_account_from_group_use_case()

    dto_request = RemoveAccountFromGroupRequest(
        group_id=group_id,
        account_id=account_id,
        user_id=current_user.id,
    )

    response = await use_case.execute(dto_request)

    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=response.error,
        )

    return {
        "message": f"Account {account_id} removed from group",
    }
