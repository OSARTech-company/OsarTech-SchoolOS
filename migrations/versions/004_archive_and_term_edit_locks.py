"""Add archive columns and term edit lock table.

Revision ID: 004_archive_and_term_edit_locks
Revises: 003_teacher_gender_phone
Create Date: 2026-03-05 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '004_archive_and_term_edit_locks'
down_revision = '003_teacher_gender_phone'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS is_archived INTEGER DEFAULT 0")
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP")
    op.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS is_archived INTEGER DEFAULT 0")
    op.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP")

    op.execute(
        '''CREATE TABLE IF NOT EXISTS term_edit_locks (
               id SERIAL PRIMARY KEY,
               school_id TEXT NOT NULL,
               classname TEXT NOT NULL,
               term TEXT NOT NULL,
               academic_year TEXT DEFAULT '',
               is_locked INTEGER NOT NULL DEFAULT 1,
               unlocked_until TIMESTAMP,
               unlock_reason TEXT DEFAULT '',
               unlocked_by TEXT DEFAULT '',
               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               UNIQUE(school_id, classname, term, academic_year)
           )'''
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_students_school_archived ON students(school_id, is_archived)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_teachers_school_archived ON teachers(school_id, is_archived)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_term_edit_locks_scope ON term_edit_locks(school_id, classname, term, academic_year)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_term_edit_locks_scope")
    op.execute("DROP INDEX IF EXISTS idx_teachers_school_archived")
    op.execute("DROP INDEX IF EXISTS idx_students_school_archived")
    op.execute("DROP TABLE IF EXISTS term_edit_locks CASCADE")
    op.execute("ALTER TABLE teachers DROP COLUMN IF EXISTS archived_at")
    op.execute("ALTER TABLE teachers DROP COLUMN IF EXISTS is_archived")
    op.execute("ALTER TABLE students DROP COLUMN IF EXISTS archived_at")
    op.execute("ALTER TABLE students DROP COLUMN IF EXISTS is_archived")
