# Phase 5A: True AI Backtest Routing - Discovery Report

**Date:** March 14, 2026
**Status:** Discovery Complete - Implementation Path Identified

---

## Executive Summary

**Current State:** AI engine **currently falls back to unified** in backtesting (explicitly marked as "not yet implemented").

**Feasibility:** **Partial AI backtest routing is feasible now** with honest limitations.

**Recommendation:** Implement AI backtest using **deterministic signal logic** with AI confidence thresholds, avoiding live Claude API calls during backtesting.

---

## 1. Current AI Live Engine Paths

### A. AI-Only Mode (`run_ai_only_cycle`)

**Location:** `app/services/smartflow_service.py:1758-1920`

**How it works in live trading:**
1. Scans configured instruments every 15 minutes
2. Calls **live Claude API** for analysis:
   - `ai_strategy_suite.analyze_technical(ticker)`
   - `ai_strategy_suite.analyze_patterns(ticker)`
   - `ai_strategy_suite.analyze_macro(ticker)`
3. Computes composite recommendation (buy/sell votes)
4. Generates signals if:
   - Average confidence ≥ `ai_only_confidence_threshold` (70%)
   - MTF bias aligns with AI direction
   - Not duplicate of recent signal

**Key characteristics:**
- **External dependency:** Claude API (Anthropic)
- **Live-only data:** Real-time market data from Polygon
- **Non-deterministic:** Claude responses vary per call
- **Expensive:** API costs ~$0.25-$1.25 per analysis
- **Rate limited:** 15-minute scan interval to control costs

### B. AI Enhancement (`get_ai_enhancement`)

**Location:** `app/services/smartflow_service.py:1009-1095`

**How it works:**
- Called as enhancement to Flow/Deterministic signals
- Runs same Claude analyses
- Provides confidence boost based on agreement
- Used when `enable_ai_enhancement = True`

**Same limitations:** Claude API dependency, non-deterministic, expensive.

---

## 2. Current AI Backtest Handling

**Location:** `app/services/backtesting/comparison_runner.py:211-244`

```python
else:
    # Unified, flow, ai - use default unified strategy
    metrics = await backtester.run_backtest(ticker=ticker, days=days)
```

**Execution Metadata for AI:**
```python
'ai': {
    'mode': 'unified_fallback',
    'fallback': True,
    'status': 'unified_fallback',
    'notes': 'AI engine backtest not yet implemented - using unified fallback'
}
```

**Current behavior:**
- AI requests **fall back to unified** backtest
- Metadata **honestly labels** this as fallback
- Router **correctly excludes AI** from auto-routing
- No fake AI behavior

---

## 3. AI Analysis Dependencies

### A. External Dependencies

| Dependency | Purpose | Backtest Impact |
|-----------|---------|-----------------|
| **Claude API (Anthropic)** | AI analysis generation | ❌ Not replayable, expensive, non-deterministic |
| **Polygon API** | Live market data | ✅ Can use historical bars (already available) |
| **market_data_service** | Multi-timeframe analysis | ✅ Can replay with historical data |

### B. Key AI Decision Components

**From `run_ai_only_cycle` analysis:**

1. **AI Analysis Results:**
   - `recommendation`: strong_buy, buy, neutral, sell, strong_sell
   - `confidence`: 0-100%
   - `summary`: Text description

2. **Voting Logic:**
   - Count buy votes vs sell votes
   - Calculate average confidence
   - Require threshold: `ai_only_confidence_threshold` (70%)

3. **MTF Alignment:**
   - Multi-timeframe bias: bullish, bearish, neutral
   - Require AI direction to align with MTF bias
   - Confluences boost signal quality

4. **Signal Generation:**
   - Action: buy or sell (determined by vote majority)
   - Score: Average confidence
   - Source: 'SmartFlow-AI'
   - Reason: Includes analysis votes + MTF alignment

---

## 4. Deterministic vs Non-Deterministic Components

### ✅ DETERMINISTIC (Replayable):

1. **Multi-Timeframe Analysis:**
   - Available from `market_data_service.get_multi_timeframe_analysis()`
   - Uses historical bars from Polygon
   - Produces: bias, bullish_alignment, bearish_alignment, confluences
   - **100% replayable** with historical data

2. **Voting Logic:**
   - Count buy/sell votes
   - Calculate average confidence
   - Threshold comparison
   - MTF alignment check
   - **100% deterministic** given AI results

3. **Signal Generation:**
   - Standard SmartFlowSignal creation
   - **100% deterministic** given inputs

### ❌ NON-DETERMINISTIC (Not Replayable):

1. **Claude API Calls:**
   - `analyze_technical()`, `analyze_patterns()`, `analyze_macro()`
   - Different response each time
   - Expensive ($$$)
   - Not suitable for backtesting

2. **Cache Dependency:**
   - AI results cached with TTL (1-24 hours depending on analysis type)
   - Historical cache entries don't exist for past bars
   - Can't replay past decisions

---

## 5. Feasible AI Backtest Approaches

### Option A: Mock AI with Deterministic Indicators ✅ **RECOMMENDED**

**Approach:**
- Use **multi-timeframe analysis** (already deterministic) as AI proxy
- Apply AI-style **confidence thresholds** and **voting logic**
- Preserve **AI behavioral characteristics** without Claude API

**Benefits:**
- ✅ Fully replayable with historical data
- ✅ No API costs
- ✅ Fast backtest execution
- ✅ Honest about what it represents
- ✅ Captures AI decision framework (thresholds, alignment, voting)

**Limitations:**
- ⚠️ Not true Claude AI analysis
- ⚠️ Simpler than real AI (no DCF, macro, competitive analysis)
- ⚠️ Should be labeled clearly as "AI-style" or "AI-proxy"

**Implementation:**
```python
async def run_ai_backtest(self, ticker: str, days: int):
    """
    AI-Proxy Backtest using deterministic MTF analysis
    with AI-style confidence thresholds and voting logic.

    NOTE: Uses multi-timeframe technical analysis as AI proxy.
    Not true Claude API analysis (too expensive/non-deterministic for backtesting).
    """
    # Use MTF analysis for each bar
    # Apply AI confidence threshold (70%)
    # Require MTF alignment
    # Generate signals with engine_type='ai'
```

**Metadata:**
```python
'ai': {
    'mode': 'ai_proxy_backtest',
    'fallback': False,  # Now has dedicated path
    'status': 'partially_routed',
    'notes': 'AI-proxy using MTF analysis + AI thresholds (not true Claude analysis)'
}
```

---

### Option B: True AI Backtest (Not Feasible Now) ❌

**Would require:**
- Pre-generating AI analysis for all historical bars
- Storing massive AI response cache
- $$$$ API costs for historical analysis
- Still non-deterministic (different responses)

**Why not feasible:**
- 90-day backtest with 15-min bars = ~8,640 bars
- 3 analyses per bar (technical, patterns, macro) = 25,920 API calls
- Cost: ~$0.50/call * 25,920 = **$12,960 per backtest** ❌
- Still wouldn't be deterministic

**Verdict:** Not practical for backtesting.

---

### Option C: Cached AI Responses (Not Feasible) ❌

**Would require:**
- Building historical cache of AI responses
- Maintaining cache indefinitely
- Assumes responses don't change (but they do)

**Why not feasible:**
- Cache doesn't exist for historical dates
- Can't replay past
- Claude responses change over time (model updates, knowledge cutoff)

**Verdict:** Not practical.

---

## 6. Recommended Implementation Path

### Phase 5A Implementation: AI-Proxy Backtest

**What to build:**

1. **New backtest method:** `run_ai_proxy_backtest(ticker, days)`
2. **Signal logic:**
   - Use MTF analysis for each bar (deterministic)
   - Apply AI confidence threshold (≥70%)
   - Require MTF bias alignment (same as live AI)
   - Generate buy/sell based on MTF bias
   - Mark trades as `engine_type='ai'`

3. **Honest labeling:**
   - `actual_execution_mode = 'ai_proxy_backtest'`
   - `routing_status = 'partially_routed'`
   - `notes = 'AI-proxy using MTF analysis + AI thresholds (not true Claude analysis)'`

4. **Router integration:**
   - Add AI to `AUTO_ELIGIBLE_ENGINES` (with partial status)
   - Or keep manual-only and require explicit opt-in
   - Comparison metadata shows honest proxy status

**What NOT to do:**
- ❌ Don't call Claude API during backtest
- ❌ Don't fake AI analysis responses
- ❌ Don't claim it's true AI if it's proxy logic
- ❌ Don't misrepresent proxy as equivalent to live AI

---

## 7. AI Behavioral Characteristics to Preserve

From live AI implementation (`run_ai_only_cycle`):

1. **Confidence Threshold:**
   - `ai_only_confidence_threshold = 70%`
   - Only trade when confidence ≥ 70%

2. **MTF Alignment Requirement:**
   - AI direction must align with MTF bias
   - Bullish AI + Bearish MTF = skip
   - Neutral MTF = allow

3. **Voting Logic:**
   - Multiple analysis votes (technical, patterns, macro)
   - Buy votes > sell votes = buy signal
   - Sell votes > buy votes = sell signal
   - Tie = skip

4. **Scan Interval:**
   - 15-minute intervals (cost control)
   - Don't spam signals

5. **Duplicate Prevention:**
   - Check last signal for same ticker
   - Skip if same direction within 30 minutes

**AI-Proxy should preserve these characteristics.**

---

## 8. Files to Modify/Create

### Create:
- `app/services/smartflow_backtest.py::run_ai_proxy_backtest()` - New backtest method

### Modify:
- `app/services/backtesting/comparison_runner.py::_run_engine_backtest()` - Route AI to proxy
- `app/services/backtesting/comparison_runner.py::_get_execution_metadata()` - Update AI metadata
- `app/services/smartflow_engine_router.py` - Decide if AI becomes auto-eligible

---

## 9. Success Criteria

**Minimum Success (Acceptable):**
- ✅ AI backtest path exists (proxy implementation)
- ✅ Metadata honestly labels execution mode
- ✅ AI produces **different results** from unified/deterministic/quick
- ✅ Router metadata shows partial routing status
- ✅ No regressions in existing engines

**Stronger Success (Ideal):**
- ✅ AI-proxy results show material divergence from other engines
- ✅ Comparison data accumulates for AI
- ✅ Statistical confidence evaluation applies to AI (once enough samples)
- ✅ AI can become auto-eligible later if performance warrants

---

## 10. Decision Point: Auto-Eligible or Manual-Only?

### Option 1: Keep AI Manual-Only for Now

**Rationale:**
- AI-proxy is not true AI
- Transparent about limitations
- Requires user explicit selection
- Can accumulate comparison data
- Move to auto-eligible later if verified

**Router code:**
```python
AUTO_ELIGIBLE_ENGINES = ['unified', 'deterministic', 'quick']  # AI excluded
MANUAL_ONLY_ENGINES = ['flow', 'ai']  # AI manual until verified
```

### Option 2: Make AI Auto-Eligible (Partial)

**Rationale:**
- AI-proxy is deterministic and testable
- Metadata clearly shows it's proxy
- Comparison data will accumulate
- Router can prefer it in regimes where it excels

**Router code:**
```python
AUTO_ELIGIBLE_ENGINES = ['unified', 'deterministic', 'quick', 'ai']
```

**Recommendation:** Start with **Manual-Only**, move to auto-eligible after verification.

---

## 11. Comparison with Other Engines

**Expected AI-Proxy Behavior:**

| Engine | Signal Logic | Entry Criteria |
|--------|--------------|----------------|
| **Unified** | Regime-based, flow confluence | Regime + flow score |
| **Deterministic** | MTF indicators (≥4/5 TFs, 75% conf, 2:1 R:R) | Strict multi-timeframe alignment |
| **Quick** | 5m momentum (60% conf, 1.5:1 R:R, 2hr hold) | Fast 5m timeframe only |
| **AI-Proxy** | MTF bias + 70% confidence + alignment | Similar to deterministic but higher confidence threshold |

**Expected Divergence:**
- AI-proxy should produce **fewer but higher-confidence trades** than deterministic
- AI-proxy **requires MTF alignment** (deterministic doesn't)
- AI-proxy uses **70% threshold** vs deterministic's 75%
- AI-proxy may skip trades that deterministic takes (due to alignment requirement)

---

## 12. Example Trade Comparison

**Scenario:** MES trending up, 4/5 timeframes bullish, 80% confidence

| Engine | Decision | Reason |
|--------|----------|--------|
| **Deterministic** | ✅ BUY | 4/5 TFs ≥ 75% conf, 2:1 R:R met |
| **Quick** | ✅ BUY | 5m bullish, 60% conf met |
| **AI-Proxy** | ✅ BUY | MTF bias bullish, 80% > 70% threshold, aligned |

**Scenario:** MES ranging, 2/5 timeframes bullish, 60% confidence

| Engine | Decision | Reason |
|--------|----------|--------|
| **Deterministic** | ❌ SKIP | Only 2/5 TFs, <75% conf |
| **Quick** | ✅ BUY | 5m might still trigger (if 60% conf met) |
| **AI-Proxy** | ❌ SKIP | 60% < 70% threshold, MTF neutral/weak |

**Expected:** AI-proxy should have **higher win rate** but **fewer trades** than quick/unified.

---

## 13. Next Steps (Implementation Plan)

**If approved, proceed with:**

1. ✅ Implement `run_ai_proxy_backtest()` in `smartflow_backtest.py`
2. ✅ Route AI to proxy in `comparison_runner.py`
3. ✅ Update execution metadata with honest labeling
4. ✅ Run comparison: unified vs deterministic vs quick vs ai
5. ✅ Verify AI produces divergent results
6. ✅ Test router integration (manual-only first)
7. ✅ Build UI to display AI partial routing status
8. ✅ Create Phase 5A completion report

---

## 14. Honest Disclosure

**What AI-Proxy IS:**
- ✅ Deterministic backtest using MTF analysis
- ✅ Applies AI-style confidence thresholds (70%)
- ✅ Requires MTF alignment (like live AI)
- ✅ Preserves AI behavioral characteristics
- ✅ Fully replayable with historical data
- ✅ Generates real comparison data

**What AI-Proxy IS NOT:**
- ❌ True Claude API analysis
- ❌ Equivalent to live AI mode
- ❌ Using 10 institutional analysis frameworks
- ❌ Calling Anthropic during backtest

**Metadata will clearly state:** "AI-proxy using MTF analysis + AI thresholds (not true Claude analysis)"

---

## 15. Conclusion

**Feasibility:** ✅ **YES** - Partial AI backtest routing is feasible now

**Recommendation:** Implement **AI-proxy backtest** using deterministic MTF analysis with AI confidence thresholds

**Status After Phase 5A:**
- AI becomes **partially routed** (proxy implementation)
- Metadata **honestly labels** execution mode
- Comparison data **accumulates** for AI
- Router can **evaluate** AI performance vs other engines
- AI can become **auto-eligible later** if verified

**Blocker Removed:** AI no longer falls back to unified (has dedicated proxy path)

**Path to Phase 5B:** Once AI is partially routed, proceed with Flow feasibility assessment

---

**Phase 5A Discovery Status:** ✅ **COMPLETE**
**Ready for Implementation:** ✅ **YES**
**Implementation Approach:** AI-Proxy Backtest with Honest Labeling

---

*Report generated on March 14, 2026*
