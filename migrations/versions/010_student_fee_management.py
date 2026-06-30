"""Add student fee management tables.

Revision ID: 010_student_fee_management
Revises: 009_school_type_and_onboarding
Create Date: 2026-06-21 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '010_student_fee_management'
down_revision = '009_school_type_and_onboarding'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS student_fee_accounts (
               id SERIAL PRIMARY KEY,
               school_id TEXT NOT NULL,
               student_id TEXT NOT NULL,
               student_name TEXT DEFAULT '',
               classname TEXT DEFAULT '',
               stream TEXT DEFAULT '',
               term TEXT DEFAULT '',
               academic_year TEXT DEFAULT '',
               fee_label TEXT DEFAULT 'School Fee',
               currency TEXT DEFAULT 'NGN',
               amount_due REAL NOT NULL DEFAULT 0,
               amount_paid REAL NOT NULL DEFAULT 0,
               balance_amount REAL NOT NULL DEFAULT 0,
               status TEXT NOT NULL DEFAULT 'pending',
               due_date TEXT DEFAULT '',
               note TEXT DEFAULT '',
               assessed_by TEXT DEFAULT '',
               assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
               updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_student_fee_accounts_unique ON student_fee_accounts(school_id, student_id, academic_year, term, fee_label)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_student_fee_accounts_school_class_term ON student_fee_accounts(school_id, classname, term, academic_year, updated_at DESC)")
    op.execute(
        """CREATE TABLE IF NOT EXISTS student_fee_payments (
               id SERIAL PRIMARY KEY,
               account_id INTEGER NOT NULL,
               school_id TEXT NOT NULL,
               student_id TEXT NOT NULL,
               term TEXT DEFAULT '',
               academic_year TEXT DEFAULT '',
               fee_label TEXT DEFAULT '',
               amount_paid REAL NOT NULL DEFAULT 0,
               payment_method TEXT DEFAULT '',
               payment_reference TEXT DEFAULT '',
               note TEXT DEFAULT '',
               recorded_by TEXT DEFAULT '',
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )"""
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_student_fee_payments_account_created ON student_fee_payments(account_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_student_fee_payments_school_created ON student_fee_payments(school_id, created_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS student_fee_payments")
    op.execute("DROP TABLE IF EXISTS student_fee_accounts")
