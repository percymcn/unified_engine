SmartFlow Analysis Report (fundamentals-analyst)

Scope:
- File reviewed: unified_engine/app/services/smartflow_service.py
- Data source: Postgres smartflow_signal_logs + smartflow_score_history (last 30 days)

Database Signal Quality Snapshot (last 30 days)
- smartflow_signal_logs:
  - buy (unified): 1,767 signals, avg confidence 69.48, avg score 550.19
  - sell (unified): 931 signals, avg confidence 62.06, avg score -135.10
  - buy (flow): 171 signals, avg confidence 80.35, avg score 334.29
  - sell (flow): 83 signals, avg confidence 65.00, avg score -54.65
  - ai_only / ai_only:unified_v1: 154 buys total, avg confidence ~80
- smartflow_score_history:
  - total scores: 23,540
  - 55.82% of scores fall within [-4, 4] (no buy/sell signal band)
  - 53.94% of scores fall within [-1, 1] (close/neutral band)

Strategy Review (8 requested)
1) unified
   - Main flow-driven path via compute_sentiment_score + should_generate_signal.
   - Requires score > 4 or < -4 plus flow confirmation, microstructure filter, funding bias,
     trend filter, and min confidence 30. AI enhancement is optional and off by default.
2) deterministic
   - Multi-timeframe indicator engine (EMA/RSI/MACD/ATR).
   - Requires 4/5 TF alignment, higher TF agreement, confidence >= 75, R:R >= 3.0.
   - Uses pct stops (0.2% SL / 0.6% TP) with preset "pct_optimal".
3) quick
   - 5m momentum scalps with EMA9/21 crossover, RSI momentum, volume confirmation,
     optional 15m trend check. Confidence >= 60, R:R 1.5.
4) flow
   - Same flow-based sentiment path as unified, with engine_type tagged as flow when used.
   - Uses flow confirmation (MEDIUM+ conviction) and options flow scoring.
5) ai_proxy
   - Not a first-class engine in this file. Related behavior is split between:
     - AI enhancement in should_generate_signal (disabled by default).
     - AI-only mode for 24/7 markets (run_ai_only_cycle).
     - Webhook routing maps "ai_v1_proxy" based on reason text.
6) pyramid
   - No explicit pyramid logic in smartflow_service.py. Likely defined elsewhere or not implemented.
7) breakout
   - Implemented via run_strategy_engine_cycle('breakout') using strategy_engines.
   - Runs only if router selects it; otherwise default off.
8) mean_reversion
   - Implemented via run_strategy_engine_cycle('mean_reversion') using strategy_engines.
   - Runs only if router selects it; otherwise default off.

Why signals are mostly NEUTRAL (low trade frequency)
- Flow score band is strict: score > 4 or < -4, with a 5-minute window and min premium 30k.
- Score history shows ~56% of samples remain inside [-4, 4], so no signal is generated.
- Flow confirmation requires MEDIUM+ conviction; mixed flow quickly blocks signals.
- Regime-asymmetric logic adds stricter requirements in uptrends (HIGH/EXTREME flow, RR >= 4,
  imbalance >= 0.45), reducing long frequency in trending regimes.
- Additional blocking filters stack: microstructure, funding bias, trend filter, min confidence,
  duplicate cooldown, and signal TTL.
- AI-only mode only runs after hours/weekends, so in-session flow droughts yield no signals.

Parameter Tuning Recommendations (to improve signal quality)
- Reduce strictness of flow gating:
  - Lower score thresholds to +/-3.0 during low-flow sessions, or scale with flow count.
  - Consider min_flow_conviction = LOW for non-whale tickers (or allow MEDIUM with >=55% agreement).
- Widen flow window to 10-15 minutes for thin symbols to accumulate usable signal.
- Reduce min_premium from 30k to 20k for non-index ETFs/FX proxies to increase sample size.
- Loosen regime-asymmetric constraints in trending_up:
  - uptrend_flow_require = MEDIUM, uptrend_imbalance_min = 0.35, uptrend_rr_min = 3.0
  - This avoids starving long signals in strong trends.
- Adjust confidence gate:
  - Keep min_confidence_score at 30, but add a dynamic boost for higher total_premium or
    increasing flow intensity to prevent borderline confidence rejections.
- AI-only scheduling:
  - Allow AI-only to run intra-day for instruments with no flow for > N cycles.

Polygon Rate Limiting Fix Status
- Implemented: _should_skip_polygon_only uses market_data_service.get_polygon_rate_limit_remaining()
  and skips Polygon-only tickers when remaining < 2.
- Coverage: applied in deterministic, quick, strategy_engine cycles, and flow ticker processing.
- Gap: AI-only mode does not call _should_skip_polygon_only, so Polygon budget can still be
  exhausted during AI-only scans (forex/CFD tickers).

SWOT Analysis
- Strengths: Multi-engine architecture, flow + MTF indicators, adaptive routing, trade journal
  integration, detailed signal metadata and confidence scoring.
- Weaknesses: Strict flow gating causes high neutral rate; AI-only limited to off-hours; pyramid
  and unified engine paths are not fully implemented; rate-limit guard missing in AI-only.
- Opportunities: Dynamic thresholds by market regime/flow density; integrate AI-only fallback
  during flow droughts; expand strategy engines with consistent confidence calibration.
- Threats: Polygon budget exhaustion can degrade data quality; flow proxy outages cause silent
  signal drops; overfitting risk with many stacked filters.
