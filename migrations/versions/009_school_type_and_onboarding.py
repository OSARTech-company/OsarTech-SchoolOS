"""Add school_type to schools and onboarding requests.

Revision ID: 009_school_type_and_onboarding
Revises: 008_class_timetables_online_url
Create Date: 2026-06-21 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '009_school_type_and_onboarding'
down_revision = '008_class_timetables_online_url'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE schools ADD COLUMN IF NOT EXISTS school_type TEXT DEFAULT 'mixed'")
    op.execute("ALTER TABLE school_onboarding_requests ADD COLUMN IF NOT EXISTS school_type TEXT DEFAULT 'mixed'")
    op.execute("UPDATE schools SET school_type = COALESCE(NULLIF(TRIM(COALESCE(school_type, '')), ''), 'mixed')")
    op.execute("UPDATE school_onboarding_requests SET school_type = COALESCE(NULLIF(TRIM(COALESCE(school_type, '')), ''), 'mixed')")


def downgrade() -> None:
    # Keep downgrade conservative for production data.
    op.execute("ALTER TABLE school_onboarding_requests DROP COLUMN IF EXISTS school_type")
    op.execute("ALTER TABLE schools DROP COLUMN IF EXISTS school_type")
