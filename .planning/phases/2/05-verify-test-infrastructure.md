# Plan: Verify Test Infrastructure

## Metadata

```yaml
phase: 2
plan: 05
title: Verify Test Infrastructure
wave: 3
depends_on: [01, 02, 03, 04]
files_modified: []
autonomous: true
requirements: [TEST-01, TEST-02, TEST-03]
```

## Goal

Verify all Phase 2 success criteria are met: tests collect without errors, tests pass, and broker error handling has coverage.

## Must-Haves

### Truths (post-execution verifiable statements)
- pytest runs without fixture errors
- All tests pass (or are skipped with documented reason)
- Broker executor error scenarios have test coverage

### Artifacts
- None (verification only)

### Key Links
- ROADMAP.md Phase 2 success criteria
- All Phase 2 plans

## Context

### Purpose
Final verification of Phase 2 completion.

### Prerequisites
Plans 01-04 must be complete.

## Tasks

### Task 1: Verify pytest configuration
**Type:** auto

Check pytest config files exist.

**Command:**
```bash
echo "=== Checking pytest config ==="
test -f pytest.ini && echo "pytest.ini: exists" || echo "pytest.ini: MISSING"
test -f tests/conftest.py && echo "conftest.py: exists" || echo "conftest.py: MISSING"
```

### Task 2: Verify test collection
**Type:** auto

Run pytest --collect-only and check for errors.

**Command:**
```bash
echo "=== Test Collection ==="
python3 -m pytest --collect-only tests/ 2>&1 | grep -E "collected|error" | tail -5
```

**Success criteria:** 0 errors in collection.

### Task 3: Verify tests pass
**Type:** auto

Run full test suite.

**Command:**
```bash
echo "=== Running Tests ==="
python3 -m pytest tests/ --tb=no -q 2>&1 | tail -10
```

**Success criteria:** "X passed, Y skipped" with 0 failures.

### Task 4: Verify broker error tests exist
**Type:** auto

Check broker error handling tests.

**Command:**
```bash
echo "=== Broker Error Tests ==="
test -f tests/test_broker_errors.py && echo "test_broker_errors.py: exists" || echo "test_broker_errors.py: MISSING"
python3 -m pytest tests/test_broker_errors.py --collect-only 2>&1 | grep -E "Function|Class" | head -10
```

### Task 5: Summary report
**Type:** auto

Generate summary of test infrastructure state.

**Command:**
```bash
echo "=== Phase 2 Summary ==="
echo "Test files:"
ls -1 tests/test_*.py | wc -l
echo "---"
python3 -m pytest tests/ --collect-only -q 2>&1 | tail -3
```

## Verification

Phase 2 success criteria from ROADMAP.md:

| Criteria | Verification |
|----------|--------------|
| pytest runs without fixture errors | Task 2 |
| All tests pass (or skipped with reason) | Task 3 |
| Broker error scenarios have test coverage | Task 4 |

## Rollback

N/A - verification only

---
*Plan created: Phase 2 verification*
