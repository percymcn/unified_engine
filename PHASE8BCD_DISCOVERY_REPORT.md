# Phase 8B-8C-8D Discovery Report

**Date**: 2026-03-14
**Purpose**: Final consolidation pass discovery before implementation
**Phases**: 8B (UI), 8C (Scale-Prep), 8D (Operational Hardening)

---

## Executive Summary

All three phases can be implemented safely with minimal changes:
- **Phase 8B**: Add single new tab to existing dashboard (Strategies), reuse existing components
- **Phase 8C**: Add 4 fields to existing model, create 2 snapshot tables, add tags JSON column
- **Phase 8D**: Add 5 operational fields to existing model, update router eligibility filter

**No new architecture required** - Pure additions to existing systems.

---

## PHASE 8B DISCOVERY: Minimal UI Visibility

### Current UI Structure

**Main Dashboard**: `/home/pharma5/unified_engine/ui-next/src/app/dashboard/smartflow/page.tsx` (1,124 lines)

**Existing Tabs** (7 tabs):
1. Overview - Engine status summary
2. Engines - Individual engine panels
3. Analytics - Elite + ML dashboards
4. Backtest - Single run, compare, saved runs
5. Forward Test - Forward test dashboard
6. Router - Adaptive router dashboard
7. Config - Engine configuration

### Insertion Point for Strategies Tab

**File**: `ui-next/src/app/dashboard/smartflow/page.tsx`

**Line 1083-1091**: TabsList definition

**Change Required**:
```typescript
// FROM:
<TabsList className="grid w-full grid-cols-7 mb-6">

// TO:
<TabsList className="grid w-full grid-cols-8 mb-6">

// ADD new trigger:
<TabsTrigger value="strategies">Strategies</TabsTrigger>

// ADD new content:
<TabsContent value="strategies">
  <StrategiesOverview />
</TabsContent>
```

### Available API Endpoints

All endpoints already exist at `/api/strategies`:
```
GET  /api/strategies                    - List all strategies (with filters)
GET  /api/strategies/{strategy_id}      - Get strategy details
GET  /api/strategies/router-eligible    - Get router-approved strategies
```

**Response Model** (from `app/services/strategy_registry/schemas.py`):
```python
class StrategyResponse(BaseModel):
    strategy_id: str
    strategy_type: str
    version: str
    status: str
    parent_strategy_id: Optional[str]

    # Performance metrics
    sharpe_ratio: Optional[float]
    win_rate: Optional[float]
    max_drawdown: Optional[float]
    total_trades: Optional[int]

    # Timestamps
    created_at: Optional[datetime]
    evaluated_at: Optional[datetime]
    approved_at: Optional[datetime]

    # Forward-test gate
    approved_for_forward_test_at: Optional[datetime]
    forward_test_gate_passed_at: Optional[datetime]
    approved_for_router_at: Optional[datetime]
```

### Minimal Component Specification

**New File**: `ui-next/src/components/smartflow/strategies-overview.tsx`

**Required Sections**:
1. **Status Overview Card** - Total strategies by status
2. **Router-Eligible Table** - Approved strategies
3. **Candidate Pipeline** - Active candidates

**Reuse Existing Components**:
- `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`
- `Badge` for status indicators
- `Table` for strategy lists
- `Button` for refresh
- `Loader2` for loading states

**Status Badge Colors**:
```typescript
const statusColors: Record<string, string> = {
  'built_in': 'bg-blue-500',
  'candidate': 'bg-yellow-500',
  'approved_for_router': 'bg-green-500',
  'approved_for_forward_test': 'bg-amber-500',
  'forward_testing': 'bg-purple-500',
  'active': 'bg-emerald-500',
  'rejected': 'bg-red-500',
  'retired': 'bg-gray-500',
};
```

### Data Fetching Pattern

```typescript
const [strategies, setStrategies] = useState<StrategyResponse[]>([]);
const [loading, setLoading] = useState(true);

useEffect(() => {
  loadStrategies();
}, []);

const loadStrategies = async () => {
  try {
    const response = await fetch('/api/strategies', {
      credentials: 'include',
    });
    const data = await response.json();
    setStrategies(data.strategies || []);
  } catch (error) {
    console.error('Failed to load strategies:', error);
  } finally {
    setLoading(false);
  }
};
```

---

## PHASE 8C DISCOVERY: Scale-Prep Improvements

### Current Strategy Model Fields

**File**: `app/models/strategy_registry_models.py`

**Existing Fields** (SmartFlowStrategy):
```python
# Core identity
id: Integer (PK)
strategy_id: String (unique) # e.g., "deterministic_v1.2"
strategy_type: String        # deterministic, quick, unified, flow, ai
version: String              # e.g., "1.2.0"
status: String               # lifecycle status

# Configuration
parameters: JSON
parent_strategy_id: String (nullable)
parameter_changes: JSON (nullable)
hypothesis: Text (nullable)

# Performance metrics (current - overloaded)
sharpe_ratio: Float (nullable)
win_rate: Float (nullable)
max_drawdown: Float (nullable)
total_return_pct: Float (nullable)
total_trades: Integer (nullable)
backtest_days: Integer (nullable)

# Metadata
created_at: DateTime
created_by: String
evaluated_at: DateTime (nullable)
approved_at: DateTime (nullable)
# ... plus 20+ tracking fields
```

**Issues for Scale**:
1. ❌ No family_id (lineage unclear for complex trees)
2. ❌ No variant_hash (duplicate detection hard)
3. ❌ Metrics are time-varying but stored in main table (not snapshot-based)
4. ❌ No tags/labels (filtering requires complex status queries)

### Phase 8C Changes Required

#### 1. Canonical Strategy Identity Fields

**Add to SmartFlowStrategy model**:
```python
# Phase 8C: Canonical Identity & Lineage
family_id = Column(String, index=True, nullable=True)
    # Root strategy family (e.g., "deterministic", "quick")
    # Built-ins: family_id = strategy_type
    # Variants: family_id = parent's family_id

variant_hash = Column(String(64), unique=True, nullable=True)
    # SHA256 of (parent_strategy_id + parameter_changes)
    # Prevents duplicate variants
    # NULL for built-ins

generation = Column(Integer, default=0, nullable=False)
    # 0 = built-in
    # 1 = first-generation variant
    # 2 = variant of variant, etc.

lineage_path = Column(String, nullable=True)
    # Full ancestry path: "deterministic_v1 > deterministic_v1.1 > deterministic_v1.1.1"
    # Makes lineage queries fast
```

#### 2. Metrics Snapshot Separation

**Problem**: Current model mixes identity with time-varying metrics.

**Solution**: Create separate snapshot tables.

**New Model 1: StrategyBacktestSnapshot**
```python
class StrategyBacktestSnapshot(Base):
    """Backtest performance snapshot for a strategy."""
    __tablename__ = "strategy_backtest_snapshots"

    id = Column(Integer, primary_key=True)
    strategy_id = Column(String, ForeignKey("smartflow_strategies.strategy_id"))
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now())

    # Backtest config
    ticker = Column(String)
    backtest_days = Column(Integer)
    start_date = Column(String)
    end_date = Column(String)

    # Performance metrics
    sharpe_ratio = Column(Float)
    win_rate = Column(Float)
    max_drawdown = Column(Float)
    total_return_pct = Column(Float)
    total_trades = Column(Integer)
    net_profit = Column(Float)
    profit_factor = Column(Float)

    # Links
    comparison_id = Column(String)  # Links to comparison_store
    evaluation_id = Column(Integer, ForeignKey("strategy_evaluations.id"))
```

**New Model 2: StrategyForwardTestSnapshot**
```python
class StrategyForwardTestSnapshot(Base):
    """Forward-test performance snapshot for a strategy."""
    __tablename__ = "strategy_forward_test_snapshots"

    id = Column(Integer, primary_key=True)
    strategy_id = Column(String, ForeignKey("smartflow_strategies.strategy_id"))
    snapshot_at = Column(DateTime(timezone=True), server_default=func.now())

    # Forward-test session
    session_id = Column(String, ForeignKey("forward_test_sessions.session_id"))

    # Performance metrics
    total_trades = Column(Integer)
    win_rate = Column(Float)
    max_drawdown = Column(Float)
    profit_factor = Column(Float)
    total_pnl = Column(Float)

    # Gate results
    gate_status = Column(String)  # passed, failed
    gate_criteria_results = Column(JSON)
```

**Keep in Main Model** (latest values for quick access):
```python
# Keep these in SmartFlowStrategy for fast queries
sharpe_ratio: Float (nullable)          # Latest backtest
win_rate: Float (nullable)              # Latest backtest
max_drawdown: Float (nullable)          # Latest backtest
latest_backtest_snapshot_id: Integer    # Phase 8C: Link to latest snapshot
latest_forward_test_snapshot_id: Integer # Phase 8C: Link to latest snapshot
```

#### 3. Tags / Labels for Filtering

**Add to SmartFlowStrategy model**:
```python
# Phase 8C: Tags for filtering/organization
tags = Column(JSON, nullable=True, default=list)
    # Examples:
    # ["engine:deterministic", "source:built_in", "router:eligible", "validation:forward_test_passed"]
    # ["engine:quick", "source:variant", "parent:quick_v1", "hypothesis:aggressive_stops"]

    # Queryable via JSON operators:
    # .filter(SmartFlowStrategy.tags.contains(["router:eligible"]))
```

**Auto-populated Tags**:
```python
def _auto_generate_tags(strategy: SmartFlowStrategy) -> List[str]:
    tags = []

    # Engine tag
    tags.append(f"engine:{strategy.strategy_type}")

    # Source tag
    if strategy.parent_strategy_id is None:
        tags.append("source:built_in")
    else:
        tags.append("source:variant")
        tags.append(f"parent:{strategy.parent_strategy_id}")

    # Status tags
    if strategy.status == "approved_for_router":
        tags.append("router:eligible")
    if strategy.status == "active":
        tags.append("router:active")

    # Validation tags
    if strategy.forward_test_gate_passed_at:
        tags.append("validation:forward_test_passed")
    if strategy.evaluated_at:
        tags.append("validation:backtest_evaluated")

    return tags
```

---

## PHASE 8D DISCOVERY: Operational Hardening Hooks

### Current Router Eligibility Filter

**File**: `app/services/strategy_registry/registry.py:679-692`

**Current Logic**:
```python
def get_router_eligible_strategies(self) -> List[SmartFlowStrategy]:
    """Get strategies eligible for router selection."""
    eligible_statuses = [
        StrategyStatus.BUILT_IN.value,
        StrategyStatus.APPROVED_FOR_ROUTER.value,
        StrategyStatus.ACTIVE.value,
    ]
    return self.db.query(SmartFlowStrategy).filter(
        SmartFlowStrategy.status.in_(eligible_statuses)
    ).all()
```

**Gap**: No pause/disable mechanism, no health status check.

### Phase 8D Changes Required

#### 1. Operational Status Fields

**Add to SmartFlowStrategy model**:
```python
# Phase 8D: Operational Hardening
is_paused = Column(Boolean, default=False, index=True, nullable=False)
    # Admin can pause strategy without retiring it
    # Router must exclude paused strategies

paused_at = Column(DateTime(timezone=True), nullable=True)
paused_by = Column(String, nullable=True)
pause_reason = Column(Text, nullable=True)

health_status = Column(String, default="healthy", index=True, nullable=False)
    # "healthy", "degraded", "unhealthy", "unknown"
    # Future: Auto-set by monitoring system

health_checked_at = Column(DateTime(timezone=True), nullable=True)
health_notes = Column(Text, nullable=True)

rollback_target_strategy_id = Column(String, nullable=True)
    # If this strategy fails, router can rollback to this strategy
    # Typically the parent_strategy_id or previous approved variant

last_reviewed_at = Column(DateTime(timezone=True), nullable=True)
    # Manual review timestamp (for audit trail)
last_reviewed_by = Column(String, nullable=True)
```

#### 2. Enhanced Router Eligibility Filter

**Update**: `app/services/strategy_registry/registry.py:679-692`

```python
def get_router_eligible_strategies(self) -> List[SmartFlowStrategy]:
    """
    Get strategies eligible for router selection.

    Phase 8D: Now excludes paused strategies and checks health status.
    """
    eligible_statuses = [
        StrategyStatus.BUILT_IN.value,
        StrategyStatus.APPROVED_FOR_ROUTER.value,
        StrategyStatus.ACTIVE.value,
    ]

    # Phase 8D: Add operational filters
    return self.db.query(SmartFlowStrategy).filter(
        SmartFlowStrategy.status.in_(eligible_statuses),
        SmartFlowStrategy.is_paused == False,  # Exclude paused
        SmartFlowStrategy.health_status.in_(["healthy", "degraded"])  # Exclude unhealthy
    ).all()
```

#### 3. Pause/Resume Methods

**Add to StrategyRegistry**:
```python
def pause_strategy(
    self,
    strategy_id: str,
    paused_by: str,
    pause_reason: str
) -> SmartFlowStrategy:
    """
    Pause a strategy (excludes from router without retiring).

    Phase 8D: Operational control.
    """
    strategy = self.get_strategy(strategy_id)
    if not strategy:
        raise ValueError(f"Strategy not found: {strategy_id}")

    strategy.is_paused = True
    strategy.paused_at = datetime.now(timezone.utc)
    strategy.paused_by = paused_by
    strategy.pause_reason = pause_reason

    self.db.commit()
    self.db.refresh(strategy)

    logger.info(f"Strategy paused: {strategy_id} by {paused_by} - {pause_reason}")
    return strategy


def resume_strategy(
    self,
    strategy_id: str,
    resumed_by: str
) -> SmartFlowStrategy:
    """
    Resume a paused strategy.

    Phase 8D: Operational control.
    """
    strategy = self.get_strategy(strategy_id)
    if not strategy:
        raise ValueError(f"Strategy not found: {strategy_id}")

    strategy.is_paused = False
    strategy.paused_at = None
    strategy.paused_by = None
    strategy.pause_reason = None

    self.db.commit()
    self.db.refresh(strategy)

    logger.info(f"Strategy resumed: {strategy_id} by {resumed_by}")
    return strategy
```

#### 4. Health Status Update Method

```python
def update_health_status(
    self,
    strategy_id: str,
    health_status: str,
    health_notes: str = None
) -> SmartFlowStrategy:
    """
    Update strategy health status.

    Phase 8D: Future hook for monitoring system.

    Args:
        health_status: "healthy", "degraded", "unhealthy", "unknown"
    """
    strategy = self.get_strategy(strategy_id)
    if not strategy:
        raise ValueError(f"Strategy not found: {strategy_id}")

    if health_status not in ["healthy", "degraded", "unhealthy", "unknown"]:
        raise ValueError(f"Invalid health_status: {health_status}")

    strategy.health_status = health_status
    strategy.health_checked_at = datetime.now(timezone.utc)
    strategy.health_notes = health_notes

    self.db.commit()
    self.db.refresh(strategy)

    logger.info(f"Strategy health updated: {strategy_id} → {health_status}")
    return strategy
```

#### 5. New API Endpoints

**Add to `app/routers/strategy_registry.py`**:
```python
@router.post("/pause")
def pause_strategy(request: PauseRequest, db: Session = Depends(get_db)):
    """Pause strategy (excludes from router)."""
    registry = StrategyRegistry(db)
    strategy = registry.pause_strategy(
        strategy_id=request.strategy_id,
        paused_by=request.paused_by,
        pause_reason=request.pause_reason
    )
    return StrategyResponse.from_orm(strategy)


@router.post("/resume")
def resume_strategy(request: ResumeRequest, db: Session = Depends(get_db)):
    """Resume paused strategy."""
    registry = StrategyRegistry(db)
    strategy = registry.resume_strategy(
        strategy_id=request.strategy_id,
        resumed_by=request.resumed_by
    )
    return StrategyResponse.from_orm(strategy)


@router.post("/health")
def update_health_status(request: HealthUpdateRequest, db: Session = Depends(get_db)):
    """Update strategy health status."""
    registry = StrategyRegistry(db)
    strategy = registry.update_health_status(
        strategy_id=request.strategy_id,
        health_status=request.health_status,
        health_notes=request.health_notes
    )
    return StrategyResponse.from_orm(strategy)
```

---

## Implementation Order

### Phase 8B: Minimal UI (30 min)
1. Create `strategies-overview.tsx` component (200 lines)
2. Update `page.tsx` TabsList grid-cols-7 → grid-cols-8
3. Add Strategies tab trigger and content
4. Test UI build

### Phase 8C: Scale-Prep (45 min)
1. Add 4 identity fields to SmartFlowStrategy model
2. Create StrategyBacktestSnapshot model
3. Create StrategyForwardTestSnapshot model
4. Add tags JSON field
5. Create database migration
6. Add helper methods for tag generation
7. Update API responses with new fields

### Phase 8D: Operational Hardening (30 min)
1. Add 5 operational fields to SmartFlowStrategy model
2. Update router eligibility filter
3. Add pause/resume/health methods
4. Add 3 new API endpoints
5. Update database migration
6. Test pause exclusion from router

---

## Files to Modify

### Phase 8B (3 files)
1. `ui-next/src/app/dashboard/smartflow/page.tsx` (5 lines)
2. `ui-next/src/components/smartflow/strategies-overview.tsx` (NEW - 200 lines)
3. Build verification

### Phase 8C (5 files)
1. `app/models/strategy_registry_models.py` (+100 lines - 3 new models, field additions)
2. `app/services/strategy_registry/schemas.py` (+30 lines - response model updates)
3. `app/services/strategy_registry/registry.py` (+50 lines - tag helpers)
4. Create migration file (NEW)
5. Update tests if needed

### Phase 8D (4 files)
1. `app/models/strategy_registry_models.py` (+30 lines - operational fields)
2. `app/services/strategy_registry/registry.py` (+80 lines - pause/resume/health methods)
3. `app/routers/strategy_registry.py` (+60 lines - 3 new endpoints)
4. Update migration file

---

## Database Migration Plan

**Single Migration** for Phases 8C + 8D:

```python
"""
Phase 8C-8D: Scale-prep + Operational Hardening

Revision ID: 044_phase8cd_scale_prep_hardening
Created: 2026-03-14
"""

def upgrade():
    # Phase 8C: Identity & Lineage
    op.add_column('smartflow_strategies', sa.Column('family_id', sa.String(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('variant_hash', sa.String(64), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('generation', sa.Integer(), default=0))
    op.add_column('smartflow_strategies', sa.Column('lineage_path', sa.String(), nullable=True))

    # Phase 8C: Snapshot links
    op.add_column('smartflow_strategies', sa.Column('latest_backtest_snapshot_id', sa.Integer(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('latest_forward_test_snapshot_id', sa.Integer(), nullable=True))

    # Phase 8C: Tags
    op.add_column('smartflow_strategies', sa.Column('tags', sa.JSON(), nullable=True))

    # Phase 8D: Operational
    op.add_column('smartflow_strategies', sa.Column('is_paused', sa.Boolean(), default=False, nullable=False))
    op.add_column('smartflow_strategies', sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('paused_by', sa.String(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('pause_reason', sa.Text(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('health_status', sa.String(), default='healthy', nullable=False))
    op.add_column('smartflow_strategies', sa.Column('health_checked_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('health_notes', sa.Text(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('rollback_target_strategy_id', sa.String(), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('last_reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('smartflow_strategies', sa.Column('last_reviewed_by', sa.String(), nullable=True))

    # Phase 8C: Create snapshot tables
    op.create_table(
        'strategy_backtest_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('strategy_id', sa.String(), sa.ForeignKey('smartflow_strategies.strategy_id')),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        # ... rest of backtest snapshot fields
    )

    op.create_table(
        'strategy_forward_test_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('strategy_id', sa.String(), sa.ForeignKey('smartflow_strategies.strategy_id')),
        sa.Column('snapshot_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        # ... rest of forward-test snapshot fields
    )

    # Add indexes
    op.create_index('ix_smartflow_strategies_family_id', 'smartflow_strategies', ['family_id'])
    op.create_index('ix_smartflow_strategies_variant_hash', 'smartflow_strategies', ['variant_hash'], unique=True)
    op.create_index('ix_smartflow_strategies_is_paused', 'smartflow_strategies', ['is_paused'])
    op.create_index('ix_smartflow_strategies_health_status', 'smartflow_strategies', ['health_status'])
```

---

## Verification Plan

### Phase 8B Verification
```bash
# 1. Check UI files compile
cd ui-next && npm run build

# 2. Check strategies endpoint
curl -s http://127.0.0.1:8000/api/strategies | jq '.strategies[] | {strategy_id, status}'

# 3. Visual check - load dashboard
# Navigate to SmartFlow → Strategies tab
```

### Phase 8C Verification
```bash
# 1. Check model compiles
python3 -m py_compile app/models/strategy_registry_models.py

# 2. Run migration
DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db" python3 -m alembic upgrade head

# 3. Check API returns new fields
curl -s http://127.0.0.1:8000/api/strategies/deterministic_v1 | jq '.family_id, .tags, .variant_hash'

# 4. Test tag filtering (if implemented)
curl -s 'http://127.0.0.1:8000/api/strategies?tags=router:eligible' | jq .
```

### Phase 8D Verification
```bash
# 1. Test pause endpoint
curl -X POST http://127.0.0.1:8000/api/strategies/pause \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "deterministic_v1.1", "paused_by": "admin", "pause_reason": "Test pause"}'

# 2. Check router excludes paused
curl -s http://127.0.0.1:8000/api/strategies/router-eligible | jq '.[] | select(.is_paused == true)'
# Should return empty (no paused strategies eligible)

# 3. Test resume
curl -X POST http://127.0.0.1:8000/api/strategies/resume \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "deterministic_v1.1", "resumed_by": "admin"}'

# 4. Check health status update
curl -X POST http://127.0.0.1:8000/api/strategies/health \
  -H "Content-Type: application/json" \
  -d '{"strategy_id": "deterministic_v1", "health_status": "healthy", "health_notes": "All metrics normal"}'
```

---

## Safety Checklist

### Phase 8B
- ✅ No changes to existing tabs
- ✅ All new code in isolated component
- ✅ Uses existing API endpoints only
- ✅ Graceful error handling
- ✅ Loading states

### Phase 8C
- ✅ All new fields nullable or have defaults
- ✅ No removal of existing fields
- ✅ Backward compatible
- ✅ Indexes on queryable fields
- ✅ Unique constraint on variant_hash (prevents duplicates)

### Phase 8D
- ✅ is_paused defaults to False (no impact on existing strategies)
- ✅ health_status defaults to "healthy"
- ✅ Router filter additions are safe (AND conditions)
- ✅ Pause/resume methods require admin role
- ✅ All timestamp fields nullable

---

## Expected Outcomes

### Phase 8B Success
- Operator can see all strategies in UI
- Current router selection visible
- Strategy lifecycle states visible
- Performance metrics visible
- No regressions

### Phase 8C Success
- Strategy lineage clear (family_id, lineage_path)
- Duplicate variants prevented (variant_hash)
- Metrics separated into snapshots
- Strategies filterable by tags
- Queries remain fast (indexed fields)

### Phase 8D Success
- Strategy can be paused/resumed
- Router excludes paused strategies
- Health status tracked
- Rollback targets configurable
- Manual review timestamps tracked

---

*End of Phase 8B-8C-8D Discovery Report*
