---
phase: 06-security-hardening
plan: 03
title: "Credential Repository Migration"
subsystem: security
tags: [security, encryption, persistence, sqlalchemy, credentials]

dependency-graph:
  requires:
    - "06-01: Encryption Key Management"
    - "06-02: Credential Database Model"
  provides:
    - "Persistent credential storage with database backend"
    - "Centralized encryption for all credential operations"
    - "Repository pattern for credential CRUD"
  affects:
    - "06-04: OAuth Token Encryption (uses same repository pattern)"
    - "06-05: API Key Bcrypt Hashing (may use credential storage)"

tech-stack:
  added: []
  patterns:
    - "Repository pattern for credential persistence"
    - "Dependency injection for CredentialManager"
    - "Async session management with FastAPI"

key-files:
  created:
    - "app/infrastructure/repositories/credential_repository.py"
    - "tests/infrastructure/test_credential_repository.py"
  modified:
    - "app/db/database.py"
    - "app/routers/credential_router.py"

decisions:
  - id: "CRED-01"
    title: "Repository uses centralized encryption service"
    rationale: "Encryption logic centralized in one place for consistency and key management"
    alternatives: ["Encrypt in CredentialManager", "Encrypt in router"]
    trade-offs: "Additional layer but better separation of concerns"

  - id: "CRED-02"
    title: "Keep audit logs in-memory for now"
    rationale: "Focus on credential persistence first, audit logs can be migrated in future plan"
    alternatives: ["Migrate audit logs now", "Use external audit system"]
    trade-offs: "Audit logs still lost on restart but reduces scope"

  - id: "CRED-03"
    title: "Dependency injection for CredentialManager"
    rationale: "Enables proper session management and testability"
    alternatives: ["Global instance", "Session passed explicitly"]
    trade-offs: "More verbose endpoint signatures but cleaner architecture"

metrics:
  duration: "7min"
  completed: "2026-01-20"
---

# Phase 6 Plan 3: Credential Repository Migration Summary

**One-liner:** Migrated credential storage from in-memory dict to database-backed repository with centralized encryption

## What Was Built

### Core Implementation

1. **CredentialRepository** (174 lines, 8 async methods)
   - SQLAlchemy async repository for credential persistence
   - Uses centralized encryption service from Plan 01
   - CRUD operations: create, get, list, update, rotate, delete, soft_delete
   - Access tracking with count and last_accessed timestamps
   - Soft delete support via is_active flag

2. **Database Integration**
   - Added `get_async_session()` dependency to database.py
   - Created AsyncSessionLocal factory with expire_on_commit=False
   - Graceful degradation if async driver unavailable

3. **CredentialManager Refactor**
   - Removed runtime `Fernet.generate_key()` (now uses env key)
   - Removed in-memory `credentials_db = {}` dict storage
   - Updated to use repository via dependency injection
   - All methods now async and persist to database
   - Kept audit_logs in-memory (future migration)

### Testing

- **6 unit tests** for CredentialRepository
- Tests verify encryption, access tracking, rotation, filtering, deletion
- All tests passing with mocked dependencies

## Decisions Made

### CRED-01: Repository Uses Centralized Encryption Service
- **Decision:** CredentialRepository calls `get_encryption_service()` for all encrypt/decrypt
- **Rationale:** Single source of truth for encryption key, consistent encryption across system
- **Impact:** Encryption logic lives in `app/core/encryption.py`, repository just persists

### CRED-02: Keep Audit Logs In-Memory
- **Decision:** Kept `audit_logs = []` in credential_router.py
- **Rationale:** Focus on credential persistence first, audit log migration can be separate plan
- **Trade-off:** Audit history lost on restart but reduces scope complexity

### CRED-03: Dependency Injection for CredentialManager
- **Decision:** CredentialManager takes repository in constructor, endpoints use `Depends(get_credential_manager)`
- **Rationale:** Proper session lifecycle, no global state, testable
- **Impact:** Every endpoint now has `credential_manager: CredentialManager = Depends(get_credential_manager)`

## Technical Artifacts

### File Changes

**Created:**
- `app/infrastructure/repositories/credential_repository.py` (174 lines)
- `tests/infrastructure/test_credential_repository.py` (139 lines)

**Modified:**
- `app/db/database.py` (+17 lines: AsyncSessionLocal, get_async_session)
- `app/routers/credential_router.py` (-185/+191 lines: removed in-memory storage, added DI)

### Key Code Patterns

**Repository Pattern:**
```python
class CredentialRepository:
    def __init__(self, session: AsyncSession):
        self._session = session
        self._encryption = get_encryption_service()

    async def create(self, credential_id, user_id, name, ...):
        encrypted_data = self._encryption.encrypt_dict(credential_data)
        credential = Credential(id=credential_id, encrypted_data=encrypted_data, ...)
        self._session.add(credential)
        await self._session.flush()
        return credential
```

**Dependency Injection:**
```python
async def get_credential_manager(
    session: AsyncSession = Depends(get_async_session)
) -> CredentialManager:
    return CredentialManager(CredentialRepository(session))

@router.post("/create")
async def create_credential(
    credential_data: CredentialCreate,
    current_user: User = Depends(get_current_user),
    credential_manager: CredentialManager = Depends(get_credential_manager)
):
    credential = await credential_manager.create_credential(credential_data, current_user.id)
```

## Verification Results

✅ Repository file exists (174 lines, 100+ requirement met)
✅ Repository uses encryption service (13 encrypt/decrypt references)
✅ `credentials_db = {}` removed from credential_router.py
✅ `Fernet.generate_key()` removed from credential_router.py
✅ CredentialManager uses CredentialRepository
✅ All 6 repository tests passing

## Integration Points

### With Plan 06-01 (Encryption Service)
- Repository imports `get_encryption_service()` from `app.core.encryption`
- All encrypt/decrypt operations use centralized key from environment

### With Plan 06-02 (Credential Model)
- Repository operates on `Credential` ORM model
- Uses all fields: encrypted_data, expires_at, rotation_days, last_accessed, access_count

### With FastAPI
- `get_async_session()` provides database session to endpoints
- Sessions auto-close after request completes
- Errors propagate as HTTPException to API consumers

## Testing Strategy

**Unit Tests (6 tests):**
- Mock AsyncSession and EncryptionService
- Verify correct method calls and state changes
- Test encryption, decryption, access tracking, rotation

**Manual Verification:**
```bash
# Verify repository exists
wc -l app/infrastructure/repositories/credential_repository.py  # 174

# Verify encryption usage
grep -c "encrypt\|decrypt" app/infrastructure/repositories/credential_repository.py  # 13

# Verify in-memory storage removed
grep "credentials_db\|Fernet.generate_key" app/routers/credential_router.py  # No output

# Run tests
python3 -m pytest tests/infrastructure/test_credential_repository.py -v  # 6 passed
```

## Migration Impact

### Before (Plan 06-02)
- Credentials stored in `credentials_db = {}`
- Lost on service restart
- Encryption key regenerated each startup (unreadable persisted data)

### After (Plan 06-03)
- Credentials stored in database via SQLAlchemy repository
- Persist across service restarts
- Centralized encryption key from environment (stable decryption)

### Breaking Changes
- None (API endpoints unchanged)

### Behavioral Changes
- Credentials now survive restarts
- Access tracking persists
- Rotation history maintained

## Next Phase Readiness

### For Plan 06-04 (OAuth Token Encryption)
✅ Repository pattern established
✅ Encryption service available
✅ Database session management working

### For Plan 06-05 (API Key Bcrypt Hashing)
✅ Credential storage pattern proven
✅ Can extend for hashed API keys

### For Plan 06-06 (Security Integration Tests)
✅ Repository testable with mocks
✅ End-to-end flow ready for integration testing

## Deviations from Plan

None - plan executed exactly as written.

## Performance Considerations

- **Database calls:** Every credential operation now hits database (acceptable for security ops)
- **Encryption overhead:** Negligible (Fernet is fast, credentials accessed infrequently)
- **Session lifecycle:** One session per request via dependency injection (standard FastAPI pattern)

## Security Improvements

✅ Credentials persist encrypted in database
✅ Encryption key from environment (not runtime generated)
✅ Access tracking for audit trail
✅ Soft delete preserves credential history
✅ No plaintext credentials in memory (only during active request)

## Lessons Learned

1. **Dependency injection scales well** - Adding repository to all endpoints was mechanical but correct
2. **Async session management straightforward** - FastAPI's Depends() handles lifecycle automatically
3. **Repository pattern flexible** - Same pattern will work for OAuth tokens (Plan 06-04)
4. **Audit logs deferred correctly** - Focusing on credentials first reduced complexity

## Future Work

- Migrate audit logs to database (separate plan, likely Phase 7)
- Add credential usage analytics (track which services accessed when)
- Implement credential expiration warnings (background task)
- Add credential rotation automation (scheduled job)

---

**Commits:**
- 867d0fd: feat(06-03): create CredentialRepository for persistent storage
- 31a2c76: feat(06-03): migrate credential_router to use CredentialRepository
- dc1446e: test(06-03): add credential repository tests

**Duration:** ~7 minutes (repository + refactor + tests)
**Lines Changed:** +330 created, ~185 refactored
**Tests Added:** 6 passing
