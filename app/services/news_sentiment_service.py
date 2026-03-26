"""
News Sentiment Service - Alternative Data Edge
===============================================

Lightweight news/sentiment proxy for non-TA alpha:
- NewsAPI for hourly headlines
- Keyword sentiment scoring (fast, no LLM required)
- Optional LLM prompt for deeper analysis (Anthropic/OpenAI)
- Social sentiment from X/Twitter semantic search

Pi5 optimized:
- Keyword scoring: <10ms
- LLM analysis: Optional, async, cached

2026 Edge: Pure price/volume/flow is saturated.
News events often lead price by minutes.
"""

import logging
import aiohttp
import asyncio
import os
import re
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import Anthropic for LLM analysis
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None


class SentimentLevel(Enum):
    """Sentiment levels"""
    VERY_BULLISH = "very_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    VERY_BEARISH = "very_bearish"


@dataclass
class NewsArticle:
    """Single news article"""
    title: str
    description: str
    source: str
    url: str
    published_at: datetime
    ticker: Optional[str] = None

    # Sentiment scores
    keyword_sentiment: float = 0.0  # -1 to +1
    llm_sentiment: Optional[float] = None
    combined_sentiment: float = 0.0

    # Relevance
    relevance_score: float = 0.0  # 0-1


@dataclass
class NewsSentimentAnalysis:
    """Complete news sentiment analysis"""
    ticker: str
    timestamp: datetime

    # Articles
    articles: List[NewsArticle] = field(default_factory=list)
    article_count: int = 0

    # Aggregated sentiment
    avg_sentiment: float = 0.0  # -1 to +1
    sentiment_level: SentimentLevel = SentimentLevel.NEUTRAL
    sentiment_confidence: float = 0.0  # 0-1

    # Momentum
    sentiment_change_1h: float = 0.0
    sentiment_zscore: float = 0.0

    # Key topics
    top_keywords: List[str] = field(default_factory=list)
    has_breaking_news: bool = False

    # Ensemble features
    features: Dict[str, float] = field(default_factory=dict)


@dataclass
class SentimentConfig:
    """Configuration for news sentiment service"""
    # NewsAPI
    newsapi_key: str = ""
    newsapi_base_url: str = "https://newsapi.org/v2"

    # Ensemble boost settings (ENHANCED)
    sentiment_threshold: float = 0.5        # Min sentiment for boost
    boost_min: float = 0.08                 # Min +8% probability boost
    boost_max: float = 0.12                 # Max +12% probability boost
    flow_require: str = 'MEDIUM'            # Min flow for boost to apply

    # Ticker to keyword mapping
    ticker_keywords: Dict[str, List[str]] = field(default_factory=lambda: {
        'MES': ['S&P 500', 'SPX', 'ES futures', 'stock market'],
        'NQ': ['Nasdaq', 'tech stocks', 'QQQ', 'NQ futures'],
        'RTY': ['Russell 2000', 'small cap', 'IWM'],
        'GC': ['gold', 'precious metals', 'gold futures'],
        'CL': ['crude oil', 'oil prices', 'WTI'],
        'SPY': ['S&P 500', 'SPY', 'stock market', 'equities'],
        'QQQ': ['Nasdaq', 'tech stocks', 'QQQ', 'technology'],
        'BTCUSD': ['Bitcoin', 'BTC', 'cryptocurrency', 'crypto'],
        'ETHUSD': ['Ethereum', 'ETH', 'cryptocurrency', 'DeFi'],
    })

    # Sentiment keywords (scaled by importance)
    bullish_keywords: Dict[str, float] = field(default_factory=lambda: {
        'surge': 1.0, 'soar': 1.0, 'rally': 0.8, 'gain': 0.5,
        'bullish': 1.0, 'breakout': 0.8, 'highs': 0.6, 'record': 0.7,
        'strong': 0.5, 'growth': 0.5, 'beat': 0.6, 'optimism': 0.7,
        'recovery': 0.6, 'upgrade': 0.7, 'outperform': 0.8,
        'buy': 0.5, 'accumulate': 0.6, 'boom': 0.9,
    })

    bearish_keywords: Dict[str, float] = field(default_factory=lambda: {
        'crash': 1.0, 'plunge': 1.0, 'selloff': 0.9, 'drop': 0.6,
        'bearish': 1.0, 'breakdown': 0.8, 'lows': 0.6, 'fear': 0.7,
        'weak': 0.5, 'decline': 0.5, 'miss': 0.6, 'recession': 0.9,
        'correction': 0.6, 'downgrade': 0.7, 'underperform': 0.8,
        'sell': 0.5, 'dump': 0.8, 'crisis': 1.0, 'collapse': 1.0,
    })

    # Breaking news patterns
    breaking_patterns: List[str] = field(default_factory=lambda: [
        'breaking:', 'urgent:', 'just in:', 'flash:',
        'breaking news', 'developing story'
    ])

    # LLM config (optional)
    use_llm: bool = False
    llm_model: str = "claude-3-haiku-20240307"  # Fast and cheap
    llm_cache_minutes: int = 30

    # Update intervals
    news_fetch_interval_minutes: int = 15
    sentiment_history_hours: int = 24

    # Thresholds
    relevance_threshold: float = 0.3
    strong_sentiment_threshold: float = 0.5


class NewsSentimentService:
    """
    News and sentiment analysis service.

    Provides alternative alpha from news events:
    - Keyword-based fast sentiment (no API calls)
    - NewsAPI headlines fetching
    - Optional LLM deeper analysis
    - Sentiment momentum tracking
    """

    def __init__(self, config: Optional[SentimentConfig] = None):
        self.config = config or SentimentConfig()

        # Load API keys from environment
        self.config.newsapi_key = os.getenv('NEWSAPI_KEY', '')
        self.anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')

        # HTTP session
        self.session: Optional[aiohttp.ClientSession] = None

        # Anthropic client
        self.anthropic_client = None
        if ANTHROPIC_AVAILABLE and self.anthropic_key:
            self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_key)

        # Cache
        self.article_cache: Dict[str, List[NewsArticle]] = {}
        self.sentiment_cache: Dict[str, NewsSentimentAnalysis] = {}
        self.llm_cache: Dict[str, Tuple[float, datetime]] = {}  # (sentiment, timestamp)

        # History for z-scores
        self.sentiment_history: Dict[str, deque] = {}
        self.max_history = 500

        # Last fetch times
        self.last_fetch: Dict[str, datetime] = {}

        logger.info(
            f"NewsSentimentService initialized: "
            f"NewsAPI={'configured' if self.config.newsapi_key else 'not configured'}, "
            f"LLM={'enabled' if self.anthropic_client else 'disabled'}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def close(self):
        """Close session."""
        if self.session and not self.session.closed:
            await self.session.close()

    # ========================================
    # NEWS FETCHING
    # ========================================

    async def fetch_news(
        self,
        ticker: str,
        hours_back: int = 4
    ) -> List[NewsArticle]:
        """
        Fetch news articles for a ticker from NewsAPI.

        Args:
            ticker: Symbol to search for
            hours_back: How many hours back to search

        Returns:
            List of NewsArticle objects
        """
        if not self.config.newsapi_key:
            logger.debug("NewsAPI key not configured, using mock data")
            return self._generate_mock_articles(ticker)

        try:
            session = await self._get_session()

            # Get keywords for this ticker
            keywords = self.config.ticker_keywords.get(ticker, [ticker])
            query = ' OR '.join(f'"{kw}"' for kw in keywords)

            # Calculate time range
            from_time = datetime.utcnow() - timedelta(hours=hours_back)

            url = f"{self.config.newsapi_base_url}/everything"
            params = {
                'q': query,
                'from': from_time.isoformat(),
                'sortBy': 'publishedAt',
                'language': 'en',
                'pageSize': 50,
                'apiKey': self.config.newsapi_key
            }

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    logger.warning(f"NewsAPI returned {response.status}")
                    return []

                data = await response.json()

                articles = []
                for item in data.get('articles', []):
                    article = NewsArticle(
                        title=item.get('title', ''),
                        description=item.get('description', '') or '',
                        source=item.get('source', {}).get('name', ''),
                        url=item.get('url', ''),
                        published_at=self._parse_datetime(item.get('publishedAt', '')),
                        ticker=ticker
                    )

                    # Score sentiment
                    article.keyword_sentiment = self._score_keyword_sentiment(
                        article.title + ' ' + article.description
                    )

                    # Score relevance
                    article.relevance_score = self._score_relevance(
                        article.title + ' ' + article.description,
                        keywords
                    )

                    # Check for breaking news
                    if self._is_breaking_news(article.title):
                        article.relevance_score = min(1.0, article.relevance_score + 0.3)

                    if article.relevance_score >= self.config.relevance_threshold:
                        articles.append(article)

                # Cache
                self.article_cache[ticker] = articles
                self.last_fetch[ticker] = datetime.now()

                logger.info(
                    f"📰 News {ticker}: fetched {len(articles)} articles "
                    f"(avg sentiment: {sum(a.keyword_sentiment for a in articles)/len(articles) if articles else 0:.2f})"
                )

                return articles

        except Exception as e:
            logger.error(f"News fetch failed for {ticker}: {e}")
            return []

    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse datetime string from NewsAPI."""
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return datetime.now()

    def _generate_mock_articles(self, ticker: str) -> List[NewsArticle]:
        """Generate mock articles for testing."""
        import random

        articles = []
        now = datetime.now()

        headlines = [
            ("Markets rally on strong economic data", 0.6),
            ("Tech stocks lead gains amid optimism", 0.5),
            ("Traders cautious ahead of Fed decision", 0.0),
            ("Volatility spikes as uncertainty grows", -0.3),
            ("Strong earnings beat expectations", 0.7),
        ]

        for headline, sentiment in random.sample(headlines, min(3, len(headlines))):
            article = NewsArticle(
                title=headline,
                description=f"Details about {headline.lower()}...",
                source="Mock News",
                url="https://example.com",
                published_at=now - timedelta(minutes=random.randint(10, 180)),
                ticker=ticker,
                keyword_sentiment=sentiment + random.uniform(-0.1, 0.1),
                relevance_score=random.uniform(0.5, 0.9)
            )
            articles.append(article)

        return articles

    # ========================================
    # KEYWORD SENTIMENT (Fast, No API)
    # ========================================

    def _score_keyword_sentiment(self, text: str) -> float:
        """
        Score sentiment using keyword matching.

        Fast, deterministic, no API calls.

        Returns: -1 (bearish) to +1 (bullish)
        """
        text_lower = text.lower()

        bullish_score = 0.0
        bearish_score = 0.0

        # Match bullish keywords
        for keyword, weight in self.config.bullish_keywords.items():
            if keyword in text_lower:
                bullish_score += weight

        # Match bearish keywords
        for keyword, weight in self.config.bearish_keywords.items():
            if keyword in text_lower:
                bearish_score += weight

        # Net sentiment
        total = bullish_score + bearish_score
        if total == 0:
            return 0.0

        sentiment = (bullish_score - bearish_score) / total
        return max(-1.0, min(1.0, sentiment))

    def _score_relevance(self, text: str, keywords: List[str]) -> float:
        """Score relevance of text to keywords."""
        text_lower = text.lower()

        matches = sum(1 for kw in keywords if kw.lower() in text_lower)
        return min(1.0, matches / len(keywords)) if keywords else 0.0

    def _is_breaking_news(self, title: str) -> bool:
        """Check if title indicates breaking news."""
        title_lower = title.lower()
        return any(pattern in title_lower for pattern in self.config.breaking_patterns)

    # ========================================
    # LLM SENTIMENT (Optional, Deeper Analysis)
    # ========================================

    async def analyze_with_llm(
        self,
        text: str,
        ticker: str
    ) -> Optional[float]:
        """
        Analyze sentiment using LLM (Claude).

        Cached to avoid repeated API calls.

        Returns: -1 (bearish) to +1 (bullish), or None if unavailable
        """
        if not self.anthropic_client or not self.config.use_llm:
            return None

        # Check cache
        cache_key = f"{ticker}:{hash(text)}"
        if cache_key in self.llm_cache:
            cached_sentiment, cached_time = self.llm_cache[cache_key]
            if datetime.now() - cached_time < timedelta(minutes=self.config.llm_cache_minutes):
                return cached_sentiment

        try:
            prompt = f"""Analyze the market sentiment of this news headline for {ticker}.
Return ONLY a number from -1.0 (very bearish) to +1.0 (very bullish).
0 means neutral.

Headline: {text}

Sentiment score (just the number):"""

            message = self.anthropic_client.messages.create(
                model=self.config.llm_model,
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            response_text = message.content[0].text.strip()
            sentiment = float(response_text)
            sentiment = max(-1.0, min(1.0, sentiment))

            # Cache
            self.llm_cache[cache_key] = (sentiment, datetime.now())

            return sentiment

        except Exception as e:
            logger.debug(f"LLM sentiment analysis failed: {e}")
            return None

    # ========================================
    # COMBINED ANALYSIS
    # ========================================

    async def analyze(
        self,
        ticker: str,
        force_refresh: bool = False
    ) -> NewsSentimentAnalysis:
        """
        Run complete news sentiment analysis.

        Args:
            ticker: Symbol to analyze
            force_refresh: Force fetch new articles

        Returns:
            NewsSentimentAnalysis with all metrics
        """
        now = datetime.now()

        analysis = NewsSentimentAnalysis(
            ticker=ticker,
            timestamp=now
        )

        # Check if refresh needed
        last_fetch = self.last_fetch.get(ticker)
        should_fetch = (
            force_refresh or
            last_fetch is None or
            (now - last_fetch).total_seconds() > self.config.news_fetch_interval_minutes * 60
        )

        # Get articles
        if should_fetch:
            articles = await self.fetch_news(ticker)
        else:
            articles = self.article_cache.get(ticker, [])

        analysis.articles = articles
        analysis.article_count = len(articles)

        if not articles:
            return analysis

        # Calculate aggregate sentiment
        sentiments = [a.keyword_sentiment for a in articles]
        relevances = [a.relevance_score for a in articles]

        # Weighted average by relevance
        total_relevance = sum(relevances)
        if total_relevance > 0:
            analysis.avg_sentiment = sum(
                s * r for s, r in zip(sentiments, relevances)
            ) / total_relevance
        else:
            analysis.avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0

        # Determine sentiment level
        if analysis.avg_sentiment > self.config.strong_sentiment_threshold:
            analysis.sentiment_level = SentimentLevel.VERY_BULLISH
        elif analysis.avg_sentiment > 0.2:
            analysis.sentiment_level = SentimentLevel.BULLISH
        elif analysis.avg_sentiment < -self.config.strong_sentiment_threshold:
            analysis.sentiment_level = SentimentLevel.VERY_BEARISH
        elif analysis.avg_sentiment < -0.2:
            analysis.sentiment_level = SentimentLevel.BEARISH
        else:
            analysis.sentiment_level = SentimentLevel.NEUTRAL

        # Confidence based on article count and agreement
        sentiment_std = (
            sum((s - analysis.avg_sentiment) ** 2 for s in sentiments) / len(sentiments)
        ) ** 0.5 if len(sentiments) > 1 else 0

        analysis.sentiment_confidence = min(1.0, (
            min(len(articles), 10) / 10 *  # More articles = more confidence
            max(0, 1 - sentiment_std)  # Less variance = more confidence
        ))

        # Track history for z-score
        if ticker not in self.sentiment_history:
            self.sentiment_history[ticker] = deque(maxlen=self.max_history)
        self.sentiment_history[ticker].append(analysis.avg_sentiment)

        # Calculate z-score
        history = list(self.sentiment_history[ticker])
        if len(history) >= 10:
            import numpy as np
            mean = np.mean(history)
            std = np.std(history)
            if std > 0:
                analysis.sentiment_zscore = (analysis.avg_sentiment - mean) / std

        # Check for breaking news
        analysis.has_breaking_news = any(
            self._is_breaking_news(a.title) for a in articles
        )

        # Extract top keywords
        analysis.top_keywords = self._extract_top_keywords(articles)

        # Build features
        analysis.features = self._build_features(analysis)

        # Cache
        self.sentiment_cache[ticker] = analysis

        logger.info(
            f"📰 Sentiment {ticker}: {analysis.sentiment_level.value} "
            f"(avg={analysis.avg_sentiment:.2f}, confidence={analysis.sentiment_confidence:.2f}, "
            f"articles={len(articles)}, breaking={analysis.has_breaking_news})"
        )

        return analysis

    def _extract_top_keywords(
        self,
        articles: List[NewsArticle],
        top_n: int = 5
    ) -> List[str]:
        """Extract most frequent meaningful words from articles."""
        # Simple frequency-based extraction
        word_counts: Dict[str, int] = {}

        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                    'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                    'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                    'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                    'through', 'during', 'before', 'after', 'above', 'below',
                    'between', 'under', 'again', 'further', 'then', 'once',
                    'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                    'neither', 'not', 'only', 'own', 'same', 'than', 'too',
                    'very', 'just', 'also', 'now', 'here', 'there', 'when',
                    'where', 'why', 'how', 'all', 'each', 'every', 'both',
                    'few', 'more', 'most', 'other', 'some', 'such', 'no',
                    'any', 'this', 'that', 'these', 'those', 'it', 'its'}

        for article in articles:
            text = (article.title + ' ' + article.description).lower()
            words = re.findall(r'\b[a-z]+\b', text)

            for word in words:
                if word not in stopwords and len(word) > 3:
                    word_counts[word] = word_counts.get(word, 0) + 1

        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:top_n]]

    def _build_features(self, analysis: NewsSentimentAnalysis) -> Dict[str, float]:
        """Build feature dict for ML ensemble."""
        import numpy as np

        features = {}

        # Sentiment features
        features['news_sentiment'] = analysis.avg_sentiment
        features['news_sentiment_abs'] = abs(analysis.avg_sentiment)
        features['news_sentiment_zscore'] = np.clip(analysis.sentiment_zscore / 3, -1, 1)
        features['news_confidence'] = analysis.sentiment_confidence

        # Sentiment level encoding
        features['sentiment_very_bullish'] = 1.0 if analysis.sentiment_level == SentimentLevel.VERY_BULLISH else 0.0
        features['sentiment_bullish'] = 1.0 if analysis.sentiment_level == SentimentLevel.BULLISH else 0.0
        features['sentiment_bearish'] = 1.0 if analysis.sentiment_level == SentimentLevel.BEARISH else 0.0
        features['sentiment_very_bearish'] = 1.0 if analysis.sentiment_level == SentimentLevel.VERY_BEARISH else 0.0

        # Article features
        features['article_count_norm'] = min(analysis.article_count / 20, 1.0)
        features['has_breaking_news'] = 1.0 if analysis.has_breaking_news else 0.0

        return features

    def get_cached_sentiment(self, ticker: str) -> Optional[NewsSentimentAnalysis]:
        """Get cached sentiment analysis if available."""
        return self.sentiment_cache.get(ticker)

    async def analyze_all(
        self,
        tickers: Optional[List[str]] = None
    ) -> Dict[str, NewsSentimentAnalysis]:
        """Analyze sentiment for multiple tickers."""
        if tickers is None:
            tickers = list(self.config.ticker_keywords.keys())

        results = {}
        for ticker in tickers:
            try:
                results[ticker] = await self.analyze(ticker)
            except Exception as e:
                logger.error(f"Sentiment analysis failed for {ticker}: {e}")

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get service status."""
        return {
            'newsapi_configured': bool(self.config.newsapi_key),
            'llm_enabled': self.anthropic_client is not None and self.config.use_llm,
            'cached_articles': {k: len(v) for k, v in self.article_cache.items()},
            'cached_sentiment': list(self.sentiment_cache.keys()),
            'llm_cache_size': len(self.llm_cache),
        }


# Global instance
_news_sentiment_service: Optional[NewsSentimentService] = None


async def get_news_sentiment_service() -> NewsSentimentService:
    """Get or create global news sentiment service."""
    global _news_sentiment_service
    if _news_sentiment_service is None:
        _news_sentiment_service = NewsSentimentService()
    return _news_sentiment_service


def get_sentiment_features_for_ensemble(
    analysis: NewsSentimentAnalysis,
    direction: str,
    flow_conviction: str,
    config: Optional[SentimentConfig] = None
) -> Dict[str, float]:
    """
    Get sentiment features formatted for ensemble scorer.

    Applies the 0.08-0.12 boost when:
    - sentiment > 0.5 AND
    - flow >= MEDIUM AND
    - direction aligns with sentiment

    Returns dict with:
    - news_sentiment: Aggregate sentiment score (-1 to +1)
    - news_boost: Probability boost amount (0.08-0.12 when conditions met)
    - news_headline_count: Number of headlines
    """
    config = config or SentimentConfig()

    # Check flow requirement
    flow_levels = ['MEDIUM', 'HIGH', 'EXTREME']
    if config.flow_require == 'HIGH':
        flow_levels = ['HIGH', 'EXTREME']
    flow_ok = flow_conviction.upper() in flow_levels

    # Direction alignment
    direction_aligned = (
        (direction == 'buy' and analysis.avg_sentiment > 0) or
        (direction == 'sell' and analysis.avg_sentiment < 0)
    )

    # Calculate effective boost
    effective_boost = 0.0
    if direction_aligned and flow_ok and abs(analysis.avg_sentiment) >= config.sentiment_threshold:
        # Scale boost between min and max based on sentiment strength
        sentiment_strength = min(abs(analysis.avg_sentiment), 1.0)
        effective_boost = config.boost_min + \
            (config.boost_max - config.boost_min) * \
            (sentiment_strength - config.sentiment_threshold) / \
            (1.0 - config.sentiment_threshold)

    return {
        'news_sentiment': analysis.avg_sentiment,
        'news_boost': effective_boost,
        'news_headline_count': float(analysis.article_count),
        'news_confidence': analysis.sentiment_confidence,
        'news_has_breaking': 1.0 if analysis.has_breaking_news else 0.0
    }
