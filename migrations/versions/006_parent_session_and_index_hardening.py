"""Parent session support and index hardening.

Revision ID: 006_parent_session_idx_hardening
Revises: 005_access_security_hardening
Create Date: 2026-03-09 00:30:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '006_parent_session_idx_hardening'
down_revision = '005_access_security_hardening'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS parent_phone TEXT")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_school_role ON users(school_id, role)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_students_parent_phone_lower ON students(LOWER(parent_phone))")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reports_status_timestamp ON reports(status, timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reports_user_timestamp ON reports(user_id, timestamp)")

    # Normalize leadership_title values for consistency.
    op.execute(
        """UPDATE schools
           SET leadership_title = 'principal'
           WHERE COALESCE(TRIM(LOWER(leadership_title)), '') NOT IN ('principal', 'head_teacher')"""
    )

    op.execute(
        """CREATE TABLE IF NOT EXISTS app_meta (
               key TEXT PRIMARY KEY,
               value TEXT NOT NULL,
               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    op.execute(
        """INSERT INTO app_meta (key, value, updated_at)
           VALUES ('schema_version', '2026-03-09.2', CURRENT_TIMESTAMP)
           ON CONFLICT(key) DO UPDATE
             SET value = EXCLUDED.value,
                 updated_at = CURRENT_TIMESTAMP"""
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_reports_user_timestamp")
    op.execute("DROP INDEX IF EXISTS idx_reports_status_timestamp")
    op.execute("DROP INDEX IF EXISTS idx_students_parent_phone_lower")
    op.execute("DROP INDEX IF EXISTS idx_users_school_role")
