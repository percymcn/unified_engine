# Phase 8A Discovery Report: Router Integration Analysis

**Date**: 2026-03-14
**Phase**: 8A - Router Integration
**Purpose**: Identify integration points for strategy registry eligibility filter

---

## Executive Summary

The SmartFlow adaptive router is **fully implemented** with sophisticated regime-aware engine selection, but is **NOT YET integrated** into signal generation. The router exists in `app/services/smartflow_engine_router.py` with complete API endpoints, but signal generation in `app/services/smartflow_service.py` currently hardcodes engine selection without calling the router.

**Phase 8A Goal**: Connect signal generation → router → strategy registry eligibility filter → selected strategy_id

---

## 1. Current Router Implementation

### Location
**File**: `/home/pharma5/unified_engine/app/services/smartflow_engine_router.py` (640 lines)

### Key Class: `SmartFlowEngineRouter`

```python
class SmartFlowEngineRouter:
    """
    Adaptive router for SmartFlow engine selection.

    Decision Hierarchy:
    1. Manual Override (if set)
    2. Manual Mode Default ('unified')
    3. Auto Mode:
       a. Data-driven (comparison store)
       b. Rule-based (fallback rules)
       c. Default ('unified')
    """
```

### Main Entry Point
```python
def route_signal_request(
    self,
    regime: str,
    regime_confidence: float = 1.0
) -> RouterDecision:
    """
    Route signal request based on regime.

    Returns RouterDecision with:
    - selected_engine: str
    - decision_source: DecisionSource
    - statistical_confidence: float
    - fallback_used: bool
    """
```

**Line**: 300-372

---

## 2. Engine Eligibility System

### Two-Tier System (lines 53-59)

```python
AUTO_ELIGIBLE_ENGINES = ['unified', 'deterministic', 'quick']
MANUAL_ONLY_ENGINES = ['ai', 'flow']
ALL_ENGINES = AUTO_ELIGIBLE_ENGINES + MANUAL_ONLY_ENGINES
```

**Why Two Tiers?**
- Auto-eligible: Fully routed, no fallback dependencies
- Manual-only: Fallback-backed, require explicit user override

**Phase 8A Requirement**: Replace this with dynamic strategy registry filter

---

## 3. Router Decision Hierarchy

### Priority Order (lines 300-372)

1. **Manual Override** (line 317)
   - If `manual_override_engine` set → use it
   - Source: `DecisionSource.MANUAL_OVERRIDE`

2. **Manual Mode** (line 333)
   - If `routing_mode == MANUAL` → use 'unified'
   - Source: `DecisionSource.DEFAULT`

3. **Auto Mode - Data-Driven** (line 348)
   - Query comparison store rankings
   - If sample_count >= 20 → `DecisionSource.COMPARISON_RESULTS`
   - If 0 < sample_count < 20 → `DecisionSource.LOW_CONFIDENCE_DATA`

4. **Auto Mode - Fallback Rules** (line 258)
   - Use hardcoded regime-to-engine mappings
   - Source: `DecisionSource.FALLBACK_RULE`

5. **Ultimate Fallback** (line 295)
   - Default to 'unified'
   - Source: `DecisionSource.DEFAULT`

---

## 4. Regime-Based Fallback Rules

### 8 Market Regimes (lines 148-212)

| Regime | Preferred Engine | Ranking | Confidence | Notes |
|--------|------------------|---------|------------|-------|
| `ranging` | deterministic | [det, uni, quick] | 0.6 | Strict MTF alignment in sideways |
| `mean_reverting` | deterministic | [det, uni, quick] | 0.6 | Deterministic for reversion setups |
| `trending_up` | quick | [quick, uni, det] | 0.7 | Fast momentum entries |
| `trending_down` | quick | [quick, uni, det] | 0.7 | Fast momentum entries |
| `vol_expansion` | quick | [quick, uni, det] | 0.65 | Capture breakout momentum |
| `vol_contraction` | deterministic | [det, uni, quick] | 0.65 | Prepare for breakout |
| `chaotic` | unified | [uni, det, quick] | 0.5 | Balanced default in uncertainty |
| `neutral` | unified | [uni, det, quick] | 0.5 | Default balanced |

**Phase 8A Note**: These rules currently select engine **types** (deterministic, quick, etc.), but Phase 8A must extend this to select specific **strategy_ids** (e.g., deterministic_v1, deterministic_v1.7).

---

## 5. Data-Driven Rankings (Comparison Store)

### Source
**File**: `/home/pharma5/unified_engine/app/services/backtesting/comparison_store.py`

### Method: `get_regime_ranking(regime: str)`

**Returns**:
```python
{
    'ranked_engines': ['unified', 'deterministic', 'quick'],  # Best to worst
    'engine_stats': {
        'unified': {
            'samples': 25,
            'avg_pnl': 520.5,
            'avg_win_rate': 0.62,
            'pnl_history': [...],
            'win_rate_history': [...]
        },
        # ... other engines
    },
    'sample_count': 25,  # Total comparisons for this regime
    'last_updated': '2026-03-14T12:00:00Z',
    'comparison_ids': ['comp_001', 'comp_002', ...]
}
```

### Statistical Confidence (Phase 4.5, lines 544-584)

```python
MINIMUM_REGIME_SAMPLES = 20  # For high confidence
CONFIDENCE_DENOMINATOR = 50  # For 100% confidence

# Confidence formula
confidence = min(1.0, sample_count / CONFIDENCE_DENOMINATOR)

# If sample_count >= 20: DecisionSource.COMPARISON_RESULTS (high confidence)
# If 0 < sample_count < 20: DecisionSource.LOW_CONFIDENCE_DATA (low confidence)
# If sample_count == 0: DecisionSource.FALLBACK_RULE (no data)
```

---

## 6. RouterDecision Object

### Class Definition (lines 83-117)

```python
@dataclass
class RouterDecision:
    # Core decision
    routing_mode: RoutingMode  # MANUAL or AUTO_BY_REGIME
    current_regime: str  # Market regime detected
    selected_engine: str  # Engine to use

    # Rankings
    eligible_engines: List[str]  # Which engines can be chosen
    ranking: List[str]  # Ordered preference for this regime

    # Traceability
    decision_source: DecisionSource  # How decision was made
    decision_reason: str  # Human-readable explanation
    fallback_used: bool  # True if rule-based, False if data-driven

    # Statistical confidence (Phase 4.5)
    sample_size: int  # Number of comparisons used
    statistical_confidence: float  # 0-1 based on sample size

    # Metadata
    timestamp: datetime
    manual_override: Optional[str]  # If user forced choice
    regime_confidence: float  # Confidence in regime detection
```

### Example Response

```json
{
  "routing_mode": "auto_by_regime",
  "current_regime": "trending_up",
  "selected_engine": "quick",
  "eligible_engines": ["unified", "deterministic", "quick"],
  "ranking": ["quick", "unified", "deterministic"],
  "decision_source": "fallback_rule",
  "decision_reason": "Trending up: Quick preferred for fast momentum entries",
  "fallback_used": true,
  "sample_size": 0,
  "statistical_confidence": 0.0,
  "regime_confidence": 0.75,
  "timestamp": "2026-03-14T12:00:00Z",
  "manual_override": null
}
```

**Phase 8A Addition**: Add `selected_strategy_id`, `strategy_status`, `parent_strategy` fields.

---

## 7. Strategy Registry Eligibility Filter (Phase 7)

### Location
**File**: `/home/pharma5/unified_engine/app/services/strategy_registry/registry.py`

### Method: `get_router_eligible_strategies()` (line 679)

```python
def get_router_eligible_strategies(self) -> List[SmartFlowStrategy]:
    """
    Get strategies eligible for router selection.

    Only these statuses are eligible:
    - built_in
    - approved_for_router
    - active

    Blocked statuses:
    - candidate (not evaluated)
    - approved_for_forward_test (backtest only)
    - forward_testing (in test)
    - rejected (failed criteria)
    - retired (removed from service)
    - archived (historical)
    """
    eligible_statuses = [
        StrategyStatus.BUILT_IN.value,
        StrategyStatus.APPROVED_FOR_ROUTER.value,
        StrategyStatus.ACTIVE.value,
    ]
    return self.db.query(SmartFlowStrategy).filter(
        SmartFlowStrategy.status.in_(eligible_statuses)
    ).all()
```

### Strategy Object Fields

```python
class SmartFlowStrategy:
    strategy_id: str  # e.g., "deterministic_v1", "deterministic_v1.7"
    strategy_type: str  # "deterministic", "quick", "unified", "flow", "ai"
    status: str  # "built_in", "approved_for_router", "active"
    parent_strategy_id: Optional[str]  # For variants

    # Performance metrics
    sharpe_ratio: Optional[float]
    win_rate: Optional[float]
    max_drawdown: Optional[float]

    # Audit trail
    approved_for_router_at: Optional[datetime]
    approved_for_router_by: Optional[str]
    active_at: Optional[datetime]
```

---

## 8. CRITICAL GAP: No Signal Generation Integration

### Current State: Signal Generation

**File**: `/home/pharma5/unified_engine/app/services/smartflow_service.py`

**Lines 251-268**: Hardcoded engine enablement
```python
# Current implementation (NO ROUTER CALL)
self.enable_deterministic_mode = True
self.enable_quick_mode = True
self.enable_flow_mode = False
self.enable_ai_mode = False
# ... generates signals without router decision
```

**Problem**: Signal generation never calls the router, so all the adaptive routing logic is unused in production.

### What's Missing

1. **No regime detection** in signal generation flow
2. **No router call** to select engine
3. **No strategy registry filter** integration
4. **No routing decision** in signal metadata
5. **Auto mode disabled** (stuck in MANUAL mode)

---

## 9. Regime Detection Services

### Primary Service
**File**: `/home/pharma5/unified_engine/app/services/regime_detector.py`

```python
class RegimeDetector:
    def detect_regime(self, df: pd.DataFrame, ticker: str) -> RegimeAnalysis:
        """
        Detect market regime from OHLCV data.

        Returns:
            RegimeAnalysis(
                regime: str,  # 'trending_up', 'ranging', etc.
                confidence: float,  # 0-1
                regime_config: dict,  # Regime-specific parameters
                metadata: dict  # Additional info
            )
        """
```

**Line**: 310

### V2 Service (Advanced)
**File**: `/home/pharma5/unified_engine/app/services/regime_detector_v2.py`

- 6-class regime states with probability vectors
- More sophisticated detection logic

---

## 10. API Endpoints (Current Integration)

### Router Control Endpoints
**File**: `/home/pharma5/unified_engine/app/routers/smartflow.py`

| Endpoint | Method | Purpose | Line |
|----------|--------|---------|------|
| `/router/status` | GET | Get router status | 3070 |
| `/router/mode` | POST | Set routing mode (MANUAL/AUTO) | 3094 |
| `/router/override` | POST | Set/clear manual override | 3141 |
| `/router/mapping` | GET | Get regime-to-engine mapping | 3181 |
| `/router/decision` | GET | Get routing decision for regime (test) | 3212 |
| `/router/refresh` | POST | Refresh rankings from comparison store | 3245 |

**Note**: All endpoints require `require_smartflow_tier` permission.

### Strategy Registry Endpoints
**File**: `/home/pharma5/unified_engine/app/routers/strategy_registry.py`

| Endpoint | Method | Purpose | Line |
|----------|--------|---------|------|
| `/api/strategies/router-eligible` | GET | Get router-eligible strategies | 600 |
| `/api/strategies` | GET | List all strategies | 63 |
| `/api/strategies/{strategy_id}` | GET | Get strategy details | 100 |

---

## 11. Phase 8A Integration Points

### **INTEGRATION POINT 1: Signal Generation Call**

**File**: `/home/pharma5/unified_engine/app/services/smartflow_service.py`

**Where**: Before signal generation (around line 250)

**What to Add**:
```python
# 1. Detect regime
regime_detector = RegimeDetector()
regime_analysis = regime_detector.detect_regime(df, ticker)

# 2. Get router decision
from app.services.smartflow_engine_router import get_router
router = get_router()
decision = router.route_signal_request(
    regime=regime_analysis.regime,
    regime_confidence=regime_analysis.confidence
)

# 3. Use selected engine
selected_engine_type = decision.selected_engine  # 'deterministic', 'quick', etc.
```

**Current Code**:
```python
# Line 251-268
self.enable_deterministic_mode = True
self.enable_quick_mode = True
# ... hardcoded
```

**New Code**:
```python
# Enable only selected engine
self.enable_deterministic_mode = (selected_engine_type == 'deterministic')
self.enable_quick_mode = (selected_engine_type == 'quick')
self.enable_unified_mode = (selected_engine_type == 'unified')
# ... etc
```

---

### **INTEGRATION POINT 2: Router Eligibility Filter**

**File**: `/home/pharma5/unified_engine/app/services/smartflow_engine_router.py`

**Where**: Inside `select_best_engine_for_regime()` method (around line 273)

**What to Add**:
```python
# 1. Get router-eligible strategies
from app.services.strategy_registry import get_strategy_registry
registry = get_strategy_registry()
eligible_strategies = registry.get_router_eligible_strategies()

# 2. Filter ranking by eligible strategies
eligible_ids = {s.strategy_id for s in eligible_strategies}
eligible_types = {s.strategy_type for s in eligible_strategies}

# 3. Filter ranking.ranked_engines to only include eligible types
filtered_ranking = [
    engine for engine in ranking.ranked_engines
    if engine in eligible_types
]

# 4. Select best eligible strategy_id (not just type)
# If multiple variants of same type, select by performance
best_strategy = max(
    [s for s in eligible_strategies if s.strategy_type == filtered_ranking[0]],
    key=lambda s: s.sharpe_ratio or 0
)
selected_strategy_id = best_strategy.strategy_id
```

**Current Code** (line 292):
```python
selected = ranking.ranked_engines[0]  # Just engine type
```

**New Code**:
```python
selected_strategy_id = best_strategy.strategy_id  # Specific strategy
selected_engine_type = best_strategy.strategy_type
```

---

### **INTEGRATION POINT 3: RouterDecision Extension**

**File**: `/home/pharma5/unified_engine/app/services/smartflow_engine_router.py`

**Where**: `RouterDecision` dataclass (lines 83-117)

**What to Add**:
```python
@dataclass
class RouterDecision:
    # ... existing fields ...

    # Phase 8A: Strategy Registry Integration
    selected_strategy_id: str  # "deterministic_v1.7"
    strategy_status: str  # "approved_for_router"
    parent_strategy: Optional[str]  # "deterministic_v1" or None for built-ins
    is_variant: bool  # True if parent_strategy is not None
```

---

### **INTEGRATION POINT 4: Signal Metadata**

**File**: `/home/pharma5/unified_engine/app/services/smartflow_service.py`

**Where**: Signal response object (wherever signals are returned)

**What to Add**:
```python
signal_response = {
    # ... existing signal fields ...

    # Phase 8A: Routing metadata
    "routing_decision": {
        "selected_strategy_id": decision.selected_strategy_id,
        "selected_engine_type": decision.selected_engine,
        "strategy_status": decision.strategy_status,
        "parent_strategy": decision.parent_strategy,
        "decision_source": decision.decision_source,
        "current_regime": decision.current_regime,
        "statistical_confidence": decision.statistical_confidence,
        "fallback_used": decision.fallback_used,
        "timestamp": decision.timestamp.isoformat()
    }
}
```

---

## 12. Fallback Preservation Requirements

### Current Fallback Chain (MUST PRESERVE)

1. **Manual Override** → Use override engine
2. **Manual Mode** → Use 'unified'
3. **Auto Mode - Data-Driven** → Use comparison store rankings
4. **Auto Mode - Fallback Rules** → Use regime-based rules
5. **Ultimate Default** → Use 'unified'

### Phase 8A Additions (PRESERVE CHAIN)

At each step, filter by strategy registry eligibility:

```python
# If manual override
if manual_override_engine:
    # Check if eligible variant exists for this engine type
    eligible_variants = [s for s in eligible_strategies if s.strategy_type == manual_override_engine]
    if eligible_variants:
        selected = max(eligible_variants, key=lambda s: s.sharpe_ratio or 0)
    else:
        # Fallback: use built-in of that type if available
        built_ins = [s for s in eligible_strategies if s.strategy_type == manual_override_engine and s.parent_strategy_id is None]
        selected = built_ins[0] if built_ins else fallback_to_unified_built_in
```

**Critical**: Never break existing fallback logic - only enhance it with strategy_id selection.

---

## 13. Summary of Changes Required

### Files to Modify

1. **`app/services/smartflow_engine_router.py`**
   - Extend `RouterDecision` dataclass (add strategy_id, status, parent)
   - Modify `select_best_engine_for_regime()` to filter by registry eligibility
   - Modify `route_signal_request()` to return selected strategy_id
   - Add `_select_best_strategy_for_type()` helper method

2. **`app/services/smartflow_service.py`**
   - Add regime detection before signal generation
   - Call router to get decision
   - Use decision.selected_engine to enable only selected engine
   - Include routing_decision in signal metadata

3. **`app/routers/smartflow.py`**
   - Update router API responses to include strategy_id fields
   - Add endpoint for testing strategy-level routing

### No New Files Required
Phase 8A is pure integration - no new architecture.

---

## 14. Testing Plan

### Test 1: Built-In Strategy Selection
1. Ensure all 5 built-in strategies are router-eligible
2. Route signal in trending_up regime
3. Verify 'quick' type selected
4. Verify `selected_strategy_id = "quick_v1"` (built-in)

### Test 2: Variant Selection (Better Performance)
1. Create variant `deterministic_v1.7` with sharpe_ratio = 2.5
2. Approve for router (status = approved_for_router)
3. Route signal in ranging regime
4. Verify 'deterministic' type selected
5. Verify `selected_strategy_id = "deterministic_v1.7"` (variant, not built-in)
6. Verify `parent_strategy = "deterministic_v1"`

### Test 3: Blocked Strategy (Candidate Status)
1. Create variant `quick_v1.5` with sharpe_ratio = 3.0
2. Keep as candidate (status = candidate)
3. Route signal in trending_up regime
4. Verify `selected_strategy_id = "quick_v1"` (built-in fallback)
5. Verify candidate variant NOT selected

### Test 4: Manual Override with Variant
1. Set manual override to 'deterministic'
2. Ensure `deterministic_v1.7` is approved_for_router
3. Route signal
4. Verify `selected_strategy_id = "deterministic_v1.7"`
5. Verify `decision_source = "manual_override"`

### Test 5: Fallback Preservation
1. Disable all strategies except unified_v1
2. Route signal in trending_up regime (prefers quick)
3. Verify fallback to `unified_v1`
4. Verify `fallback_used = true`

---

## 15. Router Status API Update

### Current Response
```json
{
  "routing_mode": "manual",
  "manual_override_engine": null,
  "auto_eligible_engines": ["unified", "deterministic", "quick"],
  "manual_only_engines": ["ai", "flow"]
}
```

### Phase 8A Enhanced Response
```json
{
  "routing_mode": "auto_by_regime",
  "manual_override_engine": null,
  "router_eligible_strategies": [
    {
      "strategy_id": "unified_v1",
      "strategy_type": "unified",
      "status": "built_in",
      "is_variant": false,
      "parent_strategy": null,
      "sharpe_ratio": 1.35,
      "win_rate": 55.2
    },
    {
      "strategy_id": "deterministic_v1.7",
      "strategy_type": "deterministic",
      "status": "approved_for_router",
      "is_variant": true,
      "parent_strategy": "deterministic_v1",
      "sharpe_ratio": 2.15,
      "win_rate": 62.5
    }
  ],
  "total_eligible": 6,
  "total_variants": 1,
  "total_built_ins": 5
}
```

---

## 16. Regime Mapping API Update

### Current Response
```json
{
  "trending_up": {
    "preferred_engine": "quick",
    "ranking": ["quick", "unified", "deterministic"],
    "source": "fallback_rule"
  }
}
```

### Phase 8A Enhanced Response
```json
{
  "trending_up": {
    "preferred_engine": "quick",
    "preferred_strategy": {
      "strategy_id": "quick_v1",
      "status": "built_in",
      "sharpe_ratio": 1.65
    },
    "ranking": [
      {
        "strategy_id": "quick_v1",
        "strategy_type": "quick",
        "status": "built_in"
      },
      {
        "strategy_id": "unified_v1.3",
        "strategy_type": "unified",
        "status": "approved_for_router"
      }
    ],
    "source": "fallback_rule"
  }
}
```

---

## 17. Comparison Store Enhancement (Future)

**Out of Scope for Phase 8A** (Phase 9+ work):

Currently, comparison store tracks engine **types** (deterministic, quick, unified).

**Future Enhancement**: Track specific **strategy_ids** in comparisons:
```json
{
  "ranked_strategies": [
    {"strategy_id": "deterministic_v1.7", "avg_pnl": 625.5},
    {"strategy_id": "deterministic_v1", "avg_pnl": 480.2},
    {"strategy_id": "quick_v1", "avg_pnl": 450.0}
  ]
}
```

This would require:
- Backtest comparison runner to evaluate specific strategy_ids
- Comparison store schema upgrade
- Router to select from strategy_id rankings (not type rankings)

**For Phase 8A**: Use type-level rankings, then select best strategy_id within that type.

---

## 18. Decision: Best Insertion Points

### PRIMARY INSERTION POINT: `SmartFlowEngineRouter.select_best_engine_for_regime()`

**File**: `app/services/smartflow_engine_router.py`
**Method**: `select_best_engine_for_regime()` (line 273)

**Why This Point?**
- Central decision logic for all routing modes
- Already has engine type selection logic
- Natural place to add strategy_id selection
- Preserves all fallback logic
- Minimal code changes

**Changes**:
1. Add strategy registry eligibility query
2. Filter ranked_engines to only eligible types
3. Select best strategy_id within selected type
4. Return both `selected_engine` (type) and `selected_strategy_id`

---

### SECONDARY INSERTION POINT: Signal Generation

**File**: `app/services/smartflow_service.py`
**Method**: Signal generation (around line 250)

**Why This Point?**
- Where signals are actually generated
- Add regime detection here
- Call router for decision
- Use decision to enable correct engine
- Include routing metadata in signal response

**Changes**:
1. Add regime detection call
2. Add router decision call
3. Replace hardcoded engine enablement with decision-based
4. Add routing_decision to signal metadata

---

### TERTIARY INSERTION POINT: API Enhancements

**File**: `app/routers/smartflow.py`
**Method**: Router status/mapping endpoints (lines 3070-3245)

**Why This Point?**
- Expose new strategy-level information to UI
- Minimal changes to existing endpoints
- Add new fields to existing responses

**Changes**:
1. Add `router_eligible_strategies` to `/router/status`
2. Add `preferred_strategy` to `/router/mapping`
3. Add `selected_strategy_id` to `/router/decision` test endpoint

---

## 19. Risk Analysis

### Low Risk Changes
✓ Adding fields to `RouterDecision` dataclass (backward compatible)
✓ Adding strategy registry query in router (new logic, no changes to existing)
✓ Enhancing API responses with new fields (backward compatible)

### Medium Risk Changes
⚠ Modifying `select_best_engine_for_regime()` logic (central routing logic)
⚠ Modifying signal generation to call router (changes production flow)

**Mitigation**:
- Preserve all existing fallback logic
- Add feature flag for Phase 8A routing (can disable if issues)
- Comprehensive testing of all fallback scenarios

### High Risk Changes
❌ None - Phase 8A is pure integration, no architecture changes

---

## 20. Implementation Order

### Step 1: Extend RouterDecision (Low Risk)
- Add `selected_strategy_id`, `strategy_status`, `parent_strategy` fields
- No behavior changes yet

### Step 2: Add Eligibility Filter to Router (Medium Risk)
- Modify `select_best_engine_for_regime()` to query registry
- Filter ranked_engines by eligibility
- Select best strategy_id within type
- Preserve all fallback logic

### Step 3: Signal Generation Integration (Medium Risk)
- Add regime detection
- Call router for decision
- Use decision to enable engine
- Add routing metadata to signal

### Step 4: API Enhancements (Low Risk)
- Update `/router/status` response
- Update `/router/mapping` response
- Update `/router/decision` test endpoint

### Step 5: Testing (Critical)
- Test all 5 test scenarios
- Verify fallback preservation
- Verify eligibility filtering
- Verify variant selection

---

## Conclusion

**Phase 8A is ready for implementation**. All components exist:
- ✅ Adaptive router (fully implemented)
- ✅ Strategy registry eligibility filter (Phase 7)
- ✅ Regime detection services
- ✅ Comparison store rankings
- ✅ API endpoints

**The gap**: These components are **not connected**. Phase 8A will connect them with minimal risk by:
1. Adding strategy_id selection to existing router logic
2. Calling router from signal generation
3. Filtering by registry eligibility
4. Enhancing API responses

**No new architecture required** - pure integration.

---

**End of Phase 8A Discovery Report**
