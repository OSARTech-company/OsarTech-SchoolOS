# Student Score Management System

A Flask web application for managing student records, entering scores, calculating grades, and generating reports.

## Overview

This project provides:
- Teacher account signup/login
- Student account creation from teacher workflow
- Student CRUD (add, view, edit, delete, search)
- Score entry per subject (tests + exam components)
- Automatic grade and pass/fail calculation
- Class ranking and report pages
- CSV/XLSX export for reports
- Public student result portal (`/student-portal`)

The app supports SQLite by default and PostgreSQL when `DATABASE_URL` is set.

## Tech Stack

- Python 3.10+
- Flask
- Flask-WTF (CSRF)
- Werkzeug (password hashing)
- SQLite / PostgreSQL (`psycopg2-binary`)
- openpyxl (XLSX export)
- gunicorn (production WSGI)

## Project Structure

```text
student_scor.py            Main Flask app
templates/                 Jinja2 templates
static/                    Static assets (CSS, images)
tools/                     Utility scripts
requirements.txt           Python dependencies
Procfile                   gunicorn process definition
student_score.db           SQLite database file (auto-created)
app.log                    Application log file
```

## Setup

1. Create and activate a virtual environment.

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:
```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Set environment variables.

Windows (PowerShell):
```powershell
$env:SECRET_KEY = "replace-with-a-long-random-secret"
# Optional: use PostgreSQL instead of SQLite
# $env:DATABASE_URL = "postgresql://user:password@host:5432/dbname"
# Optional: enable debug mode
# $env:FLASK_DEBUG = "1"
```

macOS/Linux:
```bash
export SECRET_KEY="replace-with-a-long-random-secret"
# Optional
# export DATABASE_URL="postgresql://user:password@host:5432/dbname"
# export FLASK_DEBUG="1"
```

4. Run the app.

```bash
python student_scor.py
```

5. Open:

- http://127.0.0.1:5000

## Environment Variables

- `SECRET_KEY`: Flask session/CSRF secret. Strongly recommended in all environments.
- `DATABASE_URL`: If set to `postgres://...` or `postgresql://...`, PostgreSQL is used.
- `PORT`: Runtime port (default `5000`).
- `FLASK_DEBUG`: Debug toggle (`1`, `true`, `yes` => enabled).

## Main Routes

Public:
- `GET /` Home
- `GET /student-portal` Student result lookup page
- `POST /check-result` Student result lookup submit
- `GET|POST /login` Login
- `GET|POST /signup` Teacher signup

Teacher (authenticated):
- `GET /menu`
- `GET|POST /add_student`
- `GET /view_students`
- `GET|POST /edit_student`
- `GET|POST /delete_student`
- `GET|POST /search_student`
- `GET|POST /enter_scores`
- `GET /student_report`
- `GET /all_students_report`
- `GET /rank_students`
- `GET /reports/export_csv`
- `GET /reports/export_xlsx`
- `GET /rank/export_csv`
- `GET|POST /report_issue`
- `GET /backup`
- `GET|POST /restore`

Student (authenticated student role):
- `GET /student_menu`
- `GET /my_report`

General authenticated:
- `GET|POST /change_password`
- `GET /logout`
- `GET /api/students`
- `GET /help`

## Database

Tables are created automatically on startup:
- `users` (`username`, `password_hash`, `role`, ...)
- `students` (`user_id`, `student_id`, `firstname`, `classname`, `subjects`, `scores`, ...)
- `reports` (issue reports and status)

Notes:
- `subjects` and `scores` are stored as JSON strings.
- Student uniqueness is enforced per owner: `(user_id, student_id)`.

## Production Run

Use gunicorn (matches `Procfile`):

```bash
gunicorn student_scor:app
```

You can also set workers explicitly:

```bash
gunicorn -w 2 -b 0.0.0.0:$PORT student_scor:app
```

## Exports and Backups

- CSV export: `/reports/export_csv`
- XLSX export: `/reports/export_xlsx` (requires `openpyxl`)
- Backup/restore endpoints currently operate on `student_score.db` (SQLite file workflow).

## Logging

Application logs are written to:
- `app.log`

## Smoke Test Utility

Use `tools/role_smoke_test.py` to verify core auth routes before release.

```powershell
python tools/role_smoke_test.py
```

It checks:
- Public routes (`/`, `/login`, `/terms-privacy`)
- Role login flow for any role credentials you provide via env vars

## Username Duplicate Fix

Audit case-insensitive username collisions:

```powershell
python tools/fix_username_duplicates.py
```

Apply safe renames and enforce unique index:

```powershell
python tools/fix_username_duplicates.py --apply
```

## PostgreSQL Backup Utility

Create a compressed PostgreSQL backup from `DATABASE_URL`:

```powershell
powershell -ExecutionPolicy Bypass -File tools\run_pg_backup.ps1 -BackupDir .\backups\postgres -RetentionDays 30
```

## Troubleshooting

- CSRF errors: ensure form templates include `csrf_token` for POST forms.
- Login issues: confirm account exists and password is correct.
- PostgreSQL issues: verify `DATABASE_URL` and `psycopg2-binary` installation.
- XLSX export errors: install/verify `openpyxl`.

## License

Use and modify as needed for your school. Add your preferred license file if you plan to distribute publicly.
