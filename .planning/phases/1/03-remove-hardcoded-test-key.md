# Plan: Remove Hardcoded Test API Key

## Metadata

```yaml
phase: 1
plan: 03
title: Remove Hardcoded Test API Key
wave: 1
depends_on: []
files_modified:
  - app/routers/auth.py
autonomous: true
requirements: [STAB-04]
```

## Goal

Remove the hardcoded `test-api-key` fallback from the API key verification function. All API key authentication must go through the database.

## Must-Haves

### Truths (post-execution verifiable statements)
- `app/routers/auth.py` does NOT contain the string `"test-api-key"`
- The `verify_api_key` function only validates against database-stored keys
- Invalid API keys return 401 Unauthorized (no fallback bypass)

### Artifacts
- None (modifying existing file only)

### Key Links
- `app/routers/auth.py:259-275` - hardcoded test key fallback logic
- CONCERNS.md: "Hardcoded API Keys in Code" section

## Context

### Problem
The `verify_api_key` function in `app/routers/auth.py` has a hardcoded fallback:

```python
# Fallback to test key for development
if api_key == "test-api-key":
    test_user = get_user_by_username(db, "api_user")
    if test_user:
        return test_user
```

This is a security risk if deployed to production - anyone with knowledge of this key can bypass authentication.

### Solution
Remove the entire test key fallback block. The function already properly checks the database first - if no match is found, it should return 401 Unauthorized.

### References
- CONCERNS.md: "Hardcoded API Keys in Code" tech debt item
- PITFALLS.md: "Hardcoded API keys" risk

## Tasks

### Task 1: Remove hardcoded test key from auth.py
**Type:** auto

Remove the test key fallback block and simplify the function.

**Instructions:**
1. Open `app/routers/auth.py`
2. Find the `verify_api_key` function (line 244)
3. Remove lines 259-275 (the test key fallback block and stale user check)
4. After database check, directly raise HTTPException if user is None

**File:** `app/routers/auth.py`

**Expected change:**

Before (lines 244-279):
```python
async def verify_api_key(api_key: str = Header(None, alias="X-API-Key"), db: Session = Depends(get_db)) -> User:
    """Verify API key"""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    # Try database verification first
    from app.routers.api_keys import verify_api_key_from_db
    user = await verify_api_key_from_db(api_key, db)

    if user:
        return user

    # Fallback to test key for development
    if api_key == "test-api-key":
        test_user = get_user_by_username(db, "api_user")
        if test_user:
            return test_user

    # Check for stale user case
    # ... more code ...

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )
```

After:
```python
async def verify_api_key(api_key: str = Header(None, alias="X-API-Key"), db: Session = Depends(get_db)) -> User:
    """Verify API key against database"""
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )

    # Verify against database
    from app.routers.api_keys import verify_api_key_from_db
    user = await verify_api_key_from_db(api_key, db)

    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key"
    )
```

### Task 2: Verify no hardcoded keys remain
**Type:** auto

Search the codebase for any remaining hardcoded API keys.

**Instructions:**
```bash
cd /home/pharma5/unified_engine
grep -r "test-api-key" app/ --include="*.py"
grep -r "test.*key" app/routers/auth.py
```

**Success criteria:** No matches found.

## Verification

After completing all tasks, verify:

1. **No hardcoded key in auth.py:**
   ```bash
   grep -c "test-api-key" app/routers/auth.py
   # Expected: 0
   ```

2. **Function still works** (syntax check):
   ```bash
   python3 -c "from app.routers.auth import verify_api_key; print('Function imported OK')"
   ```

3. **Invalid key returns 401** (functional test with running service):
   ```bash
   curl -H "X-API-Key: test-api-key" http://localhost:8000/api/v1/status
   # Expected: 401 Unauthorized
   ```

## Rollback

If issues arise:
1. Re-add the test key fallback block to `app/routers/auth.py`
2. Create a proper API key in the database for testing

---
*Plan created: Phase 1, STAB-04*
