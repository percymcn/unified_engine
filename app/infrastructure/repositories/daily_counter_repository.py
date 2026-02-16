"""
Daily Counter Repository - Database Implementation

Stores daily counters in PostgreSQL for persistence across container restarts.
"""

from datetime import date, datetime
from typing import Dict, Optional
import asyncio
import logging
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.domain.services.daily_counter_service import DailyCounters
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)


class SQLAlchemyDailyCounterRepository:
    """
    Database-backed repository for daily counters.

    Persists counters to daily_counters table.
    Survives container restarts and deployments.
    """

    def __init__(self, db: Optional[Session] = None):
        """
        Initialize with optional database session.

        Args:
            db: SQLAlchemy session (creates new if None)
        """
        self._db = db
        self._owns_session = db is None

    def _get_db(self) -> Session:
        """Get or create database session"""
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def _close_db(self):
        """Close database session if we own it"""
        if self._owns_session and self._db:
            self._db.close()
            self._db = None

    async def get_or_create(self, account_id: int, for_date: date) -> DailyCounters:
        """
        Get or create counters for account on date.

        Args:
            account_id: Account ID
            for_date: Date for counters

        Returns:
            DailyCounters instance
        """
        from app.models.database_models import DailyCounter

        db = self._get_db()
        try:
            # Try to get existing counter
            counter = db.query(DailyCounter).filter(
                DailyCounter.account_id == account_id,
                DailyCounter.date == for_date
            ).first()

            if counter:
                # Convert to domain model
                return DailyCounters(
                    account_id=counter.account_id,
                    date=counter.date,
                    signals_received=counter.signals_received,
                    trades_executed=counter.trades_executed,
                    trades_rejected=counter.trades_rejected,
                    last_trade_at=counter.last_trade_at
                )
            else:
                # Create new counter
                new_counter = DailyCounter(
                    account_id=account_id,
                    date=for_date,
                    signals_received=0,
                    trades_executed=0,
                    trades_rejected=0,
                    last_trade_at=None
                )
                db.add(new_counter)
                db.commit()
                db.refresh(new_counter)

                return DailyCounters(
                    account_id=new_counter.account_id,
                    date=new_counter.date,
                    signals_received=new_counter.signals_received,
                    trades_executed=new_counter.trades_executed,
                    trades_rejected=new_counter.trades_rejected,
                    last_trade_at=new_counter.last_trade_at
                )
        except Exception as e:
            logger.error(f"Error getting/creating daily counter: {e}")
            db.rollback()
            # Return empty counters on error
            return DailyCounters(
                account_id=account_id,
                date=for_date
            )

    async def save(self, counters: DailyCounters) -> None:
        """
        Save counters to database.

        Args:
            counters: DailyCounters to save
        """
        from app.models.database_models import DailyCounter

        db = self._get_db()
        try:
            # Upsert using PostgreSQL INSERT ... ON CONFLICT
            stmt = insert(DailyCounter).values(
                account_id=counters.account_id,
                date=counters.date,
                signals_received=counters.signals_received,
                trades_executed=counters.trades_executed,
                trades_rejected=counters.trades_rejected,
                last_trade_at=counters.last_trade_at,
                updated_at=datetime.utcnow()
            ).on_conflict_do_update(
                index_elements=['account_id', 'date'],
                set_={
                    'signals_received': counters.signals_received,
                    'trades_executed': counters.trades_executed,
                    'trades_rejected': counters.trades_rejected,
                    'last_trade_at': counters.last_trade_at,
                    'updated_at': datetime.utcnow()
                }
            )
            db.execute(stmt)
            db.commit()
        except Exception as e:
            logger.error(f"Error saving daily counter: {e}")
            db.rollback()

    async def get_all_for_date(self, for_date: date) -> list[DailyCounters]:
        """
        Get all counters for a specific date.

        Args:
            for_date: Date to query

        Returns:
            List of DailyCounters for that date
        """
        from app.models.database_models import DailyCounter

        db = self._get_db()
        try:
            counters = db.query(DailyCounter).filter(
                DailyCounter.date == for_date
            ).all()

            return [
                DailyCounters(
                    account_id=c.account_id,
                    date=c.date,
                    signals_received=c.signals_received,
                    trades_executed=c.trades_executed,
                    trades_rejected=c.trades_rejected,
                    last_trade_at=c.last_trade_at
                )
                for c in counters
            ]
        except Exception as e:
            logger.error(f"Error getting all counters: {e}")
            return []

    async def clear(self) -> None:
        """Clear all counters (for testing)"""
        from app.models.database_models import DailyCounter

        db = self._get_db()
        try:
            db.query(DailyCounter).delete()
            db.commit()
        except Exception as e:
            logger.error(f"Error clearing counters: {e}")
            db.rollback()

    def __del__(self):
        """Cleanup on destruction"""
        self._close_db()


class InMemoryDailyCounterRepository:
    """
    In-memory repository for daily counters.

    Stores counters keyed by (account_id, date).
    Automatically cleans up old entries.
    """

    def __init__(self):
        """Initialize in-memory storage"""
        # Storage: {(account_id, date_str): DailyCounters}
        self._storage: Dict[tuple, DailyCounters] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = date.today()

    def _make_key(self, account_id: int, for_date: date) -> tuple:
        """Create storage key from account_id and date"""
        return (account_id, for_date.isoformat())

    async def get_or_create(self, account_id: int, for_date: date) -> DailyCounters:
        """
        Get or create counters for account on date.

        Args:
            account_id: Account ID
            for_date: Date for counters

        Returns:
            DailyCounters instance
        """
        async with self._lock:
            # Cleanup old entries if needed
            await self._cleanup_if_needed()

            key = self._make_key(account_id, for_date)
            if key not in self._storage:
                self._storage[key] = DailyCounters(
                    account_id=account_id,
                    date=for_date
                )
            return self._storage[key]

    async def save(self, counters: DailyCounters) -> None:
        """
        Save counters to storage.

        Args:
            counters: DailyCounters to save
        """
        async with self._lock:
            key = self._make_key(counters.account_id, counters.date)
            self._storage[key] = counters

    async def get_all_for_date(self, for_date: date) -> list[DailyCounters]:
        """
        Get all counters for a specific date.

        Args:
            for_date: Date to query

        Returns:
            List of DailyCounters for that date
        """
        async with self._lock:
            return [
                counters for (_, d), counters in self._storage.items()
                if d == for_date.isoformat()
            ]

    async def _cleanup_if_needed(self) -> None:
        """Remove entries older than yesterday"""
        today = date.today()
        if today == self._last_cleanup:
            return

        # Remove entries older than yesterday
        yesterday = date.today().isoformat()
        keys_to_remove = [
            key for key in self._storage.keys()
            if key[1] < yesterday
        ]

        for key in keys_to_remove:
            del self._storage[key]

        self._last_cleanup = today
        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} old counter entries")

    async def clear(self) -> None:
        """Clear all counters (for testing)"""
        async with self._lock:
            self._storage.clear()


# Global singleton instance for database-backed repository
_counter_repository: Optional[SQLAlchemyDailyCounterRepository] = None


def get_daily_counter_repository(use_memory: bool = False) -> SQLAlchemyDailyCounterRepository:
    """
    Get the global daily counter repository instance.

    Args:
        use_memory: If True, use in-memory repository (for testing only)

    Returns:
        SQLAlchemyDailyCounterRepository singleton (database-backed)
    """
    global _counter_repository
    if _counter_repository is None:
        if use_memory:
            logger.warning("Using in-memory counter repository - data will be lost on restart!")
            _counter_repository = InMemoryDailyCounterRepository()
        else:
            _counter_repository = SQLAlchemyDailyCounterRepository()
    return _counter_repository
