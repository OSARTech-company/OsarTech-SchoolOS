"""Add teacher gender and phone fields.

Revision ID: 003_teacher_gender_phone
Revises: 002_score_audit_logs
Create Date: 2026-02-27 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '003_teacher_gender_phone'
down_revision = '002_score_audit_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS phone TEXT")
    op.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS gender TEXT")
    op.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS subjects_taught TEXT")


def downgrade() -> None:
    # Keep downgrade safe on shared/legacy DBs by dropping only additive columns.
    op.execute("ALTER TABLE teachers DROP COLUMN IF EXISTS phone")
    op.execute("ALTER TABLE teachers DROP COLUMN IF EXISTS gender")
