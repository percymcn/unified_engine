"""
Symbol Alias DTOs (Data Transfer Objects)

Request/Response objects for symbol alias operations.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class SymbolAliasDTO:
    """DTO representing a symbol alias."""
    id: int
    source_symbol: str
    broker_type: str
    target_symbol: str
    is_auto_detected: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


@dataclass
class SymbolAliasGroupDTO:
    """DTO representing symbol aliases grouped by broker."""
    broker_type: str
    broker_name: str
    aliases: List[SymbolAliasDTO] = field(default_factory=list)


# Request DTOs

@dataclass
class GetSymbolAliasesRequest:
    """Request to get all symbol aliases for a user."""
    user_id: int
    broker_type: Optional[str] = None


@dataclass
class CreateSymbolAliasRequest:
    """Request to create a new symbol alias."""
    user_id: int
    source_symbol: str
    broker_type: str
    target_symbol: str


@dataclass
class UpdateSymbolAliasRequest:
    """Request to update a symbol alias."""
    alias_id: int
    user_id: int
    target_symbol: str


@dataclass
class DeleteSymbolAliasRequest:
    """Request to delete a symbol alias."""
    alias_id: int
    user_id: int


# Response DTOs

@dataclass
class GetSymbolAliasesResponse:
    """Response containing grouped symbol aliases."""
    groups: List[SymbolAliasGroupDTO] = field(default_factory=list)
    total: int = 0


@dataclass
class SymbolAliasResponse:
    """Response for single alias operations."""
    alias: Optional[SymbolAliasDTO] = None
    success: bool = False
    error: Optional[str] = None


@dataclass
class DeleteSymbolAliasResponse:
    """Response for delete operation."""
    deleted: bool = False
    error: Optional[str] = None
