---
phase: 11-integration-wiring
plan: 03
subsystem: api
tags: [fastapi, hexagonal-architecture, encryption, credential-security, fernet]

# Dependency graph
requires:
  - phase: 11-01
    provides: DI Container initialized in main.py
  - phase: 06-security-hardening
    provides: CredentialRepository with Fernet encryption
  - phase: 05-infrastructure-adapters
    provides: Account use cases and repository interfaces

provides:
  - Accounts router wired to hexagonal architecture
  - Account CRUD operations with encrypted credential storage
  - CreateAccountUseCase, UpdateAccountUseCase, DeleteAccountUseCase
  - Credential encryption via CredentialRepository on all account operations

affects: [account-management, broker-integration, credential-security]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Account credentials encrypted via CredentialRepository.encrypt_dict()
    - Use case-based account operations replace direct SQL
    - Credential rotation on account updates
    - Soft-delete for credentials on account deletion

key-files:
  created:
    - app/application/dto/account_dto.py (new DTOs: Create/Update/Delete)
  modified:
    - app/routers/accounts.py (complete hexagonal wiring)
    - app/application/use_cases/manage_accounts.py (added CRUD use cases)
    - app/infrastructure/container.py (credential repository integration)
    - app/application/use_cases/__init__.py (export new use cases)

key-decisions:
  - "Credentials stored in separate credentials table with Fernet encryption"
  - "Account create/update use CredentialRepository for automatic encryption"
  - "Soft-delete credentials on account deletion (preserve audit trail)"
  - "Credential rotation re-encrypts data on account update"

patterns-established:
  - "Account credentials never stored in account table - separate encrypted storage"
  - "All CRUD operations flow through use cases from container"
  - "API router acts as thin adapter layer converting requests to DTOs"

# Metrics
duration: 9min
completed: 2026-01-21
---

# Phase 11 Plan 03: Wire Accounts Router to Hexagonal Architecture Summary

**Account CRUD with Fernet-encrypted credentials via CredentialRepository, closing SEC-02 audit gap**

## Performance

- **Duration:** 9 min
- **Started:** 2026-01-21T00:19:29Z
- **Completed:** 2026-01-21T00:28:42Z
- **Tasks:** 2 (use cases + router wiring)
- **Files modified:** 5

## Accomplishments
- All account CRUD operations use hexagonal architecture (use cases from container)
- Credentials encrypted via CredentialRepository.encrypt_dict() on storage
- Account router no longer uses direct SQL queries
- SEC-02 audit gap closed: credentials now properly encrypted in database

## Task Commits

Each task was committed atomically:

1. **Task 1: Add account CRUD use cases** - `73f8fe5` (feat)
   - CreateAccountUseCase, UpdateAccountUseCase, DeleteAccountUseCase
   - DTOs for Create/Update/Delete operations
   - Container integration with CredentialRepository

2. **Task 2: Wire accounts router** - `e858b9a` (feat)
   - All endpoints use container use cases
   - Credentials flow through encryption service
   - Removed direct SQLAlchemy queries

## Files Created/Modified

- `app/application/dto/account_dto.py` - Added CreateAccountRequest/Response, UpdateAccountRequest/Response, DeleteAccountRequest/Response DTOs
- `app/application/use_cases/manage_accounts.py` - Added CreateAccountUseCase, UpdateAccountUseCase, DeleteAccountUseCase with credential encryption
- `app/infrastructure/container.py` - Added CredentialRepository to _get_repositories(), factory methods for new use cases
- `app/application/use_cases/__init__.py` - Exported new account use cases
- `app/routers/accounts.py` - Replaced all direct SQL with use cases, credentials encrypted on create/update

## Decisions Made

1. **Credentials in separate table**: Account credentials stored in `credentials` table with Fernet encryption, not in `accounts` table
2. **Soft-delete for credentials**: Delete operations soft-delete credentials (set is_active=False) to preserve audit trail
3. **Credential rotation on update**: UpdateAccountUseCase re-encrypts credentials via CredentialRepository.rotate()
4. **Router as thin adapter**: Accounts router converts HTTP requests to DTOs, delegates to use cases

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added Create/Update/Delete use cases**
- **Found during:** Task 1 (reviewing existing use cases)
- **Issue:** Plan assumed these use cases existed, but only Get/Connect/Sync use cases were implemented
- **Fix:** Created CreateAccountUseCase, UpdateAccountUseCase, DeleteAccountUseCase with credential encryption
- **Files modified:** app/application/use_cases/manage_accounts.py, app/application/dto/account_dto.py
- **Verification:** Use cases compile, export from application layer
- **Committed in:** 73f8fe5 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (missing critical use cases)
**Impact on plan:** Essential for credential encryption - cannot wire router without CRUD use cases. No scope creep.

## Issues Encountered

None - plan executed successfully after adding missing use cases.

## User Setup Required

None - no external service configuration required.

## Security Flow

Account creation now follows proper encryption flow:
1. Router receives credentials in request
2. CreateAccountUseCase orchestrates creation
3. CredentialRepository.create() encrypts via EncryptionService.encrypt_dict()
4. Fernet-encrypted blob stored in credentials.encrypted_data
5. Account entity stored without credentials in accounts table

## Next Phase Readiness

- Account management fully integrated with hexagonal architecture
- Credentials encrypted at rest (SEC-02 requirement met)
- Ready for broker integrations to use encrypted credentials
- All Phase 11 plans complete (webhook router 11-02, accounts router 11-03)

## Verification

To verify encryption works:

```sql
-- Check encrypted credentials in database
SELECT id, user_id, service,
       encrypted_data IS NOT NULL AS is_encrypted,
       LENGTH(encrypted_data) AS encrypted_length
FROM credentials
WHERE service IN ('tradelocker', 'topstep', 'tradovate', 'mt4', 'mt5');

-- Should show encrypted_data with ~150+ chars (Fernet output)
```

---
*Phase: 11-integration-wiring*
*Completed: 2026-01-21*
