# v1.2 Roadmap - Broker Integration & Account UX Polish

**Created:** 2026-01-24
**Status:** Active
**Goal:** Production readiness for all broker integrations with excellent UX

---

## Phase 2: Infrastructure Fixes (Quick Wins)

**Objective:** Fix immediate blockers discovered during rehydration.

**Status:** 🔄 In Progress

### Wave 1: Code Fixes (Done)

| Task | File | Status |
|------|------|--------|
| Fix SQLAlchemy Column description params | database_models.py | ✅ Done |
| Fix missing Dict/Any imports | accounts.py | ✅ Done |

### Wave 2: Alembic Template

| Task | File | Status |
|------|------|--------|
| Create alembic script.py.mako template | alembic/ | 🔲 Pending |
| Verify alembic revision works | N/A | 🔲 Pending |

### Success Criteria
- [ ] `python3 -m py_compile app/**/*.py` passes
- [ ] `alembic revision --autogenerate` works
- [ ] Backend starts and health check passes

---

## Phase 3: Order Placement Verification

**Objective:** Verify order placement works end-to-end with real broker accounts.

**Status:** 🔲 Pending

### Wave 1: TradeLocker Orders

| Task | Description | Status |
|------|-------------|--------|
| Test TradeLocker SDK authentication with real credentials | Connect to demo account | 🔲 Pending |
| Place test market order via SDK | Small position, verify execution | 🔲 Pending |
| Verify order status updates via WebSocket | Real-time updates | 🔲 Pending |

### Wave 2: ProjectX Orders

| Task | Description | Status |
|------|-------------|--------|
| Test ProjectX Gateway API authentication | loginKey → JWT | 🔲 Pending |
| Place test market order via API | Small position, verify execution | 🔲 Pending |
| Verify position shows in dashboard | Cross-check with broker | 🔲 Pending |

### Success Criteria
- [ ] TradeLocker: Can place and confirm a trade
- [ ] ProjectX: Can place and confirm a trade
- [ ] No 500 errors during order flow

---

## Phase 4: Dynamic UI Forms

**Objective:** UI forms render from /api/v1/brokers/contracts schema.

**Status:** 🔲 Pending

### Wave 1: Schema Integration

| Task | File | Status |
|------|------|--------|
| Fetch schemas from API on form mount | account-form.tsx | 🔲 Pending |
| Render fields dynamically based on schema | account-form.tsx | 🔲 Pending |
| Handle field types (string, password, select) | account-form.tsx | 🔲 Pending |

### Wave 2: Polish

| Task | Description | Status |
|------|-------------|--------|
| Add loading state while fetching schema | Skeleton loader | 🔲 Pending |
| Add fallback if schema fetch fails | Use hardcoded fallback | 🔲 Pending |
| Validate required fields from schema | Client-side validation | 🔲 Pending |

### Success Criteria
- [ ] Adding new broker fields in backend appears in UI automatically
- [ ] No hardcoded broker-specific field logic in UI
- [ ] Form validation matches schema requirements

---

## Phase 5: Webhook Routing

**Objective:** Signals route to correct account(s) based on webhook key.

**Status:** 🔲 Pending

### Wave 1: Per-Account Routing

| Task | Description | Status |
|------|-------------|--------|
| Webhook key lookup on signal ingestion | Match key to account | 🔲 Pending |
| Route signal to matched account only | Single-account routing | 🔲 Pending |
| Log routing decisions | Debugging support | 🔲 Pending |

### Wave 2: Multi-Account Routing

| Task | Description | Status |
|------|-------------|--------|
| Support enabled_broker_account_ids routing | Route to all enabled | 🔲 Pending |
| Apply default_broker_account_id if no selection | Fallback behavior | 🔲 Pending |
| Signal execution status per-account | Track each execution | 🔲 Pending |

### Success Criteria
- [ ] Signal with account-specific webhook key routes correctly
- [ ] Multi-account routing executes on all enabled accounts
- [ ] Routing decisions logged for debugging

---

## Phase 6: Error Handling & UX Polish

**Objective:** Clear error messages and loading states throughout.

**Status:** 🔲 Pending

### Wave 1: Error Messages

| Task | Description | Status |
|------|-------------|--------|
| Add error detail to 400 responses | Actionable messages | 🔲 Pending |
| Handle credential validation errors | Clear "what's wrong" | 🔲 Pending |
| Handle network/timeout errors | Retry suggestions | 🔲 Pending |

### Wave 2: Loading States

| Task | Description | Status |
|------|-------------|--------|
| Add loading indicators to async operations | Button spinners | 🔲 Pending |
| Add skeleton loaders for data fetching | Account list, etc | 🔲 Pending |
| Disable form submission during loading | Prevent double-submit | 🔲 Pending |

### Success Criteria
- [ ] All error toasts show clear, actionable message
- [ ] Users know when async operation is in progress
- [ ] No silent failures

---

## Phase 7: E2E Testing & Verification

**Objective:** Full end-to-end flow works reliably.

**Status:** 🔲 Pending

### Wave 1: Account Flow

| Task | Description | Status |
|------|-------------|--------|
| Test: Add new account (all brokers) | Credentials → Discovery → Selection | 🔲 Pending |
| Test: Edit existing account | Update credentials, refresh accounts | 🔲 Pending |
| Test: Delete account | Clean removal | 🔲 Pending |

### Wave 2: Signal Flow

| Task | Description | Status |
|------|-------------|--------|
| Test: Receive TradingView webhook | Parse and route | 🔲 Pending |
| Test: Execute trade on broker | Place order, verify | 🔲 Pending |
| Test: Signal appears in dashboard | Status tracking | 🔲 Pending |

### Wave 3: Edge Cases

| Task | Description | Status |
|------|-------------|--------|
| Test: Invalid credentials | Clear error message | 🔲 Pending |
| Test: Broker API down | Graceful failure | 🔲 Pending |
| Test: Duplicate signal | Deduplication works | 🔲 Pending |

### Success Criteria
- [ ] All happy path tests pass
- [ ] All error cases handled gracefully
- [ ] No regression from v1.1

---

## Phase 8: Documentation & Handoff

**Objective:** Clean documentation and stable handoff.

**Status:** 🔲 Pending

### Wave 1: Documentation

| Task | Description | Status |
|------|-------------|--------|
| Update PROJECT.md with v1.2 completion | Mark requirements done | 🔲 Pending |
| Create v1.2 MILESTONE-AUDIT.md | Audit against requirements | 🔲 Pending |
| Update API docs (OpenAPI) | Verify /docs is accurate | 🔲 Pending |

### Wave 2: Cleanup

| Task | Description | Status |
|------|-------------|--------|
| Remove deprecated code | Dead code removal | 🔲 Pending |
| Archive v1.2 roadmap | Move to milestones/ | 🔲 Pending |
| Git commit with clean status | No uncommitted changes | 🔲 Pending |

### Success Criteria
- [ ] PROJECT.md reflects current state
- [ ] No uncommitted files
- [ ] Documentation matches implementation

---

## Summary

| Phase | Name | Status | Priority |
|-------|------|--------|----------|
| 2 | Infrastructure Fixes | 🔄 In Progress | P0 |
| 3 | Order Placement Verification | 🔲 Pending | P0 |
| 4 | Dynamic UI Forms | 🔲 Pending | P1 |
| 5 | Webhook Routing | 🔲 Pending | P1 |
| 6 | Error Handling & UX Polish | 🔲 Pending | P1 |
| 7 | E2E Testing & Verification | 🔲 Pending | P0 |
| 8 | Documentation & Handoff | 🔲 Pending | P2 |

---

*Last Updated: 2026-01-24*
