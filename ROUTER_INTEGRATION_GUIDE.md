# Router Integration Guide - Phase 7
## Forward-Test Gate Eligibility Filter

**Date**: 2026-03-14
**Purpose**: Ensure router only selects strategies that passed forward-test gate

---

## Router Eligibility Rules

**Phase 7 Safety Requirement**: The router MUST only consider strategies with these statuses:
- `built_in`
- `approved_for_router`
- `active`

**Blocked Statuses**:
- `candidate` - Not evaluated
- `approved_for_forward_test` - Backtest only, not forward tested
- `forward_testing` - Currently in forward test
- `rejected` - Failed criteria
- `retired` - Retired from service
- `archived` - Historical record

---

## Implementation

### Get Router-Eligible Strategies

```python
from app.services.strategy_registry import get_strategy_registry

# Get all router-eligible strategies
registry = get_strategy_registry()
eligible_strategies = registry.get_router_eligible_strategies()

# Filter by type if needed
deterministic_strategies = [s for s in eligible_strategies if s.strategy_type == 'deterministic']
```

### Mark Strategy as Active (When Router Selects It)

```python
from app.services.strategy_registry import get_strategy_registry

registry = get_strategy_registry()

# When router selects a strategy
registry.mark_strategy_active(strategy_id="deterministic_v1.1")
```

---

## Router Integration Points

### 1. SmartFlow Service Router Selection

**File**: `app/services/smartflow_service.py` or adaptive router

**Current Logic** (example):
```python
# OLD - selects by engine_type only
def select_engine(self):
    if deterministic_conditions_met:
        return 'deterministic'
    elif quick_conditions_met:
        return 'quick'
    # ... etc
```

**Phase 7 Updated Logic**:
```python
from app.services.strategy_registry import get_strategy_registry

def select_engine(self):
    # Get router-eligible strategies
    registry = get_strategy_registry()
    eligible = registry.get_router_eligible_strategies()

    # Filter by type for current conditions
    if deterministic_conditions_met:
        deterministic_strategies = [s for s in eligible if s.strategy_type == 'deterministic']
        if deterministic_strategies:
            # Select best variant (by performance, recency, etc.)
            selected = max(deterministic_strategies, key=lambda s: s.sharpe_ratio or 0)
            registry.mark_strategy_active(selected.strategy_id)
            return selected.strategy_type, selected.strategy_id

    # Fallback to built-ins
    return 'deterministic', 'deterministic_v1'
```

### 2. Adaptive Router (Data-Driven Selection)

**File**: Adaptive router service

**Phase 7 Filter**:
```python
def get_best_engine_for_regime(regime: str):
    registry = get_strategy_registry()
    eligible = registry.get_router_eligible_strategies()

    # Filter by regime performance (from comparison_store)
    # Only consider eligible strategies
    eligible_ids = {s.strategy_id for s in eligible}

    # Query comparison_store for regime performance
    # Filter results to only include eligible_ids

    # Return best eligible strategy
```

---

## Audit Trail

### Router Selection Logging

When router selects a strategy, log:
```python
logger.info(
    f"Router selected strategy: {strategy_id} "
    f"(type={strategy_type}, status={status}, "
    f"is_built_in={parent_strategy_id is None}, "
    f"sharpe={sharpe_ratio}, win_rate={win_rate})"
)
```

### Router Output Metadata

Include in router response:
```json
{
  "selected_strategy": {
    "strategy_id": "deterministic_v1.1",
    "strategy_type": "deterministic",
    "status": "active",
    "is_built_in": false,
    "parent_strategy_id": "deterministic_v1",
    "performance": {
      "sharpe_ratio": 1.85,
      "win_rate": 58.5,
      "forward_test_trades": 45
    }
  }
}
```

---

## Safety Checks

### Fail-Safe: Block Non-Eligible Strategies

```python
def is_strategy_router_eligible(strategy_id: str) -> bool:
    """
    Check if strategy is router-eligible.

    Fail-safe: Returns False for any non-eligible status.
    """
    from app.services.strategy_registry import get_strategy_registry, StrategyStatus

    registry = get_strategy_registry()
    strategy = registry.get_strategy(strategy_id)

    if not strategy:
        return False

    eligible_statuses = [
        StrategyStatus.BUILT_IN.value,
        StrategyStatus.APPROVED_FOR_ROUTER.value,
        StrategyStatus.ACTIVE.value,
    ]

    return strategy.status in eligible_statuses
```

### Router Pre-Selection Validation

```python
def validate_router_selection(strategy_id: str):
    """Validate strategy before router uses it."""
    if not is_strategy_router_eligible(strategy_id):
        logger.warning(
            f"Router attempted to select non-eligible strategy: {strategy_id}. "
            f"Falling back to built-in."
        )
        return False
    return True
```

---

## Testing Router Integration

### Test 1: Only Eligible Strategies Returned

```bash
# Get router-eligible strategies
curl http://127.0.0.1:8000/api/strategies/router-eligible | jq '.[] | {strategy_id, status}'

# Should only show: built_in, approved_for_router, active
```

### Test 2: Non-Eligible Strategy Blocked

```python
# Create candidate variant
# Verify it does NOT appear in router-eligible list

from app.services.strategy_registry import get_strategy_registry

registry = get_strategy_registry()
eligible = registry.get_router_eligible_strategies()
eligible_ids = {s.strategy_id for s in eligible}

assert "deterministic_v1.1" not in eligible_ids  # candidate
```

### Test 3: Forward-Test Passed Strategy Eligible

```python
# Approve variant for router
# Verify it DOES appear in router-eligible list

registry.approve_for_router_after_gate(...)
eligible = registry.get_router_eligible_strategies()
eligible_ids = {s.strategy_id for s in eligible}

assert "deterministic_v1.1" in eligible_ids  # approved_for_router
```

---

## Next Steps for Full Router Integration

1. **Identify current router location** (SmartFlow service, adaptive router, etc.)
2. **Add eligibility filter** at strategy selection point
3. **Update selection logic** to choose from eligible strategies only
4. **Add audit logging** for strategy selection
5. **Test fail-safe** behavior when no eligible strategies match conditions

---

*End of Router Integration Guide*
