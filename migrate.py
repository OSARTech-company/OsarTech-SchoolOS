"""
Run one-off database migrations/bootstrap without starting the web server.

Usage:
  python migrate.py

This script uses Alembic directly to apply schema migrations.
"""

import os
import sys


def _load_local_env_file():
    """Best-effort .env loader for local migrations without python-dotenv."""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, 'r', encoding='utf-8') as fh:
            for raw in fh:
                line = (raw or '').strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = (key or '').strip()
                if not key:
                    continue
                value = (value or '').strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
    except Exception:
        # Keep migration runner resilient; missing/malformed .env can still be
        # handled by explicit environment variables.
        return


def main():
    _load_local_env_file()
    # Keep app startup hooks disabled
    os.environ['RUN_STARTUP_DDL'] = '0'
    os.environ['RUN_STARTUP_BOOTSTRAP'] = '0'
    os.environ.setdefault('DB_GUARDS_STRICT', '0')
    os.environ.setdefault('ALLOW_RUNTIME_SCHEMA_HEAL', '0')
    os.environ.setdefault('RESET_STUDENT_PASSWORDS_ON_STARTUP', '0')

    # Use Alembic directly (doesn't require Flask app context)
    from alembic.config import Config
    from alembic import command

    try:
        print("Applying database migrations...")
        database_url = (os.environ.get('DATABASE_URL', '') or '').strip()
        if not database_url:
            raise RuntimeError("DATABASE_URL is required before running migrations.")

        # Get the migrations directory
        migrations_dir = os.path.join(os.path.dirname(__file__), 'migrations')

        # Create Alembic config
        alembic_cfg = Config(os.path.join(migrations_dir, 'alembic.ini'))
        alembic_cfg.set_main_option('script_location', migrations_dir)
        alembic_cfg.set_main_option('sqlalchemy.url', database_url)

        # Apply all pending migrations
        command.upgrade(alembic_cfg, 'head')
        print("[OK] Migrations completed successfully.")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
