SmartFlow Growth/Disruption Analysis (growth-analyst)
====================================================

Scope
-----
- Review strategies: unified, deterministic, quick, flow, ai_proxy, pyramid, breakout, mean_reversion.
- Analyze recent signal quality from PostgreSQL: trading_db.smartflow_signal_logs and smartflow_score_history.
- Identify causes of NEUTRAL/low-confidence signals.
- Recommend parameter tuning for better signal quality.
- Verify Polygon rate limiting fix.
- Provide SWOT analysis.

Data Notes (DB queries run against unified_engine_postgres)
---------------------------------------------------------
- 30d smartflow_signal_logs: buy=2,178 (avg conf 78.0), sell=1,047 (avg conf 63.7).
- 7d smartflow_signal_logs: buy=411 (avg conf 80.1), sell=116 (avg conf 66.0).
- Engine mix (30d): unified=2,698, flow=254, ai_only:unified_v1=133, flow:unified_v1=119, ai_only=21.
- Confidence buckets (30d): <60=116, 60-69=169, 70-79=151, 80-89=313, 90+=41.
- Outcomes (30d): 2,438 logged outcomes, win_rate ~12.3% (avg pnl_pct ~0.000; likely missing pnl data).
- Score history (30d): 23,540 samples; 12,698 (54.0%) in [-1, +1]; median score 0.00.
- By ticker (30d score history): GLD, DIA, VIX, UVXY are mostly/entirely near zero.

Strategy Review (8)
-------------------
1) unified
   - Router default; live unified engine is not implemented in SmartFlowService.
   - In runtime, unified attribution is likely coming from router metadata, not a true unified engine path.
2) deterministic
   - Multi-timeframe indicator engine (EMA/RSI/MACD/ATR) with 4/5 TF alignment and 75% confidence gate.
   - Enabled, but requires indicators stack; no recent deterministic signals in logs suggests it may be unavailable or suppressed.
3) quick
   - 5m momentum scalping (EMA cross + RSI momentum + optional 15m confirm + volume gate).
   - Enabled, but no recent quick signals in logs; likely availability or routing/filters.
4) flow
   - Flow sentiment score over 5m window; thresholds +/-4, min premium 30k, flow confirmation MEDIUM+.
   - Generates most live signals (base SmartFlow path).
5) ai_proxy
   - Backtest-only proxy using MTF deterministic signals with a lower (70%) confidence gate and non-neutral bias requirement.
   - Not true Claude replay; AI proxy is honest about proxy limitations.
6) pyramid
   - Regime-adaptive pyramid strategy (2%/2% base, pullback-based adds, max 3 positions).
   - Implemented for backtests/forward test; not wired into live SmartFlow cycle.
7) breakout
   - Compression + structural breakouts, strong filters (volume 1.5x, RSI confirm, regime alignment, R:R >= 2).
   - Wired into strategy engine cycle, but only run if router selects breakout (and currently not default).
8) mean_reversion
   - Ranging-market mean reversion with strict RSI extremes, ADX < 25, volume exhaustion, R:R >= 2.
   - Wired into strategy engine cycle; excluded for crypto.

Why Signals Skew NEUTRAL / Low Confidence
-----------------------------------------
- Flow scarcity for some instruments: GLD/DIA/VIX/UVXY show near-zero scores in score history (54% of all samples are -1..+1).
- Short score window (5m) + min premium (30k) + +/-4 threshold yields many "no-signal" intervals unless bursts occur.
- Flow confirmation requires MEDIUM+ agreement (>=55%); mixed flows often block signals.
- AI-only mode requires non-neutral AI consensus and MTF alignment; neutral MTF bias drops signals.
- Deterministic/quick engines appear inactive in logs, reducing diversity of signal sources and leaving flow to dominate.

Parameter Tuning Recommendations
--------------------------------
- Flow signals:
  - Increase score window to 10-15 minutes for lower-flow tickers (GLD/DIA) or remove them from flow universe.
  - Lower score thresholds slightly (e.g., +/-3) only for higher-liquidity tickers (SPY/QQQ/IWM) if you want more signals.
  - Raise min premium back to 50k for noisy instruments, while lowering it for high-liquidity tickers via per-ticker config.
  - Lower min_flow_conviction to LOW for non-core tickers; keep MEDIUM+ for SPY/QQQ to preserve quality.
- Confidence filters:
  - If low-confidence signals remain, raise min_confidence_score from 30 to 50 to filter noisy flow signals.
  - Enable price/RSI/volume filters only if market_data_service is reliable; otherwise they can suppress signals.
- Strategy breadth:
  - Verify deterministic/quick availability (pandas-ta) and confirm they are writing to DB; they should supply more diversified signals.
  - Consider enabling breakout/mean_reversion only when router selects those regimes; keep them off in slim map.
- Universe hygiene:
  - Trim flow-driven universe to tickers with proven options flow activity; route low-flow tickers to AI-only or deterministic engines.

Polygon Rate Limiting Fix
-------------------------
- market_data_service enforces POLYGON_CALLS_PER_MINUTE (4) via _reserve_polygon_call and _polygon_get_with_backoff.
- get_multi_timeframe_bars switches to minimal mode when remaining <=2 calls.
- SmartFlowService skips Polygon-only instruments when remaining <2 in deterministic/quick/strategy cycles.
- AI-only cycle does not call _should_skip_polygon_only directly, but MTF analysis uses the same rate-limit-aware bars.
- Conclusion: fix is present and should prevent 429 storms, but AI-only could still hit the limit if the loop is aggressive.

SWOT
----
Strengths
- Multi-engine design with regime-aware routing and honest engine labeling.
- Flow + MTF + AI augmentation offers breadth of signal sources.
- Explicit rate-limit defenses reduce data-provider risk.
- Strong backtest lore (unified/quick) and structured outcome logging.

Weaknesses
- Unified engine path not implemented in live cycle; attribution can be misleading.
- Deterministic/quick signals absent in recent logs, concentrating risk in flow signals.
- Many instruments show sparse flow leading to neutral/low-confidence outputs.
- Outcome PnL metrics look incomplete (avg pnl_pct near 0).

Opportunities
- Rebalance universe to flow-rich tickers and route low-flow assets to AI/MTF engines.
- Tune thresholds per ticker/asset class; add regime-specific flow thresholds.
- Improve signal outcome capture to close the feedback loop for adaptive learning.
- Add live pyramid entries for trending regimes to increase return per signal.

Threats
- Provider throttling (Polygon, flow feeds) and data gaps can suppress signals.
- Over-filtering (flow conviction + AI disagreement + trend filters) can reduce trade frequency.
- Regime drift risks (strict filters may underperform in new volatility regimes).

