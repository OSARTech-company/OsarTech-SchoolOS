"""Add bursar accounts table and archive columns.

Revision ID: 011_bursar_accounts
Revises: 010_student_fee_management
Create Date: 2026-06-21 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '011_bursar_accounts'
down_revision = '010_student_fee_management'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS bursars (
               id SERIAL PRIMARY KEY,
               school_id TEXT NOT NULL,
               user_id TEXT NOT NULL,
               firstname TEXT NOT NULL,
               lastname TEXT NOT NULL,
               phone TEXT,
               gender TEXT,
               profile_image TEXT,
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_bursars_school_user ON bursars(school_id, user_id)")
    op.execute("ALTER TABLE bursars ADD COLUMN IF NOT EXISTS phone TEXT")
    op.execute("ALTER TABLE bursars ADD COLUMN IF NOT EXISTS gender TEXT")
    op.execute("ALTER TABLE bursars ADD COLUMN IF NOT EXISTS profile_image TEXT")
    op.execute("ALTER TABLE bursars ADD COLUMN IF NOT EXISTS is_archived INTEGER DEFAULT 0")
    op.execute("ALTER TABLE bursars ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bursars_school_archived ON bursars(school_id, is_archived)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_bursars_school_archived")
    op.execute("DROP INDEX IF EXISTS idx_bursars_school_user")
    op.execute("DROP TABLE IF EXISTS bursars")
