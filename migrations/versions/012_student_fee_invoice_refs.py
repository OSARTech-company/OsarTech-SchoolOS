"""Add student fee invoice references and webhook dedup indexes.

Revision ID: 012_student_fee_invoice_refs
Revises: 011_bursar_accounts
Create Date: 2026-06-21 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '012_student_fee_invoice_refs'
down_revision = '011_bursar_accounts'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE student_fee_accounts ADD COLUMN IF NOT EXISTS invoice_ref TEXT DEFAULT ''")
    op.execute("CREATE INDEX IF NOT EXISTS idx_student_fee_accounts_invoice_ref ON student_fee_accounts(school_id, invoice_ref)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_student_fee_payments_school_reference ON student_fee_payments(school_id, payment_reference)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_student_fee_payments_school_reference")
    op.execute("DROP INDEX IF EXISTS idx_student_fee_accounts_invoice_ref")
