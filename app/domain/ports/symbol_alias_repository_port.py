"""
SymbolAliasRepository Port Interface

Abstract repository interface for SymbolAlias entities.
Infrastructure adapters (SQLAlchemy) implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.entities.symbol_alias import SymbolAlias


class SymbolAliasRepository(ABC):
    """
    Repository interface for SymbolAlias entities.

    Provides CRUD operations and queries for symbol alias mappings.
    Implementations handle database-specific operations.
    """

    @abstractmethod
    async def get_by_user_and_broker(
        self,
        user_id: int,
        broker_type: str
    ) -> List[SymbolAlias]:
        """
        Get all aliases for a user and broker.

        Args:
            user_id: User ID
            broker_type: Broker type (e.g., "tradelocker")

        Returns:
            List of SymbolAlias entities for the user/broker
        """
        pass

    @abstractmethod
    async def get_alias(
        self,
        user_id: int,
        source_symbol: str,
        broker_type: str
    ) -> Optional[SymbolAlias]:
        """
        Get specific alias by user, source symbol, and broker.

        Args:
            user_id: User ID
            source_symbol: TradingView symbol
            broker_type: Broker type

        Returns:
            SymbolAlias if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[SymbolAlias]:
        """
        Get all aliases for a user.

        Args:
            user_id: User ID
            limit: Maximum number of aliases to return
            offset: Number of aliases to skip

        Returns:
            List of SymbolAlias entities
        """
        pass

    @abstractmethod
    async def create(self, alias: SymbolAlias) -> SymbolAlias:
        """
        Create a new alias.

        Args:
            alias: SymbolAlias entity to create

        Returns:
            Created SymbolAlias with ID populated

        Raises:
            DuplicateAliasError: If alias already exists for user/source/broker
        """
        pass

    @abstractmethod
    async def update(self, alias: SymbolAlias) -> SymbolAlias:
        """
        Update an existing alias.

        Args:
            alias: SymbolAlias entity with updated values

        Returns:
            Updated SymbolAlias entity

        Raises:
            AliasNotFoundError: If alias doesn't exist
        """
        pass

    @abstractmethod
    async def delete(self, alias_id: int, user_id: int) -> bool:
        """
        Delete an alias by ID.

        User ID is required for ownership verification.

        Args:
            alias_id: Alias ID to delete
            user_id: User ID for ownership check

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def delete_by_user_and_broker(
        self,
        user_id: int,
        broker_type: str
    ) -> int:
        """
        Delete all aliases for a user and broker.

        Args:
            user_id: User ID
            broker_type: Broker type

        Returns:
            Number of aliases deleted
        """
        pass

    @abstractmethod
    async def get_auto_detected(
        self,
        user_id: int,
        broker_type: Optional[str] = None
    ) -> List[SymbolAlias]:
        """
        Get auto-detected aliases.

        Args:
            user_id: User ID
            broker_type: Optional broker type filter

        Returns:
            List of auto-detected SymbolAlias entities
        """
        pass

    @abstractmethod
    async def get_user_defined(
        self,
        user_id: int,
        broker_type: Optional[str] = None
    ) -> List[SymbolAlias]:
        """
        Get user-defined aliases (not auto-detected).

        Args:
            user_id: User ID
            broker_type: Optional broker type filter

        Returns:
            List of user-defined SymbolAlias entities
        """
        pass

    @abstractmethod
    async def bulk_create_auto_aliases(
        self,
        user_id: int,
        broker_type: str,
        symbol_map: dict[str, str]
    ) -> int:
        """
        Bulk create auto-detected aliases from a symbol map.

        Skips aliases that already exist (user-defined take priority).
        Only creates aliases where source != target.

        Args:
            user_id: User ID for the aliases
            broker_type: Broker type (tradelocker, mt5, etc.)
            symbol_map: Dict mapping source symbols to target symbols

        Returns:
            Number of aliases created
        """
        pass

    @abstractmethod
    async def delete_auto_detected(
        self,
        user_id: int,
        broker_type: str
    ) -> int:
        """
        Delete all auto-detected aliases for a user and broker.

        Used when re-detecting symbols on re-connection.
        Does NOT delete user-defined aliases.

        Args:
            user_id: User ID
            broker_type: Broker type

        Returns:
            Number of aliases deleted
        """
        pass
