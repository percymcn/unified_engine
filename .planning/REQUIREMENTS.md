# Verification Requirements (2026-01-25)

1. Alembic sanity: `alembic current` must read from the configured `DATABASE_URL` and report the active revision.
2. Alembic heads: `alembic heads` must list the script head(s) matching the repo.
3. Smoke scripts: `scripts/smoke_backend.sh`, `scripts/smoke_webhooks.sh`, `scripts/smoke_user_flow.sh`, `scripts/smoke_signal_intelligence.sh`, and `scripts/smoke_routing_multi_account.sh` must run against the running backend.
4. Test suite: `python -m pytest` (plus any reruns for failing subsets) must succeed before declaring verification complete.
5. Multi-account routing: add regression tests for `AccountRoutingService` (`tests/domain/test_account_routing_service.py`) and ensure the smoke routing script logs its run under `.gsd/reports/logs/`.

*Status: Blocked.* Verification remains blocked by the PostgreSQL connection failure. `alembic current` continues to raise `psycopg2.OperationalError` (`.gsd/reports/logs/alembic_current_final.log`), the smoke scripts cannot reach the backend because startup times out (`.gsd/reports/logs/smoke_backend_final.log`, `.gsd/reports/logs/smoke_*_final.log`), and `python -m pytest` (and the `-x -v` rerun) fail (`.gsd/reports/logs/pytest_final.log`, `.gsd/reports/logs/pytest_final_rerun.log`) with the first failure at `tests/application/test_signal_use_cases.py::TestProcessSignalUseCase::test_process_buy_signal_success` due to `invalid literal for int()` when signals target string-based account IDs. The `test_pg_connection.py` output (`.gsd/reports/logs/postgres_final_test.log`) shows the database is reachable from a standalone script, and yet the CLI/tools still can’t connect; until the environment is reconciled, smoke and pytest runs cannot pass.
