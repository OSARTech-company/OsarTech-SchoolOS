"""Add leader quotes table for home page testimonials.

Revision ID: 014_leader_quotes
Revises: 013_student_fee_review_queue
Create Date: 2026-07-04 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '014_leader_quotes'
down_revision = '013_student_fee_review_queue'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """CREATE TABLE IF NOT EXISTS leader_quotes (
               id SERIAL PRIMARY KEY,
               author_name TEXT NOT NULL,
               author_title TEXT NOT NULL,
               quote_text TEXT NOT NULL,
               stars INTEGER DEFAULT 5,
               order_index INTEGER DEFAULT 0
           )"""
    )
    # Seed default testimonials
    op.execute(
        """INSERT INTO leader_quotes (author_name, author_title, quote_text, stars, order_index) VALUES 
        ('Mrs. Funmi Alao', 'Principal, Grace Academy', '"OSARtech SchoolOS has completely transformed our result processing. What used to take our teachers weeks now takes just a couple of clicks. The CBT module is a massive bonus!"', 5, 1),
        ('Mr. Emeka Okoye', 'Proprietor, Kings College', '"The parent portal has reduced our administrative phone calls by 80%. Parents can log in and view their child''s timetable and performance immediately. Highly recommended!"', 5, 2),
        ('Mr. Ibrahim Musa', 'Senior Teacher, Zenith High', '"Entering grades and taking daily attendance is incredibly fast. The UI is clean, intuitive, and works flawlessly on my tablet during class hours."', 5, 3)"""
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS leader_quotes")
