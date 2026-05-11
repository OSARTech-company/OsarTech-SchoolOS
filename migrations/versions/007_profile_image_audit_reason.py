"""Add teacher profile image and score audit change reason.

Revision ID: 007_profile_image_audit_reason
Revises: 006_parent_session_idx_hardening
Create Date: 2026-03-10 00:20:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '007_profile_image_audit_reason'
down_revision = '006_parent_session_idx_hardening'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE teachers ADD COLUMN IF NOT EXISTS profile_image TEXT")
    op.execute("ALTER TABLE score_audit_logs ADD COLUMN IF NOT EXISTS change_reason TEXT DEFAULT ''")


def downgrade() -> None:
    # Keep downgrade conservative on production data.
    op.execute("ALTER TABLE score_audit_logs DROP COLUMN IF EXISTS change_reason")
    op.execute("ALTER TABLE teachers DROP COLUMN IF EXISTS profile_image")
