"""
Position Sync Service
=====================
Ensures database position records stay in sync with broker positions.

Features:
- Real-time position verification before max position checks
- Automatic cleanup of stale database positions
- Reconciliation of database vs broker state
- Support for multi-account brokers (ProjectX)
"""

import logging
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.database_models import PositionTrade, TradingAccount

logger = logging.getLogger(__name__)


class PositionSyncService:
    """
    Service for synchronizing position data between database and broker.

    Handles:
    - Marking positions closed when broker reports them closed
    - Detecting positions closed by TP/SL/manual close
    - Providing accurate position counts for max position checks
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._last_sync: Dict[int, datetime] = {}  # account_id -> last sync time
        self._sync_interval = timedelta(seconds=30)  # Min time between syncs

    async def get_verified_position_count(
        self,
        account_id: int,
        broker_positions: List[Any],
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """
        Get verified position count after reconciling with broker.

        Args:
            account_id: Trading account ID
            broker_positions: List of positions from broker API
            force_sync: Force sync even if recently synced

        Returns:
            Dict with:
            - total: Verified total open positions
            - by_symbol: Dict of symbol -> count
            - stale_closed: Number of stale positions marked closed
            - broker_total: Raw broker position count
        """
        # Extract broker position IDs for comparison
        broker_position_ids = set()
        broker_symbols: Dict[str, int] = {}  # normalized_symbol -> count

        for pos in broker_positions:
            pos_id = self._get_position_id(pos)
            if pos_id:
                broker_position_ids.add(pos_id)

            symbol = self._get_position_symbol(pos)
            if symbol:
                normalized = self._normalize_symbol(symbol)
                broker_symbols[normalized] = broker_symbols.get(normalized, 0) + 1

        broker_total = len(broker_positions)
        stale_closed = 0

        # Check if we need to sync database
        now = datetime.now()
        last_sync = self._last_sync.get(account_id, datetime.min)
        should_sync = force_sync or (now - last_sync) > self._sync_interval

        if should_sync:
            # Get open positions from database
            stmt = select(PositionTrade).where(
                and_(
                    PositionTrade.account_id == account_id,
                    PositionTrade.status == 'open'
                )
            )
            result = await self.db.execute(stmt)
            db_positions = result.scalars().all()

            # Find positions in DB that are not at broker (closed via TP/SL/manual)
            positions_to_close = []
            for db_pos in db_positions:
                if db_pos.broker_position_id and db_pos.broker_position_id not in broker_position_ids:
                    positions_to_close.append(db_pos)
                    logger.info(
                        f"Position {db_pos.id} ({db_pos.symbol}) not found at broker "
                        f"(broker_id={db_pos.broker_position_id}) - marking as closed"
                    )

            # Mark stale positions as closed
            if positions_to_close:
                for pos in positions_to_close:
                    pos.status = 'closed'
                    pos.closed_at = now
                stale_closed = len(positions_to_close)
                await self.db.commit()
                logger.info(f"Account {account_id}: Marked {stale_closed} stale positions as closed")

            self._last_sync[account_id] = now

        return {
            "total": broker_total,
            "by_symbol": broker_symbols,
            "stale_closed": stale_closed,
            "broker_total": broker_total,
            "synced": should_sync
        }

    async def reconcile_all_positions(
        self,
        account_id: int,
        executor: Any
    ) -> Dict[str, Any]:
        """
        Full reconciliation of database positions with broker.

        Args:
            account_id: Trading account ID
            executor: Broker executor instance

        Returns:
            Reconciliation report
        """
        try:
            # Fetch current positions from broker
            broker_positions = await executor.get_positions()
            broker_total = len(broker_positions) if broker_positions else 0

            # Get database positions
            stmt = select(PositionTrade).where(
                and_(
                    PositionTrade.account_id == account_id,
                    PositionTrade.status == 'open'
                )
            )
            result = await self.db.execute(stmt)
            db_positions = result.scalars().all()
            db_total = len(db_positions)

            # Build broker position ID set
            broker_ids = set()
            for pos in broker_positions:
                pos_id = self._get_position_id(pos)
                if pos_id:
                    broker_ids.add(pos_id)

            # Find mismatches
            closed_by_broker = []
            missing_in_db = []

            for db_pos in db_positions:
                if db_pos.broker_position_id and db_pos.broker_position_id not in broker_ids:
                    closed_by_broker.append({
                        "db_id": db_pos.id,
                        "broker_id": db_pos.broker_position_id,
                        "symbol": db_pos.symbol,
                        "created_at": db_pos.created_at.isoformat() if db_pos.created_at else None
                    })
                    # Mark as closed
                    db_pos.status = 'closed'
                    db_pos.closed_at = datetime.now()

            # Build DB position ID set for reverse check
            db_broker_ids = {p.broker_position_id for p in db_positions if p.broker_position_id}

            for pos in broker_positions:
                pos_id = self._get_position_id(pos)
                if pos_id and pos_id not in db_broker_ids:
                    missing_in_db.append({
                        "broker_id": pos_id,
                        "symbol": self._get_position_symbol(pos)
                    })

            if closed_by_broker:
                await self.db.commit()

            report = {
                "account_id": account_id,
                "timestamp": datetime.now().isoformat(),
                "broker_positions": broker_total,
                "db_positions_before": db_total,
                "db_positions_after": db_total - len(closed_by_broker),
                "closed_by_broker": closed_by_broker,
                "missing_in_db": missing_in_db,
                "in_sync": len(closed_by_broker) == 0 and len(missing_in_db) == 0
            }

            logger.info(f"Reconciliation for account {account_id}: {report}")
            return report

        except Exception as e:
            logger.error(f"Reconciliation failed for account {account_id}: {e}", exc_info=True)
            return {
                "account_id": account_id,
                "error": str(e),
                "in_sync": False
            }

    async def cleanup_stale_positions(
        self,
        max_age_hours: int = 24
    ) -> int:
        """
        Mark old 'open' positions as closed if they haven't been updated.

        Args:
            max_age_hours: Mark positions older than this as stale

        Returns:
            Number of positions marked as stale
        """
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        stmt = (
            update(PositionTrade)
            .where(
                and_(
                    PositionTrade.status == 'open',
                    PositionTrade.updated_at < cutoff
                )
            )
            .values(status='closed', closed_at=datetime.now())
        )

        result = await self.db.execute(stmt)
        await self.db.commit()

        count = result.rowcount
        if count > 0:
            logger.info(f"Marked {count} stale positions (older than {max_age_hours}h) as closed")

        return count

    def _get_position_id(self, position: Any) -> Optional[str]:
        """Extract position ID from position object/dict."""
        if isinstance(position, dict):
            return str(position.get('id', '')) or None
        return str(getattr(position, 'id', '')) or None

    def _get_position_symbol(self, position: Any) -> Optional[str]:
        """Extract symbol from position object/dict."""
        if isinstance(position, dict):
            return position.get('symbol', '')
        return getattr(position, 'symbol', '')

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for comparison."""
        import re
        if not symbol:
            return ""
        s = symbol.upper().strip()

        # Handle ProjectX CON.F.US.XXX.YYY format
        if s.startswith('CON.'):
            parts = s.split('.')
            if len(parts) >= 4:
                s = parts[3]

        # Strip common suffixes
        for suffix in ['.PRO', '.RAW', '.STD', '.I', '.S', '_SB', '.SB']:
            if s.endswith(suffix):
                s = s[:-len(suffix)]

        # Strip futures contract month/year codes
        futures_pattern = re.compile(r'^([A-Z]+[A-Z0-9]*?)([FGHJKMNQUVXZ])(\d{1,4})$')
        match = futures_pattern.match(s)
        if match:
            s = match.group(1)

        # Strip trailing "1!" format
        if s.endswith('1!'):
            s = s[:-2]

        return s


# Global instance cache
_sync_services: Dict[int, PositionSyncService] = {}
_sync_last_sync: Dict[int, datetime] = {}
_sync_interval = timedelta(seconds=30)


def get_position_sync_service(db: AsyncSession) -> PositionSyncService:
    """Get or create position sync service for session."""
    return PositionSyncService(db)


async def sync_positions_before_check(
    db: AsyncSession,
    account_id: int,
    broker_positions: List[Any],
    force: bool = False
) -> Dict[str, Any]:
    """
    Convenience function to sync positions before max position check.

    Call this in webhook_execute.py before checking max_open_positions
    to ensure database is in sync with broker.
    """
    if isinstance(db, AsyncSession):
        service = get_position_sync_service(db)
        return await service.get_verified_position_count(account_id, broker_positions, force)

    return _get_verified_position_count_sync(db, account_id, broker_positions, force)


def _get_verified_position_count_sync(
    db: Session,
    account_id: int,
    broker_positions: List[Any],
    force_sync: bool = False
) -> Dict[str, Any]:
    """Sync version of get_verified_position_count for sync SQLAlchemy sessions."""
    def get_position_id(position: Any) -> Optional[str]:
        if isinstance(position, dict):
            return position.get('id') or position.get('position_id') or position.get('broker_position_id')
        return getattr(position, 'id', None) or getattr(position, 'position_id', None) or getattr(position, 'broker_position_id', None)

    def get_position_symbol(position: Any) -> Optional[str]:
        if isinstance(position, dict):
            return position.get('symbol') or position.get('instrument') or position.get('ticker')
        return getattr(position, 'symbol', None) or getattr(position, 'instrument', None) or getattr(position, 'ticker', None)

    def normalize_symbol(symbol: str) -> str:
        import re
        if not symbol:
            return ""
        s = symbol.upper().strip()
        if s.startswith('CON.'):
            parts = s.split('.')
            if len(parts) >= 4:
                s = parts[3]
        for suffix in ['.PRO', '.RAW', '.STD', '.I', '.S', '_SB', '.SB']:
            if s.endswith(suffix):
                s = s[:-len(suffix)]
        futures_pattern = re.compile(r'^([A-Z]+[A-Z0-9]*?)([FGHJKMNQUVXZ])(\d{1,4})$')
        match = futures_pattern.match(s)
        if match:
            s = match.group(1)
        if s.endswith('1!'):
            s = s[:-2]
        return s

    broker_position_ids = set()
    broker_symbols: Dict[str, int] = {}

    for pos in broker_positions:
        pos_id = get_position_id(pos)
        if pos_id:
            broker_position_ids.add(pos_id)

        symbol = get_position_symbol(pos)
        if symbol:
            normalized = normalize_symbol(symbol)
            broker_symbols[normalized] = broker_symbols.get(normalized, 0) + 1

    broker_total = len(broker_positions)
    stale_closed = 0

    now = datetime.now()
    last_sync = _sync_last_sync.get(account_id, datetime.min)
    should_sync = force_sync or (now - last_sync) > _sync_interval
    if should_sync:
        stmt = select(PositionTrade).where(
            and_(
                PositionTrade.account_id == account_id,
                PositionTrade.status == 'open'
            )
        )
        result = db.execute(stmt)
        db_positions = result.scalars().all()

        positions_to_close = []
        for db_pos in db_positions:
            if db_pos.broker_position_id and db_pos.broker_position_id not in broker_position_ids:
                positions_to_close.append(db_pos)
                logger.info(
                    f"Position {db_pos.id} ({db_pos.symbol}) not found at broker "
                    f"(broker_id={db_pos.broker_position_id}) - marking as closed"
                )

        if positions_to_close:
            for pos in positions_to_close:
                pos.status = 'closed'
                pos.closed_at = now
            stale_closed = len(positions_to_close)
            db.commit()
            logger.info(f"Account {account_id}: Marked {stale_closed} stale positions as closed")

        _sync_last_sync[account_id] = now

    return {
        "total": broker_total,
        "by_symbol": broker_symbols,
        "stale_closed": stale_closed,
        "broker_total": broker_total,
        "synced": should_sync
    }
