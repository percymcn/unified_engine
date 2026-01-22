"""
Repository Implementations Package

Contains SQLAlchemy implementations of domain repository interfaces:
- SQLAlchemySignalRepository
- SQLAlchemyTradeRepository
- SQLAlchemyOrderRepository
- SQLAlchemyAccountRepository
- SQLAlchemyPositionRepository

Each repository:
- Implements corresponding interface from app.domain.ports.repository_port
- Uses SQLAlchemy for database operations
- Converts between SQLAlchemy models and domain entities
- Handles database-specific queries and optimizations

Implementation in Plan 05-03.
"""

from app.infrastructure.repositories.signal_repository import SQLAlchemySignalRepository
from app.infrastructure.repositories.trade_repository import SQLAlchemyTradeRepository
from app.infrastructure.repositories.order_repository import SQLAlchemyOrderRepository
from app.infrastructure.repositories.account_repository import SQLAlchemyAccountRepository
from app.infrastructure.repositories.position_repository import SQLAlchemyPositionRepository
from app.infrastructure.repositories.symbol_alias_repository import SQLAlchemySymbolAliasRepository
from app.infrastructure.repositories.account_group_repository import AccountGroupRepository
from app.infrastructure.repositories.daily_counter_repository import (
    InMemoryDailyCounterRepository,
    get_daily_counter_repository,
)
from app.infrastructure.repositories.daily_pnl_repository import DailyPnLRepository
from app.infrastructure.repositories.equity_history_repository import EquityHistoryRepository

__all__ = [
    "SQLAlchemySignalRepository",
    "SQLAlchemyTradeRepository",
    "SQLAlchemyOrderRepository",
    "SQLAlchemyAccountRepository",
    "SQLAlchemyPositionRepository",
    "SQLAlchemySymbolAliasRepository",
    "AccountGroupRepository",
    "InMemoryDailyCounterRepository",
    "get_daily_counter_repository",
    "DailyPnLRepository",
    "EquityHistoryRepository",
]
