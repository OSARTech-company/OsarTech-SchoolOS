## Deployment with Flask-Migrate

As of 2026-02-26, schema is managed via **Flask-Migrate** (Alembic). Always run migrations separately from app startup.

### Migration Workflow

```bash
# 1. Run migrations (required whenever schema changes exist)
python migrate.py

# 2. Start app (no schema DDL during import)
gunicorn student_scor:app
```

### How It Works

- Migrations are in `migrations/versions/`
- Each migration is an idempotent SQL upgrade
- `python migrate.py` applies all pending migrations
- No DDL happens during app import (`RUN_STARTUP_DDL=0`)

### Recommended Setup for Render/Heroku

In your release command or pre-start phase:
```bash
python migrate.py
```

In your start command:
```bash
gunicorn student_scor:app
```

### Creating New Migrations

When schema changes are needed:
```bash
# Auto-generate migration from model changes
flask db revision --autogenerate -m "describe change"

# Review and edit migrations/versions/<new_migration>.py if needed

# Apply it
python migrate.py
```

### Best Practices

✅ **DO:**
- Run `python migrate.py` once per deployment (before app boots)
- Keep migrations version-controlled in `migrations/versions/`
- Test schema changes locally before production

❌ **DON'T:**
- Have multiple app instances trying to run migrations simultaneously
- Modify schema outside of migrations
- Try to run migrations during app request handlers

