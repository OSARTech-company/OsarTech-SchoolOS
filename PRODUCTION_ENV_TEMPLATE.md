# Production Env Template

Use this as a template in your hosting panel or `.env` for production.

```env
# Core security
SECRET_KEY=replace_with_a_long_random_secret
BACKUP_SIGNING_KEY=replace_with_a_long_random_secret
ALLOW_INSECURE_DEFAULTS=0
FLASK_DEBUG=0

# App defaults (bootstrap only, must be strong in production)
DEFAULT_STUDENT_PASSWORD=replace_with_strong_bootstrap_password
DEFAULT_TEACHER_PASSWORD=replace_with_strong_bootstrap_password

# Database
DATABASE_URL=postgresql://db_user:db_password@db_host:5432/db_name

# Runtime
PORT=5000

# Optional hardening
ADMIN_PASSWORD_MAX_AGE_DAYS=90
SESSION_TIMEOUT_MINUTES=120

# Optional email notifications
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=

# Optional SMS notifications
SMS_WEBHOOK_URL=
```

## Notes

- Keep `SECRET_KEY` and `BACKUP_SIGNING_KEY` private and long.
- Use different values per environment (dev/staging/prod).
- After changing env values, restart the app.
- If `BACKUP_SIGNING_KEY` changes, old signed backups will fail signature verification.

