"""Add score audit log table.

Revision ID: 002_score_audit_logs
Revises: 001_initial
Create Date: 2026-02-27 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '002_score_audit_logs'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        '''CREATE TABLE IF NOT EXISTS score_audit_logs (
               id SERIAL PRIMARY KEY,
               school_id TEXT NOT NULL,
               student_id TEXT NOT NULL,
               classname TEXT NOT NULL,
               term TEXT NOT NULL,
               academic_year TEXT DEFAULT '',
               subject TEXT NOT NULL,
               old_score_json TEXT,
               new_score_json TEXT,
               changed_fields_json TEXT,
               changed_by TEXT NOT NULL,
               changed_by_role TEXT NOT NULL,
               change_source TEXT NOT NULL,
               changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )'''
    )
    op.execute("ALTER TABLE score_audit_logs ADD COLUMN IF NOT EXISTS academic_year TEXT DEFAULT ''")
    op.execute("ALTER TABLE score_audit_logs ADD COLUMN IF NOT EXISTS changed_by_role TEXT DEFAULT 'teacher'")
    op.execute("ALTER TABLE score_audit_logs ADD COLUMN IF NOT EXISTS change_source TEXT DEFAULT 'manual_entry'")
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_score_audit_school_student_changed ON score_audit_logs(school_id, student_id, changed_at)'
    )
    op.execute(
        'CREATE INDEX IF NOT EXISTS idx_score_audit_school_class_term_year ON score_audit_logs(school_id, classname, term, academic_year)'
    )


def downgrade() -> None:
    op.execute('DROP TABLE IF EXISTS score_audit_logs CASCADE')
