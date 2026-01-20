# Plan: Fix Test Failures

## Metadata

```yaml
phase: 2
plan: 03
title: Fix Test Failures
wave: 2
depends_on: [01, 02]
files_modified:
  - tests/*.py (as needed)
  - app/**/*.py (if bugs found)
autonomous: false
checkpoint_type: human-verify
requirements: [TEST-02]
```

## Goal

Run the test suite and fix failing tests until all tests pass (or are skipped with documented reason).

## Must-Haves

### Truths (post-execution verifiable statements)
- `pytest tests/` exits with code 0 (all tests pass)
- Any skipped tests have documented reason in skip decorator
- No test failures (only passes and documented skips)

### Artifacts
- None (fixing existing tests)

### Key Links
- tests/ - all test files
- CONCERNS.md - "90/101 tests failing" reference

## Context

### Problem
According to CONCERNS.md, 90 of 101 tests are failing. After fixing collection errors (Plan 02), we need to:
1. Run tests and identify failures
2. Categorize failures (fixture issues, logic bugs, environment issues)
3. Fix or skip with documentation

### Solution
Iterative approach:
1. Run pytest with -x (stop on first failure)
2. Fix the failure
3. Repeat until all pass

### Checkpoint
This plan requires human verification because:
- Test failures may indicate real bugs requiring decisions
- Some tests may need to be skipped due to environment constraints
- May discover issues requiring architectural decisions

## Tasks

### Task 1: Run initial test suite
**Type:** checkpoint:human-verify

Run full test suite and capture output.

**Command:**
```bash
python3 -m pytest tests/ -v --tb=short 2>&1 | tee test_results.txt
```

**Checkpoint:** Review test results and categorize failures.

### Task 2: Fix deployment tests
**Type:** auto

Fix any failures in test_deployment.py (these should mostly pass).

**File:** `tests/test_deployment.py`

### Task 3: Fix performance tests
**Type:** auto

Fix any failures in test_performance.py.

**File:** `tests/test_performance.py`

### Task 4: Fix remaining test files
**Type:** auto

Fix failures in other test files as identified.

### Task 5: Document skipped tests
**Type:** auto

For any tests that cannot be fixed without major changes, add skip with reason:
```python
@pytest.mark.skip(reason="Requires live database connection - see TEST-SKIP-001")
def test_something():
    ...
```

### Task 6: Final verification
**Type:** auto

Run full suite and verify all pass.

**Command:**
```bash
python3 -m pytest tests/ -v 2>&1 | tail -20
```

**Success criteria:** "X passed, Y skipped" with 0 failures.

## Verification

After completing all tasks:

```bash
python3 -m pytest tests/ --tb=no -q
# Expected: "X passed, Y skipped in Xs"
# No failures
```

## Rollback

If issues arise:
1. Document test state
2. Failures indicate bugs to fix in later phases

---
*Plan created: Phase 2, TEST-02*
