# Production Checklist (Windows/PowerShell)

This runbook is for deploying `student_scor.py` safely in production.

## 1. Set Required Environment Variables

Set these in your server environment (not hardcoded in source).

```powershell
setx SECRET_KEY "replace-with-very-long-random-secret"
setx BACKUP_SIGNING_KEY "replace-with-very-long-random-secret"
setx DEFAULT_STUDENT_PASSWORD "replace-with-strong-bootstrap-password"
setx DEFAULT_TEACHER_PASSWORD "replace-with-strong-bootstrap-password"
setx ENFORCE_PRODUCTION_ENV "1"
setx ALLOW_INSECURE_DEFAULTS "0"
setx FLASK_DEBUG "0"
setx PORT "5000"
```

Database (choose one strategy used by your app):

```powershell
setx DATABASE_URL "postgresql://user:password@host:5432/dbname"
```

Open a new terminal after `setx` so values are available.

## 2. Install Dependencies

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Run Schema + Health Preflight

```powershell
python -m py_compile student_scor.py
python migrate.py
python student_scor.py --db-health-check --apply-fixes --include-startup-ddl
```

All checks should pass before go-live.

## 3b. Run Role Smoke Test

Set at least one role credential pair, then run smoke tests:

```powershell
setx SMOKE_SUPER_ADMIN_USERNAME "osartech3@gmail.com"
setx SMOKE_SUPER_ADMIN_PASSWORD "replace-with-real-password"
setx SMOKE_SCHOOL_ADMIN_USERNAME "admin@school.com"
setx SMOKE_SCHOOL_ADMIN_PASSWORD "replace-with-real-password"
setx SMOKE_TEACHER_USERNAME "teacher@school.com"
setx SMOKE_TEACHER_PASSWORD "replace-with-real-password"
setx SMOKE_STUDENT_USERNAME "26/1/001/21"
setx SMOKE_STUDENT_PASSWORD "replace-with-real-password"
setx SMOKE_PARENT_PHONE "08000000000"
setx SMOKE_PARENT_PASSWORD "replace-with-real-password"
```

Then run:

```powershell
python tools/role_smoke_test.py
```

## 3c. Fix Case-Insensitive Username Duplicates (One-Time)

Audit first:

```powershell
python tools/fix_username_duplicates.py
```

Apply fixes:

```powershell
python tools/fix_username_duplicates.py --apply
```

This also enforces `UNIQUE LOWER(username)` after cleanup.

## 4. Verify Backup/Restore Safety

1. In School Admin, download a JSON backup.
2. Confirm backup file contains:
   - `backup_version`
   - `manifest`
   - `integrity` (checksum and signed=true when `BACKUP_SIGNING_KEY` is set)
3. Test restore in a staging database first.

If backup is signed, restore requires the same `BACKUP_SIGNING_KEY`.

## 5. Start Production Server

Use Gunicorn (already in `requirements.txt`):

```powershell
gunicorn -w 3 -b 0.0.0.0:5000 student_scor:app
```

Put it behind a reverse proxy (Nginx/Caddy/IIS) with HTTPS.

## 6. Security Baseline

- Keep `FLASK_DEBUG=0`
- Use strong unique passwords for all admin accounts
- Restrict database network access to app host only
- Rotate secrets periodically (`SECRET_KEY`, `BACKUP_SIGNING_KEY`)
- Store backups off-server and encrypted at rest

## 7. Operations

- Run backups on a schedule (daily recommended)
- Test restore monthly
- Monitor logs (`app.log`) and system metrics
- Re-run preflight after each release

### Scheduled PostgreSQL Backups (Windows Task Scheduler)

Run once manually first:

```powershell
powershell -ExecutionPolicy Bypass -File tools\run_pg_backup.ps1 -BackupDir .\backups\postgres -RetentionDays 30
```

Create daily 2:00 AM task:

```powershell
schtasks /Create /SC DAILY /ST 02:00 /TN "SchoolResult-PostgresBackup" /TR "powershell -ExecutionPolicy Bypass -File C:\Aka\School_Result\tools\run_pg_backup.ps1 -BackupDir C:\Aka\School_Result\backups\postgres -RetentionDays 30" /F
```

Verify:

```powershell
schtasks /Query /TN "SchoolResult-PostgresBackup" /V /FO LIST
```
