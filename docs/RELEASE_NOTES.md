# Release Notes

**TradeFlow Unified Engine**

## Version History

### v1.2.1 - Secure Per-Broker Webhooks + Theme Isolation (January 22, 2026)
**Commit:** `5d100641b8fb7f051d2b26a19da832bc96133617`

**Features:**
- Per-broker secure webhook keys (each broker connection has unique key)
- Secure webhook endpoint `/api/v1/webhooks/incoming` with broker/user/key validation
- Theme isolation (dashboard-only theme, landing page always dark)
- Webhook key auto-generation on account create/connect
- Copy webhook URL button in account cards

**Database Changes:**
- Migration 019: Added `users.theme` column
- Migration 019: Added `trading_accounts.webhook_key` column (unique)

**Breaking Changes:** None

**Migration Required:** Yes - Run `alembic upgrade head`

---

### v1.2.0 - Signal Intelligence Layer (January 22, 2026)
**Commit:** `4acc73e`

**Features:**
- Signal Momentum Guard (sg-001)
- Time-Lock & Staleness Guard (sg-002)
- Visual Momentum Meter (sg-003)
- Max Exposure Guard (sg-004)
- Discard Bin & Auto-Flush (sg-005)
- 24h Signal Heat Map (sg-006)
- Hedge Toggle (sg-007)
- FlowGuard Bot (sg-008) - Client-side template generator
- Auto-documentation (sg-009)

**Database Changes:**
- Migration 018: Added `momentum_settings`, `signal_counters`, `discard_bin` tables

**Breaking Changes:** None

**Migration Required:** Yes - Run `alembic upgrade head`

---

## Upgrade Instructions

1. **Backup Database** (recommended)
2. **Apply Migrations:**
   ```bash
   export DATABASE_URL="postgresql://user:password@host:5432/dbname"
   alembic upgrade head
   ```
3. **Restart Services**
4. **Verify:** Check `/health` endpoint and test webhook endpoints

## Rollback

To rollback Patch 1.2.1:
```bash
alembic downgrade 018
```

To rollback Milestone 1.2:
```bash
alembic downgrade 017
```
