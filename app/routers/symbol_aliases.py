"""
Symbol Aliases Router

REST API endpoints for managing symbol alias mappings.
Allows users to view, create, update, and delete custom symbol mappings per broker.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

from app.models.models import User
from app.routers.auth import get_current_user
from app.dependencies import get_container
from app.domain.entities.symbol_alias import SymbolAlias


# Pydantic models for API request/response

class SymbolAliasResponse(BaseModel):
    """Symbol alias response model."""
    id: int
    source_symbol: str = Field(..., alias="sourceSymbol")
    broker_type: str = Field(..., alias="brokerType")
    target_symbol: str = Field(..., alias="targetSymbol")
    is_auto_detected: bool = Field(..., alias="isAutoDetected")
    created_at: datetime = Field(..., alias="createdAt")

    class Config:
        populate_by_name = True
        from_attributes = True


class SymbolAliasGroupResponse(BaseModel):
    """Symbol aliases grouped by broker."""
    broker_type: str = Field(..., alias="brokerType")
    broker_name: str = Field(..., alias="brokerName")
    aliases: List[SymbolAliasResponse]

    class Config:
        populate_by_name = True


class CreateSymbolAliasRequest(BaseModel):
    """Request to create a new symbol alias."""
    source_symbol: str = Field(..., alias="sourceSymbol", min_length=1, max_length=50)
    broker_type: str = Field(..., alias="brokerType", min_length=1, max_length=50)
    target_symbol: str = Field(..., alias="targetSymbol", min_length=1, max_length=50)

    class Config:
        populate_by_name = True


class UpdateSymbolAliasRequest(BaseModel):
    """Request to update a symbol alias."""
    target_symbol: str = Field(..., alias="targetSymbol", min_length=1, max_length=50)

    class Config:
        populate_by_name = True


# Broker display name mapping
BROKER_DISPLAY_NAMES = {
    "tradelocker": "TradeLocker",
    "tradovate": "Tradovate",
    "projectx": "ProjectX",
    "topstep": "TopStep",
    "mt4": "MetaTrader 4",
    "mt5": "MetaTrader 5",
}


router = APIRouter()


def _entity_to_response(entity: SymbolAlias) -> SymbolAliasResponse:
    """Convert domain entity to API response."""
    return SymbolAliasResponse(
        id=entity.id,
        sourceSymbol=entity.source_symbol,
        brokerType=entity.broker_type,
        targetSymbol=entity.target_symbol,
        isAutoDetected=entity.is_auto_detected,
        createdAt=entity.created_at,
    )


@router.get("/", response_model=List[SymbolAliasGroupResponse])
async def get_symbol_aliases(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Get all symbol aliases for the current user, grouped by broker.

    Returns aliases organized by broker type, with broker display names
    for UI rendering. Auto-detected aliases are marked with a flag.
    """
    container = get_container(request)
    alias_repo = container._get_symbol_alias_repository()

    # Get all aliases for user
    aliases = await alias_repo.get_by_user(current_user.id, limit=500)

    # Group by broker type
    groups_dict = {}
    for alias in aliases:
        broker = alias.broker_type
        if broker not in groups_dict:
            groups_dict[broker] = []
        groups_dict[broker].append(_entity_to_response(alias))

    # Convert to list of groups
    groups = []
    for broker_type, alias_list in sorted(groups_dict.items()):
        groups.append(SymbolAliasGroupResponse(
            brokerType=broker_type,
            brokerName=BROKER_DISPLAY_NAMES.get(broker_type, broker_type.title()),
            aliases=alias_list,
        ))

    return groups


@router.get("/{broker_type}", response_model=List[SymbolAliasResponse])
async def get_symbol_aliases_by_broker(
    request: Request,
    broker_type: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get symbol aliases for a specific broker.

    Args:
        broker_type: Broker type (tradelocker, tradovate, mt4, mt5, projectx, topstep)
    """
    container = get_container(request)
    alias_repo = container._get_symbol_alias_repository()

    aliases = await alias_repo.get_by_user_and_broker(current_user.id, broker_type)

    return [_entity_to_response(alias) for alias in aliases]


@router.post("/", response_model=SymbolAliasResponse, status_code=status.HTTP_201_CREATED)
async def create_symbol_alias(
    request: Request,
    body: CreateSymbolAliasRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new symbol alias.

    Creates a user-defined mapping from a TradingView symbol to a broker's format.
    If an alias already exists for the same source/broker combination, returns 409.
    """
    container = get_container(request)
    alias_repo = container._get_symbol_alias_repository()

    # Check for existing alias
    existing = await alias_repo.get_alias(
        current_user.id,
        body.source_symbol,
        body.broker_type,
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alias already exists for {body.source_symbol} -> {body.broker_type}. Use PUT to update.",
        )

    # Create new alias (user-defined, not auto-detected)
    alias = SymbolAlias(
        user_id=current_user.id,
        source_symbol=body.source_symbol,
        broker_type=body.broker_type,
        target_symbol=body.target_symbol,
        is_auto_detected=False,
    )

    try:
        created = await alias_repo.create(alias)
        return _entity_to_response(created)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{alias_id}", response_model=SymbolAliasResponse)
async def update_symbol_alias(
    request: Request,
    alias_id: int,
    body: UpdateSymbolAliasRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing symbol alias.

    Updates the target symbol for an alias. If the alias was auto-detected,
    this converts it to a user-defined alias (user overrides take priority).
    """
    container = get_container(request)
    alias_repo = container._get_symbol_alias_repository()

    # Get aliases for user to find the one with matching ID
    aliases = await alias_repo.get_by_user(current_user.id, limit=500)
    alias = next((a for a in aliases if a.id == alias_id), None)

    if not alias:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol alias {alias_id} not found",
        )

    # Update target symbol (converts auto-detected to user-defined)
    alias.update_target(body.target_symbol)

    try:
        updated = await alias_repo.update(alias)
        return _entity_to_response(updated)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_symbol_alias(
    request: Request,
    alias_id: int,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a symbol alias.

    Removes the alias mapping. For auto-detected aliases, this effectively
    resets the symbol to use the default normalization.
    """
    container = get_container(request)
    alias_repo = container._get_symbol_alias_repository()

    deleted = await alias_repo.delete(alias_id, current_user.id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Symbol alias {alias_id} not found",
        )

    return None
