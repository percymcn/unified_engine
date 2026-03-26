# Phase 6: Strategy Registry + Variant Evaluation Pipeline - Discovery Report

**Date:** March 14, 2026
**Status:** Discovery Complete - Implementation Path Identified

---

## Executive Summary

**Goal:** Build a **controlled research system** for managing built-in SmartFlow engine strategies, generating parameterized variants, evaluating performance, and safely promoting/rejecting strategies for production use.

**Important:** This is NOT uncontrolled self-modification - it's a **controlled experimentation framework** with human oversight.

**Current State:** No dedicated strategy registry exists for SmartFlow engines (unified, deterministic, quick, flow, ai). Existing `Strategy` model tracks webhook strategies (TradingView), not built-in engines.

**Feasibility:** **Fully feasible** - can build on existing comparison framework.

---

## 1. Current Code Landscape

### A. Existing Strategy Systems (Not What We Need)

**`app/models/models.py::Strategy`** (Lines 368-381)
```python
class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, unique=True, index=True, nullable=False)
    strategy_name = Column(String, nullable=False)
    strategy_version = Column(String, nullable=False, default="1.0.0")
    strategy_source = Column(String, nullable=False)  # tradingview, inhouse, manual
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    parameters = Column(JSON)  # Strategy-specific parameters
```

**Purpose:** Tracks **webhook-based strategies** (TradingView signals).

**Not Suitable For Phase 6 Because:**
- Designed for external webhook strategies
- Doesn't track SmartFlow engines (unified, deterministic, etc.)
- Doesn't support variants/experiments
- Doesn't track backtest performance
- Doesn't support promotion/rejection workflow

---

### B. Existing Comparison Framework (Can Leverage)

**`app/services/backtesting/comparison_runner.py`** ✅

**What it provides:**
- Multi-engine backtest comparison
- Performance metrics (Sharpe, win rate, P&L, etc.)
- Regime-specific performance breakdown
- Execution metadata tracking

**Can be leveraged for:** Variant evaluation

---

**`app/services/backtesting/comparison_store.py`** ✅

**What it provides:**
- Persistent storage of comparison results
- Regime-based engine rankings
- Statistical aggregation across multiple comparisons
- Query interface for performance data

**Can be leveraged for:** Variant performance tracking

---

### C. Current SmartFlow Engines

| Engine | Status | Backtest Method | Empirical Status |
|--------|--------|-----------------|------------------|
| **Unified** | `fully_routed` | `run_backtest()` | ✅ Verified |
| **Deterministic** | `fully_routed` | `run_deterministic_backtest()` | ✅ Verified |
| **Quick** | `fully_routed` | `run_quick_backtest()` | ✅ Verified |
| **Flow** | `fully_routed` | `run_flow_backtest()` | ⚠️ Pending real Polygon key |
| **AI** | `partially_routed` | `run_ai_proxy_backtest()` | ✅ Verified (as proxy) |

**These are the built-in strategies that should populate the initial registry.**

---

## 2. Phase 6 Requirements

### A. Strategy Registry

**Must Store:**
- Strategy ID (e.g., `unified_v1`, `deterministic_v1.2`)
- Strategy type (e.g., `unified`, `deterministic`, `quick`, `flow`, `ai`)
- Version number (semantic versioning)
- Status (`built_in`, `candidate`, `approved_for_router`, `retired`)
- Parameters (JSON config)
- Performance metrics (from backtests)
- Creation date
- Approval/rejection history
- Notes (why approved/rejected)

**Must Support:**
- Listing all strategies
- Filtering by status
- Querying by engine type
- Version tracking
- Promotion/demotion

---

### B. Variant Generator

**Must Be Able To:**
- Generate parameterized variants of base strategies
- Example: `deterministic_v1.1` with `min_confidence=70%` instead of 75%
- Example: `quick_v1.2` with `max_hold=1.5hr` instead of 2hr
- Track which parameters were changed from base
- Maintain parent-child relationships

**Parameterization Examples:**

**Deterministic Variants:**
- `min_confidence_score`: 70%, 75%, 80%
- `min_aligned_timeframes`: 3, 4, 5
- `min_risk_reward`: 1.5, 2.0, 2.5

**Quick Variants:**
- `max_hold_hours`: 1.0, 1.5, 2.0, 3.0
- `min_confidence_score`: 55%, 60%, 65%
- `min_risk_reward`: 1.2, 1.5, 1.8

**Flow Variants:**
- `score_threshold_buy`: 2.5, 3.0, 3.5
- `min_premium`: $30k, $40k, $50k
- `signal_cooldown_minutes`: 20, 30, 40

---

### C. Variant Evaluator

**Must Be Able To:**
- Run backtest comparison for a variant
- Use existing `comparison_runner` infrastructure
- Store results in comparison store
- Tag results with variant ID
- Generate performance report

---

### D. Promotion/Rejection Logic

**Promotion Criteria (Example):**
- ✅ Min 30 days backtest (statistical significance)
- ✅ Sharpe ratio > 1.0
- ✅ Win rate > 50%
- ✅ Max drawdown < 10%
- ✅ Outperforms base strategy
- ✅ Human approval required

**Rejection Criteria:**
- ❌ Sharpe ratio < 0.5
- ❌ Win rate < 40%
- ❌ Max drawdown > 15%
- ❌ Underperforms base strategy
- ❌ Statistical anomalies detected

**Status Transitions:**
```
candidate → (evaluation) → approved_for_router
candidate → (evaluation) → rejected
approved_for_router → (performance degradation) → retired
built_in → (never retired automatically)
```

---

### E. Router Integration

**Auto-Routing Eligibility:**
```python
# Only these statuses can be auto-routed
AUTO_ELIGIBLE_STATUSES = ['built_in', 'approved_for_router']

# All others require manual selection
MANUAL_ONLY_STATUSES = ['candidate', 'rejected', 'retired']
```

**Engine Router Must:**
- Query registry for auto-eligible strategies
- Filter by status
- Exclude candidates/rejected variants
- Log which variant was selected

---

## 3. Proposed Architecture

### A. Database Schema

```python
# New table: smartflow_strategies
class SmartFlowStrategy(Base):
    __tablename__ = "smartflow_strategies"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, unique=True, index=True)  # e.g., "deterministic_v1.2"
    strategy_type = Column(String, index=True)  # unified, deterministic, quick, flow, ai
    version = Column(String)  # e.g., "1.2.0"
    status = Column(String, index=True)  # built_in, candidate, approved_for_router, retired

    # Configuration
    parameters = Column(JSON)  # Strategy-specific parameters
    parent_strategy_id = Column(String, nullable=True)  # For variants
    parameter_changes = Column(JSON, nullable=True)  # What changed from parent

    # Performance (from backtests)
    sharpe_ratio = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)
    backtest_days = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    evaluated_at = Column(DateTime(timezone=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(String, nullable=True)

    # Audit trail
    approval_notes = Column(Text, nullable=True)
    rejection_notes = Column(Text, nullable=True)

    # Comparison tracking
    latest_comparison_id = Column(String, nullable=True)
```

```python
# New table: strategy_evaluations
class StrategyEvaluation(Base):
    __tablename__ = "strategy_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(String, ForeignKey("smartflow_strategies.strategy_id"))
    comparison_id = Column(String)  # Links to comparison_store

    # Evaluation results
    passed = Column(Boolean)
    sharpe_ratio = Column(Float)
    win_rate = Column(Float)
    max_drawdown = Column(Float)
    total_trades = Column(Integer)

    # Evaluation criteria
    criteria_checked = Column(JSON)  # Which criteria were evaluated
    criteria_results = Column(JSON)  # Which passed/failed

    # Metadata
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
```

---

### B. Service Architecture

```
app/services/strategy_registry/
├── __init__.py
├── registry.py           # StrategyRegistry service
├── variant_generator.py  # VariantGenerator service
├── evaluator.py         # StrategyEvaluator service
├── promoter.py          # PromotionEngine service
└── schemas.py           # Pydantic schemas
```

**Key Services:**

1. **StrategyRegistry**
   - CRUD for strategies
   - Version management
   - Status transitions
   - Query interface

2. **VariantGenerator**
   - Generate variants from base strategies
   - Parameter mutation
   - Parent-child tracking

3. **StrategyEvaluator**
   - Run backtests for variants
   - Store results
   - Generate evaluation reports

4. **PromotionEngine**
   - Apply promotion criteria
   - Recommend approval/rejection
   - Require human confirmation
   - Audit trail

---

### C. API Endpoints

```python
# app/routers/strategy_registry.py
POST   /api/v1/strategies/registry/built-in/initialize  # Seed registry with built-ins
GET    /api/v1/strategies/registry                      # List all strategies
GET    /api/v1/strategies/registry/{strategy_id}        # Get strategy details
POST   /api/v1/strategies/registry/variants/generate    # Generate variant
POST   /api/v1/strategies/registry/variants/evaluate    # Evaluate variant
POST   /api/v1/strategies/registry/variants/promote     # Promote to approved
POST   /api/v1/strategies/registry/variants/reject      # Reject variant
GET    /api/v1/strategies/registry/candidates           # List candidates
GET    /api/v1/strategies/registry/approved             # List approved
```

---

## 4. Built-In Strategies (Initial Registry Population)

**Strategy IDs to Create:**

```python
BUILT_IN_STRATEGIES = [
    {
        'strategy_id': 'unified_v1',
        'strategy_type': 'unified',
        'version': '1.0.0',
        'status': 'built_in',
        'parameters': {
            'score_threshold_buy': 5.0,
            'score_threshold_sell': -5.0,
            'enable_regime_detection': True
        },
        'notes': 'Default unified strategy with regime detection'
    },
    {
        'strategy_id': 'deterministic_v1',
        'strategy_type': 'deterministic',
        'version': '1.0.0',
        'status': 'built_in',
        'parameters': {
            'min_aligned_timeframes': 4,
            'min_confidence_score': 75.0,
            'min_risk_reward': 2.0,
            'require_higher_tf_agreement': True
        },
        'notes': 'True multi-timeframe deterministic indicators (>=4/5 TFs, 75% conf, 2:1 R:R)'
    },
    {
        'strategy_id': 'quick_v1',
        'strategy_type': 'quick',
        'version': '1.0.0',
        'status': 'built_in',
        'parameters': {
            'min_confidence_score': 60.0,
            'min_risk_reward': 1.5,
            'max_hold_hours': 2.0,
            'require_volume_confirmation': True
        },
        'notes': 'True 5m momentum quick mode (60% conf, 1.5:1 R:R, 2hr max hold)'
    },
    {
        'strategy_id': 'flow_v1',
        'strategy_type': 'flow',
        'version': '1.0.0',
        'status': 'built_in',
        'parameters': {
            'score_threshold_buy': 3.0,
            'score_threshold_sell': -3.0,
            'min_premium': 40000.0,
            'signal_cooldown_minutes': 30
        },
        'notes': 'Historical flow replay using real Polygon options trade data (pending real-data validation)'
    },
    {
        'strategy_id': 'ai_v1_proxy',
        'strategy_type': 'ai',
        'version': '1.0.0',
        'status': 'built_in',
        'parameters': {
            'min_confidence_score': 70.0,
            'require_mtf_alignment': True
        },
        'notes': 'AI-proxy using MTF analysis + AI thresholds (not true Claude analysis - partial routing only)'
    }
]
```

**Important:** Flow should note "pending real-data validation", AI should be labeled honestly as "proxy".

---

## 5. Variant Generation Examples

### Example 1: Deterministic Variant

**Base:** `deterministic_v1` (75% confidence, 4/5 TFs, 2:1 R:R)

**Variant:** `deterministic_v1.1` (70% confidence, 4/5 TFs, 2:1 R:R)

**Changes:**
```python
{
    'parent_strategy_id': 'deterministic_v1',
    'parameter_changes': {
        'min_confidence_score': {'old': 75.0, 'new': 70.0}
    },
    'hypothesis': 'Lower confidence threshold may capture more trades with acceptable quality'
}
```

---

### Example 2: Quick Variant

**Base:** `quick_v1` (2hr max hold, 60% confidence)

**Variant:** `quick_v1.1` (1.5hr max hold, 60% confidence)

**Changes:**
```python
{
    'parent_strategy_id': 'quick_v1',
    'parameter_changes': {
        'max_hold_hours': {'old': 2.0, 'new': 1.5}
    },
    'hypothesis': 'Shorter hold time may improve win rate by reducing exposure to reversals'
}
```

---

## 6. Evaluation Workflow

### Step 1: Generate Variant
```python
POST /api/v1/strategies/registry/variants/generate
{
    "parent_strategy_id": "deterministic_v1",
    "parameter_changes": {
        "min_confidence_score": 70.0
    },
    "hypothesis": "Lower threshold for more trades"
}

Response:
{
    "strategy_id": "deterministic_v1.1",
    "status": "candidate",
    "parameters": {...}
}
```

---

### Step 2: Evaluate Variant
```python
POST /api/v1/strategies/registry/variants/evaluate
{
    "strategy_id": "deterministic_v1.1",
    "backtest_config": {
        "ticker": "MES",
        "days": 90
    }
}

Response:
{
    "evaluation_id": 123,
    "comparison_id": "comp_20260314_120000",
    "results": {
        "sharpe_ratio": 1.25,
        "win_rate": 55.2,
        "max_drawdown": 8.5,
        "total_trades": 42
    },
    "criteria_results": {
        "min_sharpe": "PASS",
        "min_win_rate": "PASS",
        "max_drawdown": "PASS",
        "outperforms_parent": "PASS"
    },
    "recommendation": "APPROVE"
}
```

---

### Step 3: Promote (Requires Human Approval)
```python
POST /api/v1/strategies/registry/variants/promote
{
    "strategy_id": "deterministic_v1.1",
    "approved_by": "user@example.com",
    "approval_notes": "Verified: better Sharpe, good win rate, acceptable DD"
}

Response:
{
    "strategy_id": "deterministic_v1.1",
    "status": "approved_for_router",
    "approved_at": "2026-03-14T12:00:00Z"
}
```

---

## 7. Promotion Criteria Implementation

### Automatic Criteria (Recommendation Only)

```python
class EvaluationCriteria:
    """Criteria for evaluating strategy variants."""

    MIN_SHARPE_RATIO = 1.0
    MIN_WIN_RATE = 50.0
    MAX_DRAWDOWN = 10.0
    MIN_TRADES = 30
    MIN_BACKTEST_DAYS = 30

    def evaluate(self, backtest_results: Dict) -> Dict[str, str]:
        """
        Evaluate backtest results against criteria.

        Returns: Dict of criteria → PASS/FAIL
        """
        results = {}

        results['min_sharpe'] = 'PASS' if backtest_results['sharpe_ratio'] >= self.MIN_SHARPE_RATIO else 'FAIL'
        results['min_win_rate'] = 'PASS' if backtest_results['win_rate'] >= self.MIN_WIN_RATE else 'FAIL'
        results['max_drawdown'] = 'PASS' if abs(backtest_results['max_drawdown']) <= self.MAX_DRAWDOWN else 'FAIL'
        results['min_trades'] = 'PASS' if backtest_results['total_trades'] >= self.MIN_TRADES else 'FAIL'

        return results

    def recommend_action(self, criteria_results: Dict[str, str]) -> str:
        """
        Recommend APPROVE or REJECT based on criteria.

        Returns: 'APPROVE' or 'REJECT'
        """
        if all(v == 'PASS' for v in criteria_results.values()):
            return 'APPROVE'
        else:
            return 'REJECT'
```

### Human Confirmation Required

**IMPORTANT:** Automatic recommendation only - human must approve!

```python
# Promotion requires explicit human approval
def promote_variant(strategy_id: str, approved_by: str, notes: str):
    """
    Promote variant to approved_for_router status.

    Requires:
    - Evaluation passed
    - Human approval (approved_by)
    - Approval notes (why approved)
    """
    strategy = get_strategy(strategy_id)

    if strategy.status != 'candidate':
        raise ValueError("Only candidates can be promoted")

    # Check evaluation exists
    evaluation = get_latest_evaluation(strategy_id)
    if not evaluation:
        raise ValueError("Strategy must be evaluated first")

    # Require human approval
    if not approved_by or not notes:
        raise ValueError("Human approval required (approved_by + notes)")

    # Promote
    strategy.status = 'approved_for_router'
    strategy.approved_at = datetime.now()
    strategy.approved_by = approved_by
    strategy.approval_notes = notes

    db.commit()
```

---

## 8. Router Integration

### Update Engine Router

**Before Phase 6:**
```python
AUTO_ELIGIBLE_ENGINES = ['unified', 'deterministic', 'quick']
```

**After Phase 6:**
```python
def get_auto_eligible_strategies() -> List[str]:
    """
    Get strategies eligible for auto-routing.

    Only strategies with status 'built_in' or 'approved_for_router'
    can be auto-routed.
    """
    registry = get_strategy_registry()
    strategies = registry.list_strategies(
        status=['built_in', 'approved_for_router']
    )
    return [s.strategy_id for s in strategies]
```

**Router queries registry dynamically instead of hardcoded list.**

---

## 9. Safety Guardrails

### A. No Uncontrolled Self-Modification

**Guardrails:**
- ✅ All variants start as `candidate` status
- ✅ Candidates NEVER auto-route (manual selection only)
- ✅ Promotion requires human approval
- ✅ Full audit trail (who, when, why)
- ✅ Built-in strategies cannot be modified (only variants created)

---

### B. Evaluation Before Deployment

**Guardrails:**
- ✅ Variant must be evaluated before promotion
- ✅ Evaluation must pass minimum criteria
- ✅ Backtest must be minimum 30 days
- ✅ Minimum 30 trades for statistical significance

---

### C. Rollback Capability

**Guardrails:**
- ✅ Approved strategies can be retired (status → `retired`)
- ✅ Built-in strategies always available as fallback
- ✅ Version history preserved
- ✅ Can revert to previous approved variant

---

## 10. UI Requirements

### Strategy Registry Dashboard

**Features:**
- List all strategies (filterable by status, type)
- View strategy details (parameters, performance, history)
- Generate variant (parameter editor)
- Evaluate variant (trigger backtest)
- View evaluation results
- Approve/reject variant (with notes)
- Retire strategy

**Example UI Flow:**
```
1. User navigates to Strategy Registry
2. Sees list of built-in strategies (unified_v1, deterministic_v1, etc.)
3. Clicks "Generate Variant" on deterministic_v1
4. Adjusts min_confidence_score from 75% → 70%
5. Adds hypothesis note
6. Clicks "Create Candidate"
7. System creates deterministic_v1.1 with status=candidate
8. User clicks "Evaluate" → triggers 90-day backtest
9. Results show: Sharpe=1.25, Win Rate=55%, Recommendation=APPROVE
10. User reviews, adds approval notes, clicks "Approve"
11. Strategy status → approved_for_router
12. Router can now auto-select deterministic_v1.1
```

---

## 11. Files to Create

### Services
- `app/services/strategy_registry/__init__.py`
- `app/services/strategy_registry/registry.py` - Main registry service
- `app/services/strategy_registry/variant_generator.py` - Variant generation
- `app/services/strategy_registry/evaluator.py` - Evaluation engine
- `app/services/strategy_registry/promoter.py` - Promotion logic
- `app/services/strategy_registry/schemas.py` - Pydantic schemas

### Models
- `app/models/strategy_registry_models.py` - Database models

### Routers
- `app/routers/strategy_registry.py` - API endpoints

### UI
- `ui-next/src/app/dashboard/strategy-registry/page.tsx` - Main registry page
- `ui-next/src/components/strategy-registry/` - UI components

---

## 12. Implementation Phases

### Phase 6A: Registry Foundation
1. Create database models
2. Create registry service
3. Seed with built-in strategies
4. API endpoints for CRUD

### Phase 6B: Variant Generation
1. Variant generator service
2. Parameter mutation logic
3. Parent-child tracking
4. API endpoints

### Phase 6C: Evaluation Pipeline
1. Evaluator service
2. Integration with comparison_runner
3. Criteria checking
4. API endpoints

### Phase 6D: Promotion Engine
1. Promotion logic
2. Human approval workflow
3. Audit trail
4. API endpoints

### Phase 6E: Router Integration
1. Update engine router to query registry
2. Filter by status
3. Version selection logic

### Phase 6F: UI
1. Strategy list view
2. Variant generation form
3. Evaluation results view
4. Approval workflow UI

---

## 13. Success Criteria

**Minimum Success:**
- ✅ Registry database exists
- ✅ Built-in strategies seeded
- ✅ Can create variants
- ✅ Can evaluate variants
- ✅ Can promote/reject with human approval
- ✅ Router queries registry (not hardcoded)
- ✅ Full audit trail

**Stronger Success:**
- ✅ UI for strategy management
- ✅ Evaluation reports generated
- ✅ Statistical criteria implemented
- ✅ At least one variant promoted
- ✅ Router successfully uses approved variant

---

## 14. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| **Overfitting variants to backtest data** | Require out-of-sample validation, min 90-day backtest, forward-test before production |
| **Too many candidates flooding registry** | Limit candidates per base strategy, auto-retire old candidates |
| **Poor variant approval decisions** | Require human approval, full evaluation report, audit trail |
| **Performance degradation of approved variants** | Monitor live performance, auto-flag underperformers, easy rollback |
| **Registry becoming too complex** | Start simple, iterate, keep UI clean |

---

## 15. Open Questions for User

1. **Variant Generation:**
   - Should variant generation be automatic (grid search) or manual (user-specified)?
   - How many variants allowed per base strategy?

2. **Evaluation:**
   - Should we require out-of-sample validation (e.g., 60-day train, 30-day test)?
   - Should forward-testing be required before promotion?

3. **Promotion:**
   - Who can approve variants (any user, admin only)?
   - Should approval require multiple human reviewers?

4. **Retirement:**
   - Should approved strategies be auto-retired after underperformance?
   - Or require manual retirement?

---

## 16. Conclusion

**Feasibility:** ✅ **YES** - Strategy Registry + Variant Evaluation Pipeline is fully feasible

**Foundation:** Existing comparison framework provides strong base for evaluation

**Recommendation:** Implement in phases (6A → 6F), starting with registry foundation

**Key Principle:** **Controlled experimentation with human oversight** - NOT uncontrolled self-modification

---

**Phase 6 Discovery Status:** ✅ **COMPLETE**
**Ready for Implementation:** ✅ **YES**
**Implementation Approach:** Phased rollout with safety guardrails

---

*Report generated on March 14, 2026*
