# Database Policy

## Canonical Database

**Production and Development**: PostgreSQL on port 5432

```
DATABASE_URL=postgresql://trading_user:trading_password@localhost:5432/trading_db
```

## SQLite Policy

**SQLite is a deprecated development artifact.**

- `.env` should NEVER contain `sqlite:` in DATABASE_URL
- `trading_db.db` files may exist locally but are ignored by git
- If SQLite files appear, they indicate ENV drift - fix `.env` immediately

## Alembic Migrations

All schema changes go through Alembic:

```bash
# Check current migration
DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db" python3 -m alembic current

# Apply migrations
DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db" python3 -m alembic upgrade head

# Create new migration (after model changes)
DATABASE_URL="postgresql://trading_user:trading_password@localhost:5432/trading_db" python3 -m alembic revision --autogenerate -m "description"
```

## Canonical Ports

| Service | Port | Notes |
|---------|------|-------|
| API     | 8765 | FastAPI backend |
| UI      | 3456 | Next.js frontend |
| Postgres| 5432 | Database |
| Redis   | 6379 | Cache/sessions |

## Quick Start

Use the canonical startup script:

```bash
./scripts/local_up_postgres.sh
```

This ensures:
- Postgres on 5432
- Backend on 8765
- UI on 3456
- Correct DATABASE_URL

## Troubleshooting

If you see "missing column" errors:
1. Check `.env` has `DATABASE_URL=postgresql://...` (not sqlite)
2. Run `alembic upgrade head`
3. Restart services

If backend starts on wrong port:
1. Check `.env` has `PORT=8765`
2. Use `./scripts/local_up_postgres.sh`
