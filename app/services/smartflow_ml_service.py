"""
SmartFlow ML Service
====================

Self-learning machine learning service for SmartFlow Indicator.
Learns from signal outcomes to improve win rate over time.

Features:
- Pattern Recognition: Learn which flow patterns precede winners
- Adaptive Thresholds: Auto-tune FSS thresholds based on outcomes
- Market Regime Detection: Identify trending/ranging/volatile conditions
- Time Optimization: Learn best trading hours/days
- Confidence Calibration: Weight signals by historical accuracy
- Cross-Ticker Correlation: Detect when multiple tickers align
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import statistics
import json

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

logger = logging.getLogger(__name__)


class SmartFlowMLService:
    """
    Machine Learning service for SmartFlow that learns from outcomes
    and continuously improves signal quality.
    """

    # Pattern feature extraction settings
    PATTERN_FEATURES = [
        'flow_count', 'total_premium', 'bullish_ratio', 'bearish_ratio',
        'sweep_ratio', 'block_ratio', 'avg_premium', 'premium_velocity',
        'hour_of_day', 'day_of_week', 'vix_level'
    ]

    # Confidence calculation weights
    BASE_CONFIDENCE = 50.0
    PATTERN_MATCH_BOOST = 15.0
    TIME_OPTIMIZATION_BOOST = 10.0
    REGIME_ALIGNMENT_BOOST = 10.0
    CORRELATION_BOOST = 15.0

    # Learning parameters
    MIN_SAMPLES_FOR_LEARNING = 20
    ROLLING_WINDOW_SIZE = 50
    RETRAIN_INTERVAL_HOURS = 24

    def __init__(self, db: Session):
        self.db = db

    # ========================================
    # SIGNAL OUTCOME TRACKING
    # ========================================

    async def record_signal_outcome(
        self,
        signal_log_id: int,
        trade_executed: bool,
        entry_price: Optional[float] = None,
        exit_price: Optional[float] = None,
        pnl: Optional[float] = None,
        time_in_trade: Optional[int] = None,
        max_favorable: Optional[float] = None,
        max_adverse: Optional[float] = None
    ) -> Dict:
        """
        Record the outcome of a SmartFlow signal.
        This is the feedback loop that enables learning.
        """
        from app.models.smartflow_models import SmartFlowSignalLog

        try:
            # Import here to avoid circular imports
            from sqlalchemy import text

            # Get the original signal
            signal = self.db.query(SmartFlowSignalLog).filter(
                SmartFlowSignalLog.id == signal_log_id
            ).first()

            if not signal:
                return {"error": "Signal not found"}

            # Calculate derived metrics
            is_winner = pnl > 0 if pnl is not None else None
            pnl_percent = None
            if pnl is not None and entry_price and entry_price != 0:
                # Use realized P&L whenever available so long/short direction and partial sizing
                # do not corrupt percentage performance stats.
                pnl_percent = (pnl / entry_price) * 100

            # Get current market context
            hour_of_day = datetime.utcnow().hour
            day_of_week = datetime.utcnow().weekday()

            # Extract flow pattern for learning
            flow_pattern = self._extract_flow_pattern(signal)

            # Detect current market regime
            regime = await self._detect_market_regime(signal.ticker)

            # Insert outcome record
            outcome_query = text("""
                INSERT INTO smartflow_signal_outcomes
                (signal_log_id, trade_executed, entry_price, exit_price, pnl, pnl_percent,
                 is_winner, time_in_trade, max_favorable_excursion, max_adverse_excursion,
                 market_regime, hour_of_day, day_of_week, flow_pattern)
                VALUES (:signal_log_id, :trade_executed, :entry_price, :exit_price, :pnl,
                        :pnl_percent, :is_winner, :time_in_trade, :max_favorable, :max_adverse,
                        :market_regime, :hour_of_day, :day_of_week, :flow_pattern)
                RETURNING id
            """)

            result = self.db.execute(outcome_query, {
                "signal_log_id": signal_log_id,
                "trade_executed": trade_executed,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_percent": pnl_percent,
                "is_winner": is_winner,
                "time_in_trade": time_in_trade,
                "max_favorable": max_favorable,
                "max_adverse": max_adverse,
                "market_regime": regime.get("regime") if regime else None,
                "hour_of_day": hour_of_day,
                "day_of_week": day_of_week,
                "flow_pattern": json.dumps(flow_pattern)
            })

            outcome_id = result.fetchone()[0]
            self.db.commit()

            # Trigger learning update
            await self._update_model_from_outcome(signal.ticker, is_winner, pnl, hour_of_day, day_of_week, regime)

            # Update daily metrics
            await self._update_daily_metrics(signal.ticker, is_winner, pnl)

            return {
                "outcome_id": outcome_id,
                "is_winner": is_winner,
                "pnl": pnl,
                "learning_triggered": True
            }

        except Exception as e:
            logger.error(f"Error recording signal outcome: {e}")
            self.db.rollback()
            return {"error": str(e)}

    def _extract_flow_pattern(self, signal) -> Dict:
        """Extract features from a signal for pattern learning."""
        return {
            "score": signal.score,
            "bullish_flows": signal.bullish_flows,
            "bearish_flows": signal.bearish_flows,
            "total_premium": signal.total_premium,
            "action": signal.action,
            "hour": datetime.utcnow().hour,
            "day": datetime.utcnow().weekday()
        }

    # ========================================
    # ADAPTIVE THRESHOLDS
    # ========================================

    async def get_adaptive_thresholds(self, ticker: str) -> Dict:
        """
        Get optimized FSS thresholds based on historical outcomes.
        Returns adaptive buy/sell thresholds that maximize win rate.
        """
        from sqlalchemy import text

        try:
            # Get model state
            state_query = text("""
                SELECT optimal_buy_threshold, optimal_sell_threshold,
                       optimal_close_threshold, recent_win_rate, training_samples
                FROM smartflow_model_state
                WHERE ticker = :ticker
            """)
            result = self.db.execute(state_query, {"ticker": ticker}).fetchone()

            if result and result[4] >= self.MIN_SAMPLES_FOR_LEARNING:
                return {
                    "buy_threshold": result[0],
                    "sell_threshold": result[1],
                    "close_threshold": result[2],
                    "win_rate": result[3],
                    "samples": result[4],
                    "is_learned": True
                }

            # Return defaults if not enough data
            return {
                "buy_threshold": 4.0,
                "sell_threshold": -4.0,
                "close_threshold": 1.0,
                "win_rate": 0.5,
                "samples": 0,
                "is_learned": False
            }

        except Exception as e:
            logger.error(f"Error getting adaptive thresholds: {e}")
            return {
                "buy_threshold": 4.0,
                "sell_threshold": -4.0,
                "close_threshold": 1.0,
                "is_learned": False,
                "error": str(e)
            }

    async def optimize_thresholds(self, ticker: str) -> Dict:
        """
        Run optimization to find best FSS thresholds.
        Uses historical outcomes to find thresholds that maximize expectancy.
        """
        from sqlalchemy import text

        try:
            # Get all outcomes with scores
            outcomes_query = text("""
                SELECT sl.score, sl.action, so.is_winner, so.pnl
                FROM smartflow_signal_outcomes so
                JOIN smartflow_signal_logs sl ON so.signal_log_id = sl.id
                WHERE sl.ticker = :ticker AND so.is_winner IS NOT NULL
                ORDER BY so.created_at DESC
                LIMIT 500
            """)
            results = self.db.execute(outcomes_query, {"ticker": ticker}).fetchall()

            if len(results) < self.MIN_SAMPLES_FOR_LEARNING:
                return {"status": "insufficient_data", "samples": len(results)}

            # Find optimal thresholds by testing different values
            best_buy = 4.0
            best_sell = -4.0
            best_expectancy = 0

            for buy_thresh in [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]:
                for sell_thresh in [-2.0, -2.5, -3.0, -3.5, -4.0, -4.5, -5.0, -5.5, -6.0]:
                    wins = 0
                    losses = 0
                    total_pnl = 0

                    for score, action, is_winner, pnl in results:
                        # Simulate: would this signal have been taken?
                        if action == 'buy' and score >= buy_thresh:
                            if is_winner:
                                wins += 1
                            else:
                                losses += 1
                            total_pnl += pnl or 0
                        elif action == 'sell' and score <= sell_thresh:
                            if is_winner:
                                wins += 1
                            else:
                                losses += 1
                            total_pnl += pnl or 0

                    total = wins + losses
                    if total >= 10:
                        win_rate = wins / total
                        avg_pnl = total_pnl / total
                        expectancy = win_rate * avg_pnl

                        if expectancy > best_expectancy:
                            best_expectancy = expectancy
                            best_buy = buy_thresh
                            best_sell = sell_thresh

            # Update model state
            update_query = text("""
                INSERT INTO smartflow_model_state (ticker, optimal_buy_threshold, optimal_sell_threshold,
                    training_samples, last_trained_at, model_version)
                VALUES (:ticker, :buy, :sell, :samples, NOW(), 1)
                ON CONFLICT (ticker) DO UPDATE SET
                    optimal_buy_threshold = :buy,
                    optimal_sell_threshold = :sell,
                    training_samples = :samples,
                    last_trained_at = NOW(),
                    model_version = smartflow_model_state.model_version + 1
            """)
            self.db.execute(update_query, {
                "ticker": ticker,
                "buy": best_buy,
                "sell": best_sell,
                "samples": len(results)
            })
            self.db.commit()

            return {
                "status": "optimized",
                "optimal_buy_threshold": best_buy,
                "optimal_sell_threshold": best_sell,
                "best_expectancy": best_expectancy,
                "samples_used": len(results)
            }

        except Exception as e:
            logger.error(f"Error optimizing thresholds: {e}")
            return {"error": str(e)}

    # ========================================
    # MARKET REGIME DETECTION
    # ========================================

    async def _detect_market_regime(self, ticker: str) -> Dict:
        """
        Detect current market regime (trending, ranging, volatile).
        Uses VIX levels and recent price action.
        """
        from sqlalchemy import text

        try:
            # Get recent regime history
            regime_query = text("""
                SELECT regime, regime_confidence, regime_strength
                FROM smartflow_market_regimes
                WHERE ticker = :ticker
                ORDER BY timestamp DESC
                LIMIT 1
            """)
            result = self.db.execute(regime_query, {"ticker": ticker}).fetchone()

            if result:
                return {
                    "regime": result[0],
                    "confidence": result[1],
                    "strength": result[2]
                }

            # Default to neutral if no history
            return {
                "regime": "unknown",
                "confidence": 0.5,
                "strength": 0.5
            }

        except Exception as e:
            logger.error(f"Error detecting market regime: {e}")
            return {"regime": "unknown", "confidence": 0.5}

    async def update_market_regime(
        self,
        ticker: str,
        regime: str,
        confidence: float,
        strength: float,
        vix_level: Optional[float] = None
    ) -> Dict:
        """
        Update the detected market regime.
        Called periodically with market data analysis.
        """
        from sqlalchemy import text

        try:
            # Determine recommended action based on regime
            if regime == "volatile":
                recommended_action = "reduce_size"
                size_multiplier = 0.5
            elif regime == "ranging":
                recommended_action = "trade_cautious"
                size_multiplier = 0.75
            elif regime in ["trending_up", "trending_down"]:
                recommended_action = "trade_normal"
                size_multiplier = 1.0 if strength < 0.7 else 1.25
            else:
                recommended_action = "trade_normal"
                size_multiplier = 1.0

            insert_query = text("""
                INSERT INTO smartflow_market_regimes
                (ticker, regime, regime_confidence, regime_strength, vix_level,
                 recommended_action, size_multiplier)
                VALUES (:ticker, :regime, :confidence, :strength, :vix,
                        :action, :size_mult)
            """)
            self.db.execute(insert_query, {
                "ticker": ticker,
                "regime": regime,
                "confidence": confidence,
                "strength": strength,
                "vix": vix_level,
                "action": recommended_action,
                "size_mult": size_multiplier
            })
            self.db.commit()

            return {
                "regime": regime,
                "confidence": confidence,
                "recommended_action": recommended_action,
                "size_multiplier": size_multiplier
            }

        except Exception as e:
            logger.error(f"Error updating market regime: {e}")
            self.db.rollback()
            return {"error": str(e)}

    # ========================================
    # TIME OPTIMIZATION
    # ========================================

    async def get_time_optimization(self, ticker: str) -> Dict:
        """
        Get optimized trading times based on historical performance.
        Returns best hours and days for trading.
        """
        from sqlalchemy import text

        try:
            state_query = text("""
                SELECT hourly_win_rates, best_trading_hours, avoid_hours,
                       daily_win_rates, best_trading_days
                FROM smartflow_model_state
                WHERE ticker = :ticker
            """)
            result = self.db.execute(state_query, {"ticker": ticker}).fetchone()

            if result and result[0]:
                return {
                    "hourly_win_rates": result[0],
                    "best_hours": result[1] or [],
                    "avoid_hours": result[2] or [],
                    "daily_win_rates": result[3],
                    "best_days": result[4] or [],
                    "has_data": True
                }

            return {"has_data": False}

        except Exception as e:
            logger.error(f"Error getting time optimization: {e}")
            return {"has_data": False, "error": str(e)}

    async def calculate_time_optimization(self, ticker: str) -> Dict:
        """
        Calculate optimal trading times from historical data.
        """
        from sqlalchemy import text

        try:
            # Get outcomes by hour
            hourly_query = text("""
                SELECT so.hour_of_day,
                       COUNT(*) as total,
                       SUM(CASE WHEN so.is_winner THEN 1 ELSE 0 END) as wins
                FROM smartflow_signal_outcomes so
                JOIN smartflow_signal_logs sl ON so.signal_log_id = sl.id
                WHERE sl.ticker = :ticker AND so.is_winner IS NOT NULL
                GROUP BY so.hour_of_day
                ORDER BY so.hour_of_day
            """)
            hourly_results = self.db.execute(hourly_query, {"ticker": ticker}).fetchall()

            hourly_win_rates = {}
            best_hours = []
            avoid_hours = []

            for hour, total, wins in hourly_results:
                if hour is not None and total >= 5:
                    win_rate = wins / total
                    hourly_win_rates[str(hour)] = round(win_rate, 3)
                    if win_rate >= 0.6:
                        best_hours.append(hour)
                    elif win_rate < 0.4:
                        avoid_hours.append(hour)

            # Get outcomes by day
            daily_query = text("""
                SELECT so.day_of_week,
                       COUNT(*) as total,
                       SUM(CASE WHEN so.is_winner THEN 1 ELSE 0 END) as wins
                FROM smartflow_signal_outcomes so
                JOIN smartflow_signal_logs sl ON so.signal_log_id = sl.id
                WHERE sl.ticker = :ticker AND so.is_winner IS NOT NULL
                GROUP BY so.day_of_week
                ORDER BY so.day_of_week
            """)
            daily_results = self.db.execute(daily_query, {"ticker": ticker}).fetchall()

            daily_win_rates = {}
            best_days = []

            for day, total, wins in daily_results:
                if day is not None and total >= 5:
                    win_rate = wins / total
                    daily_win_rates[str(day)] = round(win_rate, 3)
                    if win_rate >= 0.55:
                        best_days.append(day)

            # Update model state
            if hourly_win_rates:
                update_query = text("""
                    INSERT INTO smartflow_model_state (ticker, hourly_win_rates, best_trading_hours,
                        avoid_hours, daily_win_rates, best_trading_days)
                    VALUES (:ticker, :hourly::json, :best_hours::json, :avoid::json,
                            :daily::json, :best_days::json)
                    ON CONFLICT (ticker) DO UPDATE SET
                        hourly_win_rates = :hourly::json,
                        best_trading_hours = :best_hours::json,
                        avoid_hours = :avoid::json,
                        daily_win_rates = :daily::json,
                        best_trading_days = :best_days::json,
                        updated_at = NOW()
                """)
                self.db.execute(update_query, {
                    "ticker": ticker,
                    "hourly": json.dumps(hourly_win_rates),
                    "best_hours": json.dumps(best_hours),
                    "avoid": json.dumps(avoid_hours),
                    "daily": json.dumps(daily_win_rates),
                    "best_days": json.dumps(best_days)
                })
                self.db.commit()

            return {
                "hourly_win_rates": hourly_win_rates,
                "best_hours": best_hours,
                "avoid_hours": avoid_hours,
                "daily_win_rates": daily_win_rates,
                "best_days": best_days
            }

        except Exception as e:
            logger.error(f"Error calculating time optimization: {e}")
            return {"error": str(e)}

    # ========================================
    # CONFIDENCE CALIBRATION
    # ========================================

    async def calculate_signal_confidence(
        self,
        ticker: str,
        fss_score: float,
        action: str,
        current_hour: int,
        current_day: int
    ) -> Dict:
        """
        Calculate ML-enhanced confidence score for a signal.
        Combines base confidence with learned optimizations.
        """
        confidence = self.BASE_CONFIDENCE
        factors = []

        try:
            # Get model state
            from sqlalchemy import text
            state_query = text("""
                SELECT hourly_win_rates, best_trading_hours, avoid_hours,
                       fss_accuracy_by_range, recent_win_rate, training_samples
                FROM smartflow_model_state
                WHERE ticker = :ticker
            """)
            state = self.db.execute(state_query, {"ticker": ticker}).fetchone()

            if state and state[5] >= self.MIN_SAMPLES_FOR_LEARNING:
                # Time optimization boost
                hourly_rates = state[0] or {}
                best_hours = state[1] or []
                avoid_hours = state[2] or []

                if current_hour in best_hours:
                    confidence += self.TIME_OPTIMIZATION_BOOST
                    factors.append(f"best_hour_{current_hour}")
                elif current_hour in avoid_hours:
                    confidence -= self.TIME_OPTIMIZATION_BOOST
                    factors.append(f"avoid_hour_{current_hour}")

                # FSS accuracy calibration
                fss_accuracy = state[3] or {}
                abs_score = abs(fss_score)
                if abs_score >= 6:
                    accuracy = fss_accuracy.get("6+", 0.65)
                elif abs_score >= 4:
                    accuracy = fss_accuracy.get("4-6", 0.55)
                elif abs_score >= 2:
                    accuracy = fss_accuracy.get("2-4", 0.50)
                else:
                    accuracy = fss_accuracy.get("0-2", 0.45)

                # Adjust confidence based on historical accuracy
                confidence += (accuracy - 0.5) * 30  # +/- 15 based on accuracy
                factors.append(f"fss_accuracy_{accuracy:.2f}")

                # Recent performance factor
                recent_win_rate = state[4] or 0.5
                if recent_win_rate > 0.6:
                    confidence += 5
                    factors.append("hot_streak")
                elif recent_win_rate < 0.4:
                    confidence -= 5
                    factors.append("cold_streak")

            # Get current regime
            regime = await self._detect_market_regime(ticker)
            if regime.get("regime") == "trending_up" and action == "buy":
                confidence += self.REGIME_ALIGNMENT_BOOST
                factors.append("regime_aligned")
            elif regime.get("regime") == "trending_down" and action == "sell":
                confidence += self.REGIME_ALIGNMENT_BOOST
                factors.append("regime_aligned")
            elif regime.get("regime") == "volatile":
                confidence -= 10
                factors.append("volatile_market")

            # Clamp confidence to 0-100
            confidence = max(0, min(100, confidence))

            return {
                "confidence": round(confidence, 1),
                "factors": factors,
                "is_ml_enhanced": bool(state and state[5] >= self.MIN_SAMPLES_FOR_LEARNING),
                "samples_learned": state[5] if state else 0
            }

        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return {
                "confidence": self.BASE_CONFIDENCE,
                "factors": ["error"],
                "is_ml_enhanced": False
            }

    # ========================================
    # CROSS-TICKER CORRELATION
    # ========================================

    async def detect_correlation_signal(
        self,
        ticker_scores: Dict[str, float],
        min_tickers: int = 2,
        threshold: float = 3.0
    ) -> Optional[Dict]:
        """
        Detect when multiple tickers align in the same direction.
        Higher conviction signals when SPY, QQQ, IWM all agree.
        """
        from sqlalchemy import text

        bullish_tickers = []
        bearish_tickers = []
        alignment_scores = {}

        for ticker, score in ticker_scores.items():
            if score >= threshold:
                bullish_tickers.append(ticker)
                alignment_scores[ticker] = score
            elif score <= -threshold:
                bearish_tickers.append(ticker)
                alignment_scores[ticker] = score

        # Check for bullish alignment
        if len(bullish_tickers) >= min_tickers:
            composite_fss = statistics.mean([ticker_scores[t] for t in bullish_tickers])
            conviction = self._calculate_conviction(len(bullish_tickers), composite_fss)

            # Record correlation signal
            insert_query = text("""
                INSERT INTO smartflow_correlation_signals
                (signal_type, direction, confidence, tickers_aligned, alignment_scores,
                 total_tickers, composite_fss, conviction_level)
                VALUES ('bullish_alignment', 'buy', :confidence, :tickers::json, :scores::json,
                        :total, :composite, :conviction)
                RETURNING id
            """)
            result = self.db.execute(insert_query, {
                "confidence": conviction["confidence"],
                "tickers": json.dumps(bullish_tickers),
                "scores": json.dumps(alignment_scores),
                "total": len(bullish_tickers),
                "composite": composite_fss,
                "conviction": conviction["level"]
            })
            signal_id = result.fetchone()[0]
            self.db.commit()

            return {
                "id": signal_id,
                "type": "bullish_alignment",
                "direction": "buy",
                "tickers": bullish_tickers,
                "composite_fss": composite_fss,
                "confidence": conviction["confidence"],
                "conviction_level": conviction["level"]
            }

        # Check for bearish alignment
        if len(bearish_tickers) >= min_tickers:
            composite_fss = statistics.mean([ticker_scores[t] for t in bearish_tickers])
            conviction = self._calculate_conviction(len(bearish_tickers), abs(composite_fss))

            insert_query = text("""
                INSERT INTO smartflow_correlation_signals
                (signal_type, direction, confidence, tickers_aligned, alignment_scores,
                 total_tickers, composite_fss, conviction_level)
                VALUES ('bearish_alignment', 'sell', :confidence, :tickers::json, :scores::json,
                        :total, :composite, :conviction)
                RETURNING id
            """)
            result = self.db.execute(insert_query, {
                "confidence": conviction["confidence"],
                "tickers": json.dumps(bearish_tickers),
                "scores": json.dumps(alignment_scores),
                "total": len(bearish_tickers),
                "composite": composite_fss,
                "conviction": conviction["level"]
            })
            signal_id = result.fetchone()[0]
            self.db.commit()

            return {
                "id": signal_id,
                "type": "bearish_alignment",
                "direction": "sell",
                "tickers": bearish_tickers,
                "composite_fss": composite_fss,
                "confidence": conviction["confidence"],
                "conviction_level": conviction["level"]
            }

        return None

    def _calculate_conviction(self, num_tickers: int, avg_score: float) -> Dict:
        """Calculate conviction level based on alignment strength."""
        base_confidence = 50 + (num_tickers - 2) * 10  # +10 per extra ticker
        score_bonus = min(25, avg_score * 5)  # Up to +25 for high scores
        confidence = min(100, base_confidence + score_bonus)

        if confidence >= 85:
            level = "extreme"
        elif confidence >= 70:
            level = "high"
        elif confidence >= 55:
            level = "medium"
        else:
            level = "low"

        return {"confidence": confidence, "level": level}

    # ========================================
    # PATTERN RECOGNITION
    # ========================================

    async def find_matching_pattern(self, flow_features: Dict) -> Optional[Dict]:
        """
        Find if current flow matches any known winning pattern.
        """
        from sqlalchemy import text

        try:
            # Get active patterns with good performance
            patterns_query = text("""
                SELECT id, name, pattern_features, win_rate, expectancy, confidence_score
                FROM smartflow_patterns
                WHERE is_active = true AND total_occurrences >= :min_samples
                ORDER BY expectancy DESC
                LIMIT 20
            """)
            patterns = self.db.execute(patterns_query, {
                "min_samples": self.MIN_SAMPLES_FOR_LEARNING
            }).fetchall()

            best_match = None
            best_similarity = 0

            for pattern_id, name, features_json, win_rate, expectancy, confidence in patterns:
                pattern_features = features_json if isinstance(features_json, dict) else json.loads(features_json)
                similarity = self._calculate_pattern_similarity(flow_features, pattern_features)

                if similarity > 0.7 and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        "pattern_id": pattern_id,
                        "pattern_name": name,
                        "similarity": similarity,
                        "historical_win_rate": win_rate,
                        "expectancy": expectancy,
                        "confidence_boost": confidence - 50
                    }

            return best_match

        except Exception as e:
            logger.error(f"Error finding pattern match: {e}")
            return None

    def _calculate_pattern_similarity(self, current: Dict, pattern: Dict) -> float:
        """Calculate similarity between current flow and a known pattern."""
        if not current or not pattern:
            return 0.0

        score = 0.0
        comparisons = 0

        # Compare action direction
        if current.get("action") == pattern.get("action"):
            score += 0.3
        comparisons += 1

        # Compare flow direction (bullish vs bearish ratio)
        current_ratio = current.get("bullish_flows", 0) / max(1, current.get("bearish_flows", 1))
        pattern_ratio = pattern.get("bullish_flows", 0) / max(1, pattern.get("bearish_flows", 1))
        ratio_diff = abs(current_ratio - pattern_ratio) / max(current_ratio, pattern_ratio, 1)
        score += (1 - ratio_diff) * 0.3
        comparisons += 1

        # Compare score magnitude
        if current.get("score") and pattern.get("score"):
            score_diff = abs(current["score"] - pattern["score"]) / max(abs(current["score"]), abs(pattern["score"]), 1)
            score += (1 - score_diff) * 0.2
            comparisons += 1

        # Compare time of day
        if current.get("hour") == pattern.get("hour"):
            score += 0.1
        comparisons += 1

        # Compare day of week
        if current.get("day") == pattern.get("day"):
            score += 0.1
        comparisons += 1

        return score

    # ========================================
    # MODEL UPDATES & METRICS
    # ========================================

    async def _update_model_from_outcome(
        self,
        ticker: str,
        is_winner: bool,
        pnl: float,
        hour: int,
        day: int,
        regime: Dict
    ):
        """Update model state with new outcome."""
        from sqlalchemy import text

        try:
            # Get current state
            state_query = text("""
                SELECT recent_win_rate, recent_signals_count, fss_accuracy_by_range
                FROM smartflow_model_state
                WHERE ticker = :ticker
            """)
            state = self.db.execute(state_query, {"ticker": ticker}).fetchone()

            if state:
                # Update rolling win rate
                old_rate = state[0] or 0.5
                old_count = state[1] or 0
                new_count = min(old_count + 1, self.ROLLING_WINDOW_SIZE)

                # Exponential moving average for win rate
                alpha = 2 / (new_count + 1)
                new_rate = old_rate * (1 - alpha) + (1 if is_winner else 0) * alpha

                update_query = text("""
                    UPDATE smartflow_model_state
                    SET recent_win_rate = :rate,
                        recent_signals_count = :count,
                        updated_at = NOW()
                    WHERE ticker = :ticker
                """)
                self.db.execute(update_query, {
                    "ticker": ticker,
                    "rate": new_rate,
                    "count": new_count
                })
            else:
                # Create new state
                insert_query = text("""
                    INSERT INTO smartflow_model_state
                    (ticker, recent_win_rate, recent_signals_count)
                    VALUES (:ticker, :rate, 1)
                """)
                self.db.execute(insert_query, {
                    "ticker": ticker,
                    "rate": 1.0 if is_winner else 0.0
                })

            self.db.commit()

        except Exception as e:
            logger.error(f"Error updating model: {e}")
            self.db.rollback()

    async def _update_daily_metrics(self, ticker: str, is_winner: bool, pnl: float):
        """Update daily ML metrics."""
        from sqlalchemy import text

        try:
            today = date.today()

            upsert_query = text("""
                INSERT INTO smartflow_ml_metrics
                (ticker, metric_date, signals_executed, winners, losers, net_pnl)
                VALUES (:ticker, :date, 1, :wins, :losses, :pnl)
                ON CONFLICT (ticker, metric_date) DO UPDATE SET
                    signals_executed = smartflow_ml_metrics.signals_executed + 1,
                    winners = smartflow_ml_metrics.winners + :wins,
                    losers = smartflow_ml_metrics.losers + :losses,
                    net_pnl = smartflow_ml_metrics.net_pnl + :pnl,
                    win_rate = CASE
                        WHEN (smartflow_ml_metrics.winners + :wins + smartflow_ml_metrics.losers + :losses) > 0
                        THEN (smartflow_ml_metrics.winners + :wins)::float /
                             (smartflow_ml_metrics.winners + :wins + smartflow_ml_metrics.losers + :losses)
                        ELSE 0.5
                    END
            """)
            self.db.execute(upsert_query, {
                "ticker": ticker,
                "date": today,
                "wins": 1 if is_winner else 0,
                "losses": 0 if is_winner else 1,
                "pnl": pnl or 0
            })
            self.db.commit()

        except Exception as e:
            logger.error(f"Error updating daily metrics: {e}")
            self.db.rollback()

    # ========================================
    # ML DASHBOARD DATA
    # ========================================

    async def get_ml_dashboard(self, ticker: str = "SPY") -> Dict:
        """
        Get comprehensive ML performance dashboard data.
        """
        from sqlalchemy import text

        try:
            # Get model state
            state_query = text("""
                SELECT ticker, optimal_buy_threshold, optimal_sell_threshold,
                       recent_win_rate, recent_signals_count, training_samples,
                       model_version, last_trained_at,
                       hourly_win_rates, best_trading_hours, avoid_hours
                FROM smartflow_model_state
                WHERE ticker = :ticker
            """)
            state = self.db.execute(state_query, {"ticker": ticker}).fetchone()

            # Get recent daily metrics
            metrics_query = text("""
                SELECT metric_date, win_rate, net_pnl, signals_executed,
                       improvement_vs_baseline
                FROM smartflow_ml_metrics
                WHERE ticker = :ticker
                ORDER BY metric_date DESC
                LIMIT 30
            """)
            metrics = self.db.execute(metrics_query, {"ticker": ticker}).fetchall()

            # Get pattern performance
            patterns_query = text("""
                SELECT name, win_rate, expectancy, total_occurrences
                FROM smartflow_patterns
                WHERE is_active = true
                ORDER BY expectancy DESC
                LIMIT 10
            """)
            patterns = self.db.execute(patterns_query).fetchall()

            # Get recent correlation signals
            corr_query = text("""
                SELECT signal_type, direction, confidence, conviction_level,
                       tickers_aligned, was_profitable, timestamp
                FROM smartflow_correlation_signals
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            correlations = self.db.execute(corr_query).fetchall()

            return {
                "model_state": {
                    "ticker": state[0] if state else ticker,
                    "optimal_buy_threshold": state[1] if state else 4.0,
                    "optimal_sell_threshold": state[2] if state else -4.0,
                    "recent_win_rate": state[3] if state else 0.5,
                    "signals_learned": state[4] if state else 0,
                    "training_samples": state[5] if state else 0,
                    "model_version": state[6] if state else 1,
                    "last_trained": state[7].isoformat() if state and state[7] else None,
                    "best_hours": state[9] if state else [],
                    "avoid_hours": state[10] if state else []
                } if state else None,
                "daily_metrics": [
                    {
                        "date": m[0].isoformat(),
                        "win_rate": m[1],
                        "pnl": m[2],
                        "signals": m[3],
                        "improvement": m[4]
                    } for m in metrics
                ],
                "top_patterns": [
                    {
                        "name": p[0],
                        "win_rate": p[1],
                        "expectancy": p[2],
                        "occurrences": p[3]
                    } for p in patterns
                ],
                "recent_correlations": [
                    {
                        "type": c[0],
                        "direction": c[1],
                        "confidence": c[2],
                        "conviction": c[3],
                        "tickers": c[4],
                        "profitable": c[5],
                        "time": c[6].isoformat() if c[6] else None
                    } for c in correlations
                ],
                "is_learning": bool(state and state[5] >= self.MIN_SAMPLES_FOR_LEARNING)
            }

        except Exception as e:
            logger.error(f"Error getting ML dashboard: {e}")
            return {"error": str(e)}

    async def run_full_optimization(self, tickers: List[str] = None) -> Dict:
        """
        Run full optimization for all tracked tickers.
        Should be called periodically (e.g., daily).
        """
        if not tickers:
            tickers = ["SPY", "QQQ", "IWM", "DIA", "GLD"]

        results = {}
        for ticker in tickers:
            results[ticker] = {
                "thresholds": await self.optimize_thresholds(ticker),
                "time_optimization": await self.calculate_time_optimization(ticker)
            }

        return {
            "optimized_tickers": len(results),
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
