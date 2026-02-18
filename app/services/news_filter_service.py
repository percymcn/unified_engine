"""
News Filter Service

Filters trades based on economic calendar events.
Fetches news from free APIs and pauses trading around high-impact events.
"""
import logging
import aiohttp
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
import pytz

from app.models.database_models import NewsEvent, NewsFilterSettings

logger = logging.getLogger(__name__)

# Mapping of currencies to symbols they affect
CURRENCY_SYMBOL_MAP = {
    'USD': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'AUDUSD', 'NZDUSD',
            'XAUUSD', 'US30', 'US500', 'USTEC', 'NAS100', 'SPX500', 'ES', 'NQ', 'YM',
            'MES', 'MNQ', 'MYM', 'BTCUSD'],
    'EUR': ['EURUSD', 'EURJPY', 'EURGBP', 'EURCHF', 'EURAUD', 'EURCAD', 'GER40', 'DE40'],
    'GBP': ['GBPUSD', 'EURGBP', 'GBPJPY', 'GBPCHF', 'GBPAUD', 'UK100'],
    'JPY': ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'JP225', 'NIKKEI'],
    'AUD': ['AUDUSD', 'EURAUD', 'GBPAUD', 'AUDJPY', 'AUDNZD', 'AUS200'],
    'CAD': ['USDCAD', 'EURCAD', 'GBPCAD', 'AUDCAD', 'CADJPY', 'OIL', 'USOIL'],
    'CHF': ['USDCHF', 'EURCHF', 'GBPCHF', 'CHFJPY'],
    'NZD': ['NZDUSD', 'EURNZD', 'GBPNZD', 'NZDJPY', 'AUDNZD'],
    'CNH': ['USDCNH', 'EURCNH', 'CNHJPY', 'HK50'],
}

# High-impact events that always trigger filtering
HIGH_IMPACT_EVENTS = [
    'FOMC', 'Fed', 'Interest Rate', 'NFP', 'Non-Farm', 'Nonfarm',
    'CPI', 'Inflation', 'GDP', 'Employment', 'Unemployment',
    'PMI', 'Retail Sales', 'Trade Balance', 'ECB', 'BOE', 'BOJ',
    'RBA', 'RBNZ', 'SNB', 'BOC'
]


class NewsFilterService:
    """
    Service for filtering trades based on economic news events.
    """

    def __init__(self, db: Session):
        self.db = db
        self._cache: Dict[str, Any] = {}
        self._cache_expiry: Optional[datetime] = None

    async def should_allow_trade(
        self,
        user_id: int,
        symbol: str
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Check if a trade should be allowed based on upcoming news.

        Returns:
            (should_allow, reason_if_blocked, upcoming_event)
        """
        # Get user settings
        settings = self.db.query(NewsFilterSettings).filter(
            NewsFilterSettings.user_id == user_id
        ).first()

        if not settings or not settings.enabled:
            return True, None, None

        # Normalize symbol for matching
        normalized_symbol = self._normalize_symbol(symbol)

        # Get upcoming events
        now = datetime.now(pytz.UTC)
        events = await self._get_upcoming_events(
            start_time=now - timedelta(minutes=settings.pause_minutes_after),
            end_time=now + timedelta(minutes=settings.pause_minutes_before)
        )

        for event in events:
            # Check if event affects this symbol
            if not self._event_affects_symbol(event, normalized_symbol, settings):
                continue

            # Check impact level filter
            if event.get('impact') == 'high' and not settings.filter_high_impact:
                continue
            if event.get('impact') == 'medium' and not settings.filter_medium_impact:
                continue
            if event.get('impact') == 'low' and not settings.filter_low_impact:
                continue

            # Calculate time difference
            event_time = event.get('datetime')
            if event_time:
                time_diff = (event_time - now).total_seconds() / 60  # minutes

                # Check if within blackout window
                if -settings.pause_minutes_after <= time_diff <= settings.pause_minutes_before:
                    reason = f"News event: {event.get('title')} ({event.get('country')}) in {int(time_diff)} min"

                    if settings.action_on_news == 'pause':
                        return False, reason, event
                    elif settings.action_on_news == 'warn_only':
                        logger.warning(f"News warning for {symbol}: {reason}")
                        return True, None, event

        return True, None, None

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol for matching (remove suffixes like .pro, 1!, etc.)."""
        symbol = symbol.upper()
        # Remove common suffixes
        for suffix in ['.PRO', '.STD', '1!', '!', '.Z', '.F', '_SB']:
            symbol = symbol.replace(suffix, '')
        return symbol

    def _event_affects_symbol(
        self,
        event: Dict,
        symbol: str,
        settings: NewsFilterSettings
    ) -> bool:
        """Check if an economic event affects a given symbol."""
        country = event.get('country', '').upper()

        # Check if we're filtering this currency
        if settings.filter_currencies and country not in settings.filter_currencies:
            return False

        # Check against affected symbols from event
        affected = event.get('affected_symbols', [])
        if affected:
            return symbol in affected or any(s in symbol for s in affected)

        # Fall back to currency mapping
        affected_from_currency = CURRENCY_SYMBOL_MAP.get(country, [])
        return symbol in affected_from_currency or any(s in symbol for s in affected_from_currency)

    async def _get_upcoming_events(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """
        Get upcoming news events from cache or API.
        Uses FXStreet/ForexFactory style free APIs.
        """
        # Check cache
        if self._cache_expiry and datetime.now(pytz.UTC) < self._cache_expiry:
            events = self._cache.get('events', [])
            return [e for e in events
                    if start_time <= e.get('datetime', datetime.min.replace(tzinfo=pytz.UTC)) <= end_time]

        # Fetch from database first (pre-populated events)
        db_events = self.db.query(NewsEvent).filter(
            NewsEvent.event_datetime >= start_time,
            NewsEvent.event_datetime <= end_time
        ).all()

        if db_events:
            events = [{
                'id': e.event_id,
                'title': e.title,
                'country': e.country,
                'datetime': e.event_datetime,
                'impact': e.impact,
                'affected_symbols': e.affected_symbols or [],
                'forecast': e.forecast,
                'previous': e.previous,
                'actual': e.actual
            } for e in db_events]
            return events

        # Try to fetch from free API
        try:
            events = await self._fetch_events_from_api()
            self._cache['events'] = events
            self._cache_expiry = datetime.now(pytz.UTC) + timedelta(minutes=15)

            return [e for e in events
                    if start_time <= e.get('datetime', datetime.min.replace(tzinfo=pytz.UTC)) <= end_time]
        except Exception as ex:
            logger.error(f"Failed to fetch news events: {ex}")
            return []

    async def _fetch_events_from_api(self) -> List[Dict]:
        """
        Fetch economic events from a free API.
        Using a simple approach with fallback.
        """
        events = []

        try:
            # Try ForexFactory-style scraping or alternative free API
            # Note: In production, you'd want to use a proper API
            async with aiohttp.ClientSession() as session:
                # Using a public economic calendar API (example)
                url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        for item in data:
                            try:
                                # Parse the event
                                event_dt = datetime.fromisoformat(
                                    item.get('date', '').replace('Z', '+00:00')
                                )

                                impact = 'low'
                                impact_str = item.get('impact', '').lower()
                                if 'high' in impact_str or impact_str == 'red':
                                    impact = 'high'
                                elif 'medium' in impact_str or impact_str == 'orange':
                                    impact = 'medium'

                                title = item.get('title', '')
                                country = item.get('country', 'USD')

                                # Determine affected symbols
                                affected = CURRENCY_SYMBOL_MAP.get(country.upper(), [])

                                events.append({
                                    'id': f"{country}_{event_dt.timestamp()}",
                                    'title': title,
                                    'country': country.upper(),
                                    'datetime': event_dt,
                                    'impact': impact,
                                    'affected_symbols': affected,
                                    'forecast': item.get('forecast'),
                                    'previous': item.get('previous'),
                                    'actual': item.get('actual')
                                })
                            except Exception as e:
                                logger.debug(f"Error parsing event: {e}")
                                continue

        except Exception as ex:
            logger.warning(f"Could not fetch news from API: {ex}")

        return events

    async def refresh_news_cache(self):
        """Force refresh of news cache."""
        self._cache_expiry = None
        await self._get_upcoming_events(
            start_time=datetime.now(pytz.UTC) - timedelta(hours=1),
            end_time=datetime.now(pytz.UTC) + timedelta(hours=24)
        )

    def get_settings(self, user_id: int) -> Optional[NewsFilterSettings]:
        """Get user's news filter settings."""
        return self.db.query(NewsFilterSettings).filter(
            NewsFilterSettings.user_id == user_id
        ).first()

    def update_settings(self, user_id: int, **kwargs) -> NewsFilterSettings:
        """Update user's news filter settings."""
        settings = self.get_settings(user_id)

        if not settings:
            settings = NewsFilterSettings(user_id=user_id)
            self.db.add(settings)

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        self.db.commit()
        self.db.refresh(settings)
        return settings

    def get_upcoming_events_sync(
        self,
        hours_ahead: int = 24,
        impact_filter: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Synchronous method to get upcoming events from database.
        """
        now = datetime.now(pytz.UTC)
        end_time = now + timedelta(hours=hours_ahead)

        query = self.db.query(NewsEvent).filter(
            NewsEvent.event_datetime >= now,
            NewsEvent.event_datetime <= end_time
        )

        if impact_filter:
            query = query.filter(NewsEvent.impact.in_(impact_filter))

        events = query.order_by(NewsEvent.event_datetime).all()

        return [{
            'id': e.event_id,
            'title': e.title,
            'country': e.country,
            'datetime': e.event_datetime.isoformat(),
            'impact': e.impact,
            'forecast': e.forecast,
            'previous': e.previous,
            'actual': e.actual
        } for e in events]
