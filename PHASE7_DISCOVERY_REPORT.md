# Phase 7 Discovery Report
## Forward-Test Gate for Promoted Variants

**Date**: 2026-03-14
**Scope**: Safety bridge between backtest-approved and router-eligible strategies

---

## Current State Analysis

### Existing Forward Test System

**Database Models** (`app/models/forward_test_models.py`):
- ✅ `ForwardTestTrade`: Complete trade record with decision snapshot
  - Has `engine_type` field (flow, ai_enhancement, deterministic, quick)
  - Has `session_id` for grouping
  - Full decision context (regime, indicators, confidence, etc.)
- ✅ `ForwardTestSession`: Session metadata
  - Groups trades by session_id
  - Tracks performance summary (total_trades, win_rate, total_pnl, max_drawdown)
  - **MISSING**: No `strategy_id` linkage

**Current Strategy Lifecycle** (`app/services/strategy_registry/schemas.py`):
```python
class StrategyStatus(str, Enum):
    BUILT_IN = "built_in"
    CANDIDATE = "candidate"
    APPROVED_FOR_ROUTER = "approved_for_router"  # ⚠️ Currently no forward-test gate
    REJECTED = "rejected"
    RETIRED = "retired"
```

**Gap**: Strategies can jump from backtest evaluation directly to `approved_for_router` without forward testing.

---

## Phase 7 Implementation Plan

### Part 1: Status Model Upgrade

**New Lifecycle Statuses**:
```python
class StrategyStatus(str, Enum):
    BUILT_IN = "built_in"
    CANDIDATE = "candidate"
    APPROVED_FOR_FORWARD_TEST = "approved_for_forward_test"  # NEW
    FORWARD_TESTING = "forward_testing"  # NEW
    APPROVED_FOR_ROUTER = "approved_for_router"
    ACTIVE = "active"  # NEW (router-eligible + actively selected)
    REJECTED = "rejected"
    RETIRED = "retired"
    ARCHIVED = "archived"  # NEW (historical record)
```

**Lifecycle Flow**:
```
candidate
  → (backtest eval) →
approved_for_forward_test
  → (start forward test) →
forward_testing
  → (gate evaluation) →
approved_for_router
  → (router selection) →
active
```

**Router Eligibility**: Only `built_in`, `approved_for_router`, `active`

---

### Part 2: Forward-Test Gate Data Model

**Option A: Extend ForwardTestSession** (RECOMMENDED)
Add to `ForwardTestSession`:
```python
# Strategy Linkage
strategy_id = Column(String, ForeignKey('smartflow_strategies.strategy_id'), nullable=True)

# Forward-Test Gate Fields
forward_test_status = Column(String)  # 'in_progress', 'passed', 'failed'
gate_decision_at = Column(DateTime)
gate_decision_by = Column(String)
gate_decision_reason = Column(Text)
gate_criteria_results = Column(JSON)  # Detailed gate evaluation
```

**Option B: New ForwardTestGate Model**
Separate table linking strategy_id to forward-test sessions with gate decisions.

**DECISION**: Use Option A (extend ForwardTestSession) for simpler querying.

---

### Part 3: Forward-Test Evaluation Policy

**Gate Criteria** (`app/services/strategy_registry/forward_test_gate.py`):

```python
class ForwardTestGateCriteria:
    MIN_TRADES = 30
    MIN_WIN_RATE = 45.0  # percent
    MAX_DRAWDOWN_LIMIT = 25.0  # percent
    MIN_PROFIT_FACTOR = 1.2
    MAX_BACKTEST_DEGRADATION = 15.0  # percent (win rate)
```

**All criteria must pass for approval.**

**Decision Output**:
- pass/fail
- criteria_results (list of pass/fail per criterion)
- decision_reason (human-readable)
- degradation_analysis (vs backtest profile)

---

### Part 4: Forward-Test Integration

**Changes Needed**:

1. **ForwardTestSession Model**:
   - Add `strategy_id` field
   - Add gate evaluation fields
   - Add relationship to SmartFlowStrategy

2. **Forward Test Service** (`app/services/forward_test.py`):
   - Accept optional `strategy_id` parameter when creating session
   - Store strategy_id with session

3. **Strategy Registry**:
   - Add method to link strategy to forward-test session
   - Add method to evaluate forward-test gate
   - Add method to promote after gate pass

---

### Part 5: API Endpoints

**New Endpoints**:
```
GET    /api/strategies/{strategy_id}/forward-test-status
POST   /api/strategies/{strategy_id}/start-forward-test
POST   /api/strategies/{strategy_id}/link-forward-test-session
GET    /api/strategies/{strategy_id}/forward-test-results
POST   /api/strategies/{strategy_id}/evaluate-forward-test-gate
POST   /api/strategies/{strategy_id}/approve-for-router
POST   /api/strategies/{strategy_id}/fail-forward-test
GET    /api/strategies/router-eligible
```

---

### Part 6: Router Eligibility Filter

**Current Router** (`app/services/smartflow_service.py` or adaptive router):
- Need to add strategy status filter
- Only select from: `built_in`, `approved_for_router`, `active`

**Implementation**:
- Add `get_router_eligible_strategies()` to registry
- Router calls this to get allowed strategies
- Router metadata includes: strategy_id, status, is_built_in

---

### Part 7: UI/API Visibility

**Minimum API Response**:
```json
{
  "strategy_id": "deterministic_v1.1",
  "status": "forward_testing",
  "forward_test": {
    "session_id": "FT_20260314_170424",
    "total_trades": 25,
    "win_rate": 52.0,
    "net_pnl": 125.50,
    "max_drawdown": 8.5,
    "started_at": "2026-03-14T17:04:24Z",
    "gate_status": "in_progress",
    "required_trades": 30,
    "trades_remaining": 5
  },
  "router_eligible": false
}
```

---

### Part 8: Auditability

**Audit Trail Fields**:
- Forward test session: strategy_id, session_id, started_at, ended_at
- Gate decision: decision_by, decision_at, decision_reason, criteria_results
- Status changes: approved_for_forward_test_at/by, forward_testing_at, approved_for_router_at/by
- Router selection: selected_strategy_id, strategy_status, is_built_in, selection_reason

---

## Implementation Sequence

1. ✅ Discovery (this document)
2. Update StrategyStatus enum (schemas.py)
3. Extend ForwardTestSession model (forward_test_models.py)
4. Update SmartFlowStrategy model with new status fields
5. Create ForwardTestGate service (forward_test_gate.py)
6. Add registry methods for forward-test workflow
7. Create API endpoints
8. Update router eligibility filter
9. Database migration
10. Terminal verification
11. Completion report

---

## Verification Plan

**Terminal Tests**:
```bash
# 1. Create variant and approve for forward test
curl -X POST http://127.0.0.1:8000/api/strategies/deterministic_v1.1/approve-for-forward-test

# 2. Start forward test
curl -X POST http://127.0.0.1:8000/api/strategies/deterministic_v1.1/start-forward-test

# 3. Check status
curl http://127.0.0.1:8000/api/strategies/deterministic_v1.1/forward-test-status

# 4. Evaluate gate (after 30 trades)
curl -X POST http://127.0.0.1:8000/api/strategies/deterministic_v1.1/evaluate-forward-test-gate

# 5. Verify router eligibility
curl http://127.0.0.1:8000/api/strategies/router-eligible
```

**Success Criteria**:
- One variant moves through full lifecycle
- Forward-test metrics tracked per strategy_id
- Gate pass/fail decision recorded
- Router excludes non-eligible strategies
- Full audit trail exists

---

## Risks & Mitigations

**Risk 1**: Forward test sessions without strategy_id
- **Mitigation**: Make strategy_id nullable, support both old (engine_type) and new (strategy_id) sessions

**Risk 2**: Accidental router promotion
- **Mitigation**: Explicit status check in router, fail-safe to built_ins only

**Risk 3**: Manual forward-test association complexity
- **Mitigation**: Start with manual linkage, automate in future phase

---

## Next Steps

Proceed with implementation following the sequence above.

*End of Discovery Report*
