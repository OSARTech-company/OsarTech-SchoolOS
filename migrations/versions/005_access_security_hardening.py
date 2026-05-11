"""Access control and security baseline schema hardening.

Revision ID: 005_access_security_hardening
Revises: 004_archive_and_term_edit_locks
Create Date: 2026-03-09 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '005_access_security_hardening'
down_revision = '004_archive_and_term_edit_locks'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users/session security compatibility columns.
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tutorial_seen_at TIMESTAMP")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS current_login_at TIMESTAMP")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP")
    op.execute("UPDATE users SET password_changed_at = COALESCE(password_changed_at, CURRENT_TIMESTAMP)")

    # School access/routing/security settings used by current app flows.
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS show_positions INTEGER DEFAULT 1")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS class_arm_ranking_mode TEXT DEFAULT 'separate'")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS combine_third_term_results INTEGER DEFAULT 0")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS parent_timetable_show_teacher INTEGER DEFAULT 1")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS theme_primary_color TEXT DEFAULT '#1E3C72'")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS theme_secondary_color TEXT DEFAULT '#2A5298'")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS theme_accent_color TEXT DEFAULT '#1F7A8C'")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS access_status TEXT DEFAULT 'trial_free'")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS trial_start_date TEXT")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS trial_end_date TEXT")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS subscription_plan TEXT DEFAULT ''")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS subscription_start_date TEXT")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS subscription_end_date TEXT")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS payment_due_date TEXT")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS payment_grace_days INTEGER DEFAULT 14")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS payment_reference TEXT DEFAULT ''")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS access_note TEXT DEFAULT ''")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS plan_max_students INTEGER DEFAULT 0")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS plan_max_teachers INTEGER DEFAULT 0")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS plan_storage_quota_mb INTEGER DEFAULT 0")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS plan_features_json TEXT DEFAULT '{}'")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS access_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS access_updated_by TEXT DEFAULT ''")
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS leadership_title TEXT DEFAULT 'principal'")
    op.execute(
        """UPDATE schools
           SET leadership_title = 'principal'
           WHERE COALESCE(TRIM(LOWER(leadership_title)), '') NOT IN ('principal', 'head_teacher')"""
    )

    # Reports context fields required by super-admin diagnostics.
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS reporter_role TEXT DEFAULT ''")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS reporter_school_id TEXT DEFAULT ''")
    op.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS source_page TEXT DEFAULT ''")

    # Helpful indexes for access/reports lookups.
    op.execute("CREATE INDEX IF NOT EXISTS idx_schools_access_status ON schools(access_status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reports_context ON reports(reporter_role, reporter_school_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_reports_source_page ON reports(source_page)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_school_role ON users(school_id, role)")

    # Keep app_meta schema marker aligned with runtime bootstrap version.
    op.execute(
        """CREATE TABLE IF NOT EXISTS app_meta (
               key TEXT PRIMARY KEY,
               value TEXT NOT NULL,
               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    op.execute(
        """INSERT INTO app_meta (key, value, updated_at)
           VALUES ('schema_version', '2026-03-09.1', CURRENT_TIMESTAMP)
           ON CONFLICT(key) DO UPDATE
             SET value = EXCLUDED.value,
                 updated_at = CURRENT_TIMESTAMP"""
    )


def downgrade() -> None:
    # Keep downgrade conservative and non-destructive for production data.
    op.execute("DROP INDEX IF EXISTS idx_users_school_role")
    op.execute("DROP INDEX IF EXISTS idx_reports_source_page")
    op.execute("DROP INDEX IF EXISTS idx_reports_context")
    op.execute("DROP INDEX IF EXISTS idx_schools_access_status")
