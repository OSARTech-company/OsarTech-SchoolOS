"""Repair result publication arm support when revision 015 was recorded early.

Revision ID: 016_repair_result_publication_arm
Revises: 015_result_publication_arm
Create Date: 2026-07-21 00:00:00.000000

"""
from alembic import op


revision = '016_repair_result_publication_arm'
down_revision = '015_result_publication_arm'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE result_publications "
        "ADD COLUMN IF NOT EXISTS arm TEXT DEFAULT ''"
    )
    op.execute("UPDATE result_publications SET arm = '' WHERE arm IS NULL")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_result_publications_school_class_arm "
        "ON result_publications(school_id, classname, arm, term, academic_year)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_result_publications_school_class_arm_term "
        "ON result_publications(school_id, classname, arm, term, academic_year)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_result_publications_school_class_arm_term")
    op.execute("DROP INDEX IF EXISTS uq_result_publications_school_class_arm")
