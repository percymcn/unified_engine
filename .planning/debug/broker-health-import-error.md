---
status: fixing
trigger: "broker-health-import-error: broker_health.py imports non-existent module causing 500 errors"
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T12:00:00Z
---

## Current Focus

hypothesis: Line 93 imports from non-existent path "app.infrastructure.services.encryption_service" but should import from "app.core.encryption"
test: Fix import and verify endpoint works
expecting: Broker health endpoint returns 200 instead of 500
next_action: Apply fix to broker_health.py

## Symptoms

expected: Broker health endpoint should work for all brokers including ProjectX
actual: Error when testing ProjectX connection - endpoint returns 500
errors: "No module named 'app.infrastructure.services'" - broker_health.py line 93 imports "from app.infrastructure.services.encryption_service import get_encryption_service"
reproduction: Call /api/v1/brokers/health endpoint or test ProjectX connection
started: Introduced in recent changes - broker_health.py was added as a new file

## Eliminated

(none yet)

## Evidence

- timestamp: 2026-01-24T12:00:00Z
  checked: app/core/encryption.py
  found: File exists and exports get_encryption_service() function at line 148
  implication: This is the correct module to import from

- timestamp: 2026-01-24T12:00:00Z
  checked: app/routers/broker_health.py line 93
  found: Import statement "from app.infrastructure.services.encryption_service import get_encryption_service"
  implication: This path does not exist - should be "from app.core.encryption import get_encryption_service"

- timestamp: 2026-01-24T12:00:00Z
  checked: broker_health.py line 11
  found: Already has "from app.core.encryption import decrypt" at top of file
  implication: Line 93 import is redundant since get_encryption_service is in same module as decrypt

## Resolution

root_cause: Line 93 imports get_encryption_service from non-existent path "app.infrastructure.services.encryption_service" - the correct path is "app.core.encryption"
fix: Change import from "from app.infrastructure.services.encryption_service import get_encryption_service" to "from app.core.encryption import get_encryption_service"
verification: (pending)
files_changed: []
