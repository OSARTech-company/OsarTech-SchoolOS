# Dev Notes

## Run locally
```powershell
python student_scor.py
```

## Compile check (syntax only)
```powershell
python -m py_compile student_scor.py
```

## Migrations (if using Alembic)
```powershell
python migrate.py
```

## Cleanup local artifacts
```powershell
tools\\cleanup_local.ps1
```

## Logs
Runtime logs go to `logs/app.log` with rotation.

## Secrets
Never commit `.env`. Use `PRODUCTION_ENV_TEMPLATE.md` to set production vars.
