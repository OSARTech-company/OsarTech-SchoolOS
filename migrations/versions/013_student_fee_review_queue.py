"""Add student fee review queue for unmatched payments.

Revision ID: 013_student_fee_review_queue
Revises: 012_student_fee_invoice_refs
Create Date: 2026-06-22 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '013_student_fee_review_queue'
down_revision = '012_student_fee_invoice_refs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS student_fee_review_queue (
               id SERIAL PRIMARY KEY,
               school_id TEXT NOT NULL,
               source TEXT DEFAULT '',
               student_id TEXT DEFAULT '',
               student_name TEXT DEFAULT '',
               invoice_ref TEXT DEFAULT '',
               payment_reference TEXT DEFAULT '',
               term TEXT DEFAULT '',
               academic_year TEXT DEFAULT '',
               fee_label TEXT DEFAULT 'School Fee',
               currency TEXT DEFAULT 'NGN',
               amount_paid REAL NOT NULL DEFAULT 0,
               reason TEXT DEFAULT '',
               payload_json TEXT DEFAULT '{}',
               status TEXT NOT NULL DEFAULT 'pending',
               reviewed_by TEXT DEFAULT '',
               reviewed_at TIMESTAMP,
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_student_fee_review_queue_school_status_created ON student_fee_review_queue(school_id, status, created_at DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_student_fee_review_queue_school_status_created")
    op.execute("DROP TABLE IF EXISTS student_fee_review_queue")
