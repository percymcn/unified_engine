"""
Signal Intelligence Guard Layer

Implements self-protecting execution guards for the Signal Intelligence Layer.
All logic is broker-agnostic and plugs into the existing signal flow.

Features:
- sg-001: Signal Momentum Guard
- sg-002: Time-Lock & Staleness
- sg-004: Max Exposure Guard
- sg-005: Discard Bin & Auto-Flush
- sg-007: Hedge Toggle
"""
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_
import pytz

from app.models.database_models import (
    MomentumSettings,
    SignalCounter,
    DiscardBin,
    TradingAccount,
)
from app.domain.entities.signal import Signal
from app.domain.enums import SignalAction

logger = logging.getLogger(__name__)


class GuardDecision(str, Enum):
    """Guard decision types"""
    EXECUTE = "execute"
    SKIP = "skip"
    PAUSE_NEW_ENTRIES = "pause_new_entries"
    WARN_MODAL_REQUIRED = "warn_modal_required"


@dataclass
class GuardResult:
    """Result from guard layer evaluation"""
    decision: GuardDecision
    annotations: Dict[str, Any]  # History tags, discard reason, UI payload
    updated_counters: Optional[Dict] = None
    modal_data: Optional[Dict[str, Any]] = None  # Data for warning modal


class SignalIntelligenceGuard:
    """Signal Intelligence Guard Layer - Self-protecting execution engine"""

    def __init__(self, db: Session):
        self.db = db

    async def evaluate(
        self,
        signal: Signal,
        user_id: int,
        account_ids: List[int],
        open_positions_summary: Optional[Dict[int, Dict]] = None
    ) -> GuardResult:
        """
        Evaluate signal against all guards.

        Args:
            signal: Normalized signal entity
            user_id: User ID for settings lookup
            account_ids: List of target account IDs
            open_positions_summary: Dict mapping account_id -> {total_margin, positions_count, ...}

        Returns:
            GuardResult with decision and annotations
        """
        # Get user momentum settings (with defaults)
        settings = self._get_momentum_settings(user_id)

        # Initialize result
        result = GuardResult(
            decision=GuardDecision.EXECUTE,
            annotations={},
            updated_counters=None
        )

        # sg-002: Time-Lock & Staleness (execute early)
        staleness_result = await self._check_staleness(signal, settings, user_id)
        if staleness_result.decision != GuardDecision.EXECUTE:
            return staleness_result

        # Trading Session Check (new entry only)
        if signal.action != SignalAction.CLOSE:
            session_result = self._check_trading_session(settings, user_id)
            if session_result.decision != GuardDecision.EXECUTE:
                return session_result

        # Determine session key for momentum tracking
        session_key = self._get_session_key(user_id, signal)

        # sg-001: Signal Momentum Guard
        momentum_result = await self._check_momentum(
            signal, settings, user_id, session_key
        )
        if momentum_result.decision != GuardDecision.EXECUTE:
            # If warning required, merge momentum data into result
            if momentum_result.decision == GuardDecision.WARN_MODAL_REQUIRED:
                result.decision = GuardDecision.WARN_MODAL_REQUIRED
                result.modal_data = momentum_result.modal_data
                result.annotations.update(momentum_result.annotations)
                result.updated_counters = momentum_result.updated_counters
            else:
                return momentum_result

        # sg-004: Max Exposure Guard
        exposure_result = await self._check_exposure(
            signal, settings, account_ids, open_positions_summary or {}
        )
        if exposure_result.decision != GuardDecision.EXECUTE:
            if exposure_result.decision == GuardDecision.PAUSE_NEW_ENTRIES:
                # Merge exposure pause into result
                if result.decision == GuardDecision.EXECUTE:
                    result.decision = GuardDecision.PAUSE_NEW_ENTRIES
                result.annotations.update(exposure_result.annotations)
            else:
                return exposure_result

        # If we get here, signal passes all guards
        return result

    def _get_momentum_settings(self, user_id: int) -> MomentumSettings:
        """Get user momentum settings, creating defaults if missing"""
        settings = self.db.query(MomentumSettings).filter(
            MomentumSettings.user_id == user_id
        ).first()

        if not settings:
            # Create default settings
            settings = MomentumSettings(
                user_id=user_id,
                warn_at=6,
                auto_breakeven=False,
                pause_on_chop=True,
                max_exposure=5000.0,
                auto_pause_on_exposure=True,
                allow_hedge=False,
                staleness_enabled=True,
                staleness_seconds=5,
                force_old_signals=False,
                discard_flush_interval="24h"
            )
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)

        return settings

    def _get_session_key(self, user_id: int, signal: Signal) -> str:
        """Generate session key for momentum tracking"""
        strategy_id = signal.strategy_id or "default"
        return f"{user_id}:{signal.symbol.value}:{strategy_id}"

    def _check_trading_session(
        self,
        settings: MomentumSettings,
        user_id: int
    ) -> GuardResult:
        """
        Check if current time is within user's trading session.

        Returns SKIP decision if trading session is enabled and current time
        is outside the configured trading hours.
        """
        # Check if trading session is enabled
        if not getattr(settings, 'trading_session_enabled', False):
            return GuardResult(
                decision=GuardDecision.EXECUTE,
                annotations={}
            )

        try:
            # Get session settings
            session_start = getattr(settings, 'trading_session_start', '09:30') or '09:30'
            session_end = getattr(settings, 'trading_session_end', '16:00') or '16:00'
            session_tz_str = getattr(settings, 'trading_session_timezone', 'America/New_York') or 'America/New_York'
            session_days = getattr(settings, 'trading_session_days', [1, 2, 3, 4, 5]) or [1, 2, 3, 4, 5]

            # Parse timezone
            try:
                session_tz = pytz.timezone(session_tz_str)
            except Exception:
                session_tz = pytz.timezone('America/New_York')

            # Get current time in user's timezone
            now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
            now_local = now_utc.astimezone(session_tz)

            # Check day of week (1=Monday, 7=Sunday)
            # Python's weekday() returns 0=Monday, 6=Sunday, so we add 1
            current_day = now_local.weekday() + 1
            if current_day not in session_days:
                logger.info(f"Trading session: day {current_day} not in allowed days {session_days}")
                return GuardResult(
                    decision=GuardDecision.SKIP,
                    annotations={
                        "discard_reason": "outside_trading_session",
                        "history_tag": f"trading_session – outside trading days",
                        "current_day": current_day,
                        "allowed_days": session_days,
                    }
                )

            # Parse start and end times
            start_hour, start_min = map(int, session_start.split(':'))
            end_hour, end_min = map(int, session_end.split(':'))

            # Create time objects for comparison
            current_time_mins = now_local.hour * 60 + now_local.minute
            start_time_mins = start_hour * 60 + start_min
            end_time_mins = end_hour * 60 + end_min

            # Check if current time is within session
            if start_time_mins <= end_time_mins:
                # Normal case: session doesn't cross midnight
                in_session = start_time_mins <= current_time_mins <= end_time_mins
            else:
                # Session crosses midnight (e.g., 22:00 to 06:00)
                in_session = current_time_mins >= start_time_mins or current_time_mins <= end_time_mins

            if not in_session:
                logger.info(f"Trading session: time {now_local.strftime('%H:%M')} outside {session_start}-{session_end}")
                return GuardResult(
                    decision=GuardDecision.SKIP,
                    annotations={
                        "discard_reason": "outside_trading_session",
                        "history_tag": f"trading_session – outside hours ({session_start}-{session_end} {session_tz_str})",
                        "current_time": now_local.strftime('%H:%M'),
                        "session_start": session_start,
                        "session_end": session_end,
                        "session_timezone": session_tz_str,
                    }
                )

            # Within trading session
            return GuardResult(
                decision=GuardDecision.EXECUTE,
                annotations={}
            )

        except Exception as e:
            logger.warning(f"Error checking trading session: {e}")
            # On error, allow execution (fail open)
            return GuardResult(
                decision=GuardDecision.EXECUTE,
                annotations={"trading_session_error": str(e)}
            )

    async def _check_staleness(
        self,
        signal: Signal,
        settings: MomentumSettings,
        user_id: int
    ) -> GuardResult:
        """sg-002: Check if signal is stale"""
        if not settings.staleness_enabled or settings.force_old_signals:
            return GuardResult(
                decision=GuardDecision.EXECUTE,
                annotations={}
            )

        # Calculate signal age - prefer payload timestamp if present
        signal_age_seconds = 0  # Default: assume fresh
        
        # Try to get timestamp from raw_payload
        if signal.raw_payload and isinstance(signal.raw_payload, dict):
            # Check common timestamp fields
            timestamp_str = (
                signal.raw_payload.get("timestamp") or
                signal.raw_payload.get("time") or
                signal.raw_payload.get("created_at") or
                signal.raw_payload.get("ts")
            )
            
            if timestamp_str:
                try:
                    # Try ISO format first
                    if isinstance(timestamp_str, str):
                        if 'T' in timestamp_str or '+' in timestamp_str or timestamp_str.endswith('Z'):
                            received_ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        elif timestamp_str.isdigit():
                            # Unix timestamp (seconds or milliseconds)
                            ts_val = float(timestamp_str)
                            if ts_val > 1e10:  # Milliseconds
                                received_ts = datetime.fromtimestamp(ts_val / 1000.0, tz=datetime.timezone.utc)
                            else:  # Seconds
                                received_ts = datetime.fromtimestamp(ts_val, tz=datetime.timezone.utc)
                        else:
                            received_ts = datetime.fromisoformat(timestamp_str)
                    else:
                        received_ts = datetime.fromtimestamp(float(timestamp_str), tz=datetime.timezone.utc)
                    
                    # Calculate age
                    now = datetime.now(datetime.timezone.utc) if received_ts.tzinfo else datetime.utcnow()
                    if received_ts.tzinfo:
                        signal_age_seconds = (now - received_ts).total_seconds()
                    else:
                        signal_age_seconds = (datetime.utcnow() - received_ts).total_seconds()
                except Exception as e:
                    logger.debug(f"Could not parse timestamp from payload: {e}")
                    # Fallback: assume fresh if parsing fails (fail open)
                    signal_age_seconds = 0

        if signal_age_seconds > settings.staleness_seconds:
            # Signal is stale - discard it
            await self._discard_signal(
                user_id=user_id,
                signal=signal,
                reason="stale",
                age_ms=int(signal_age_seconds * 1000)
            )

            return GuardResult(
                decision=GuardDecision.SKIP,
                annotations={
                    "history_tag": "stale – skipped",
                    "discard_reason": "stale",
                    "age_seconds": signal_age_seconds
                }
            )

        return GuardResult(
            decision=GuardDecision.EXECUTE,
            annotations={}
        )

    async def _check_momentum(
        self,
        signal: Signal,
        settings: MomentumSettings,
        user_id: int,
        session_key: str
    ) -> GuardResult:
        """sg-001: Check signal momentum and detect chops"""
        # Get or create counter
        counter = self.db.query(SignalCounter).filter(
            and_(
                SignalCounter.user_id == user_id,
                SignalCounter.session_key == session_key
            )
        ).first()

        if not counter:
            # Initialize counter
            counter = SignalCounter(
                user_id=user_id,
                session_key=session_key,
                current_bias="none",
                opposite_momentum=0,
                last_signal_ts=None,
                last8_pattern="",
                chop_mode=False
            )
            self.db.add(counter)

        # Determine signal side
        signal_side = "buy" if signal.action == SignalAction.BUY else "sell"

        # Update bias and momentum
        if counter.current_bias == "none":
            # First signal - set bias
            counter.current_bias = signal_side
            counter.opposite_momentum = 0
        elif counter.current_bias == signal_side:
            # Same direction - reset opposite momentum
            counter.opposite_momentum = 0
        else:
            # Opposite direction - increment counter
            counter.opposite_momentum += 1

        # Update last signal timestamp
        counter.last_signal_ts = datetime.utcnow()

        # Update pattern for chop detection
        pattern_char = "B" if signal_side == "buy" else "S"
        if counter.last8_pattern:
            counter.last8_pattern = (counter.last8_pattern + pattern_char)[-8:]
        else:
            counter.last8_pattern = pattern_char

        # Check for chop mode (alternating pattern)
        if len(counter.last8_pattern) >= 6:
            alternations = sum(
                1 for i in range(len(counter.last8_pattern) - 1)
                if counter.last8_pattern[i] != counter.last8_pattern[i + 1]
            )
            if alternations >= 3:
                counter.chop_mode = True

        # Check if momentum threshold reached
        if counter.opposite_momentum >= settings.warn_at:
            # Warning modal required
            modal_data = {
                "type": "momentum_warning",
                "message": f"Market flipped? {counter.opposite_momentum} opposite signals while {counter.current_bias}. Breakeven? Close?",
                "count": counter.opposite_momentum,
                "current_bias": counter.current_bias,
                "opposite_bias": signal_side,
                "options": ["breakeven", "close", "ignore"]
            }

            self.db.commit()

            return GuardResult(
                decision=GuardDecision.WARN_MODAL_REQUIRED,
                annotations={
                    "history_tag": f"momentum_warning – {counter.opposite_momentum} opposite",
                    "momentum_count": counter.opposite_momentum,
                    "current_bias": counter.current_bias
                },
                updated_counters={
                    "opposite_momentum": counter.opposite_momentum,
                    "current_bias": counter.current_bias,
                    "chop_mode": counter.chop_mode
                },
                modal_data=modal_data
            )

        # Check chop mode pause
        if counter.chop_mode and settings.pause_on_chop:
            # Only pause NEW entries, allow closes/TP/SL
            if signal.action not in [SignalAction.CLOSE]:
                self.db.commit()
                return GuardResult(
                    decision=GuardDecision.PAUSE_NEW_ENTRIES,
                    annotations={
                        "history_tag": "chop_mode – paused new entries",
                        "chop_mode": True
                    },
                    updated_counters={
                        "opposite_momentum": counter.opposite_momentum,
                        "current_bias": counter.current_bias,
                        "chop_mode": counter.chop_mode
                    }
                )

        # Signal passes momentum check
        self.db.commit()
        return GuardResult(
            decision=GuardDecision.EXECUTE,
            annotations={},
            updated_counters={
                "opposite_momentum": counter.opposite_momentum,
                "current_bias": counter.current_bias,
                "chop_mode": counter.chop_mode
            }
        )

    async def _check_exposure(
        self,
        signal: Signal,
        settings: MomentumSettings,
        account_ids: List[int],
        open_positions_summary: Dict[int, Dict]
    ) -> GuardResult:
        """sg-004: Check max exposure limit"""
        if not settings.auto_pause_on_exposure:
            return GuardResult(
                decision=GuardDecision.EXECUTE,
                annotations={}
            )

        # Calculate total exposure across all accounts
        # Prefer positions table data, fallback to account.margin
        total_margin = 0.0
        for account_id in account_ids:
            if account_id in open_positions_summary:
                total_margin += open_positions_summary[account_id].get("total_margin", 0.0)
            else:
                # Fallback: query account directly
                account = self.db.query(TradingAccount).filter(
                    TradingAccount.id == account_id
                ).first()
                if account:
                    # Try to get actual positions if available
                    try:
                        from app.models.models import Position
                        positions = self.db.query(Position).filter(
                            Position.account_id == account_id,
                            Position.status == "open"
                        ).all()
                        if positions:
                            # Sum margin from actual positions
                            total_margin += sum(p.margin or 0.0 for p in positions)
                        else:
                            # Fallback to account margin
                            total_margin += account.margin or 0.0
                    except Exception as e:
                        logger.debug(f"Could not query positions for account {account_id}: {e}")
                        # Fallback to account margin
                        total_margin += account.margin or 0.0

        if total_margin >= settings.max_exposure:
            # Exposure limit hit
            modal_data = {
                "type": "exposure_warning",
                "message": f"Risk cap hit – pause? Current exposure: ${total_margin:.2f} / ${settings.max_exposure:.2f}",
                "current_exposure": total_margin,
                "max_exposure": settings.max_exposure,
                "options": ["pause", "continue"]
            }

            return GuardResult(
                decision=GuardDecision.PAUSE_NEW_ENTRIES,
                annotations={
                    "history_tag": "exposure_limit – paused new entries",
                    "total_margin": total_margin,
                    "max_exposure": settings.max_exposure
                },
                modal_data=modal_data
            )

        return GuardResult(
            decision=GuardDecision.EXECUTE,
            annotations={}
        )

    async def _discard_signal(
        self,
        user_id: int,
        signal: Signal,
        reason: str,
        age_ms: Optional[int] = None
    ):
        """sg-005: Record discarded signal in discard bin"""
        try:
            discard = DiscardBin(
                user_id=user_id,
                received_at=datetime.utcnow(),
                reason=reason,
                raw_signal_json=signal.raw_payload if signal.raw_payload else None,
                normalized_signal_json={
                    "symbol": signal.symbol.value if signal.symbol else None,
                    "action": signal.action.value if signal.action else None,
                    "volume": float(signal.volume.value) if signal.volume else None,
                    "price": float(signal.price.value) if signal.price else None,
                },
                age_ms=age_ms,
                broker_target=None,  # Will be set if known
                symbol=signal.symbol.value if signal.symbol else None,
                side="buy" if signal.action == SignalAction.BUY else "sell" if signal.action == SignalAction.SELL else None
            )
            self.db.add(discard)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to record discarded signal: {e}")
            self.db.rollback()

    def reset_counter(self, user_id: int, session_key: str):
        """Reset momentum counter (called on manual close, TP hit, or ignore)"""
        counter = self.db.query(SignalCounter).filter(
            and_(
                SignalCounter.user_id == user_id,
                SignalCounter.session_key == session_key
            )
        ).first()

        if counter:
            counter.current_bias = "none"
            counter.opposite_momentum = 0
            counter.last8_pattern = ""
            counter.chop_mode = False
            self.db.commit()

    async def flush_discard_bin(self, user_id: Optional[int] = None):
        """sg-005: Flush old discard bin entries"""
        try:
            # Get flush interval from settings
            if user_id:
                settings = self._get_momentum_settings(user_id)
                flush_interval = settings.discard_flush_interval
            else:
                flush_interval = "24h"  # Default

            # Parse interval
            if flush_interval.endswith("h"):
                hours = int(flush_interval[:-1])
                cutoff = datetime.utcnow() - timedelta(hours=hours)
            elif flush_interval.endswith("d"):
                days = int(flush_interval[:-1])
                cutoff = datetime.utcnow() - timedelta(days=days)
            else:
                cutoff = datetime.utcnow() - timedelta(hours=24)  # Default 24h

            # Delete old entries
            query = self.db.query(DiscardBin).filter(
                DiscardBin.received_at < cutoff
            )
            if user_id:
                query = query.filter(DiscardBin.user_id == user_id)

            deleted_count = query.delete()
            self.db.commit()

            logger.info(f"Flushed {deleted_count} discard bin entries older than {flush_interval}")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to flush discard bin: {e}")
            self.db.rollback()
            return 0
