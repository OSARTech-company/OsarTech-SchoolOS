"""Add class-arm support to result publication records.

Revision ID: 015_result_publication_arm
Revises: 014_leader_quotes
Create Date: 2026-07-21 00:00:00.000000

"""
from alembic import op


revision = '015_result_publication_arm'
down_revision = '014_leader_quotes'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE result_publications ADD COLUMN IF NOT EXISTS arm TEXT DEFAULT ''")
    op.execute("UPDATE result_publications SET arm = '' WHERE arm IS NULL")

    op.execute(
        "ALTER TABLE result_publications "
        "DROP CONSTRAINT IF EXISTS result_publications_school_id_classname_term_academic_yea_key"
    )
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
    op.execute(
        "ALTER TABLE result_publications "
        "ADD CONSTRAINT result_publications_school_id_classname_term_academic_yea_key "
        "UNIQUE(school_id, classname, term, academic_year)"
    )
    op.execute("ALTER TABLE result_publications DROP COLUMN IF EXISTS arm")
