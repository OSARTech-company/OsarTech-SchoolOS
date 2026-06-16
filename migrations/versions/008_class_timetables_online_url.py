"""Add online_url to class_timetables.

Revision ID: 008_class_timetables_online_url
Revises: 007_profile_image_audit_reason
Create Date: 2026-06-16 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '008_class_timetables_online_url'
down_revision = '007_profile_image_audit_reason'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE class_timetables ADD COLUMN IF NOT EXISTS online_url TEXT DEFAULT ''")


def downgrade() -> None:
    # Keep downgrade conservative for production data.
    op.execute("ALTER TABLE class_timetables DROP COLUMN IF EXISTS online_url")
