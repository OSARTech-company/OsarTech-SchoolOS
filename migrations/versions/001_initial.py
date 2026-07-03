"""Initial schema creation for school result system.

Revision ID: 001_initial
Revises: 
Create Date: 2026-02-26 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables and indexes for the school result system."""
    
    # Users table with roles: super_admin, school_admin, teacher, student
    op.execute('''CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'student',
                    school_id TEXT,
                    terms_accepted INTEGER DEFAULT 0,
                    current_login_at TIMESTAMP,
                    last_login_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')

    # Schools table
    op.execute('''CREATE TABLE IF NOT EXISTS schools (
                    id SERIAL PRIMARY KEY,
                    school_id TEXT UNIQUE NOT NULL,
                    school_name TEXT NOT NULL,
                    location TEXT,
                    school_logo TEXT,
                    academic_year TEXT,
                    current_term TEXT DEFAULT 'First Term',
                    operations_enabled INTEGER DEFAULT 1,
                    teacher_operations_enabled INTEGER DEFAULT 1,
                    test_enabled INTEGER DEFAULT 1,
                    exam_enabled INTEGER DEFAULT 1,
                    max_tests INTEGER DEFAULT 3,
                    test_score_max INTEGER DEFAULT 30,
                    exam_objective_max INTEGER DEFAULT 30,
                    exam_theory_max INTEGER DEFAULT 40,
                    grade_a_min INTEGER DEFAULT 70,
                    grade_b_min INTEGER DEFAULT 60,
                    grade_c_min INTEGER DEFAULT 50,
                    grade_d_min INTEGER DEFAULT 40,
                    pass_mark INTEGER DEFAULT 50,
                    ss_ranking_mode TEXT DEFAULT 'together',
                    ss1_stream_mode TEXT DEFAULT 'separate',
                    phone TEXT,
                    email TEXT,
                    principal_name TEXT,
                    motto TEXT,
                    principal_signature_image TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # Students table with ID format: YY/school_id/index/start_year_yy
    op.execute('''CREATE TABLE IF NOT EXISTS students (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    school_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    firstname TEXT NOT NULL,
                    classname TEXT NOT NULL,
                    first_year_class TEXT NOT NULL,
                    term TEXT NOT NULL,
                    stream TEXT NOT NULL,
                    number_of_subject INTEGER NOT NULL,
                    subjects TEXT NOT NULL,
                    scores TEXT,
                    promoted INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(school_id, student_id)
                )''')
    
    # Teachers table
    op.execute('''CREATE TABLE IF NOT EXISTS teachers (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    school_id TEXT NOT NULL,
                    firstname TEXT NOT NULL,
                    lastname TEXT NOT NULL,
                    phone TEXT,
                    gender TEXT,
                    signature_image TEXT,
                    assigned_classes TEXT,
                    subjects_taught TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # Class assignments
    op.execute('''CREATE TABLE IF NOT EXISTS class_assignments (
                    id SERIAL PRIMARY KEY,
                    school_id TEXT NOT NULL,
                    teacher_id TEXT NOT NULL,
                    classname TEXT NOT NULL,
                    term TEXT NOT NULL,
                    academic_year TEXT NOT NULL
                )''')

    # Class subject configuration (set by school admin)
    op.execute('''CREATE TABLE IF NOT EXISTS class_subject_configs (
                    id SERIAL PRIMARY KEY,
                    school_id TEXT NOT NULL,
                    classname TEXT NOT NULL,
                    core_subjects TEXT NOT NULL,
                    science_subjects TEXT,
                    art_subjects TEXT,
                    commercial_subjects TEXT,
                    optional_subjects TEXT,
                    optional_subject_limit INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(school_id, classname)
                )''')
    
    # Global subject catalog by class (shared across all schools)
    op.execute('''CREATE TABLE IF NOT EXISTS global_class_subject_catalog (
                    id SERIAL PRIMARY KEY,
                    classname TEXT NOT NULL,
                    bucket TEXT NOT NULL,
                    subject_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(classname, bucket, subject_name)
                )''')

    # Per-level assessment/exam configuration (primary, jss, ss)
    op.execute('''CREATE TABLE IF NOT EXISTS assessment_configs (
                    id SERIAL PRIMARY KEY,
                    school_id TEXT NOT NULL,
                    level TEXT NOT NULL,
                    exam_mode TEXT NOT NULL DEFAULT 'separate',
                    objective_max INTEGER NOT NULL DEFAULT 30,
                    theory_max INTEGER NOT NULL DEFAULT 40,
                    exam_score_max INTEGER NOT NULL DEFAULT 70,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(school_id, level)
                )''')
    
    # Result publication/ranking gate per class + term
    op.execute('''CREATE TABLE IF NOT EXISTS result_publications (
                    id SERIAL PRIMARY KEY,
                    school_id TEXT NOT NULL,
                    classname TEXT NOT NULL,
                    term TEXT NOT NULL,
                    academic_year TEXT DEFAULT '',
                    teacher_id TEXT NOT NULL,
                    teacher_name TEXT DEFAULT '',
                    principal_name TEXT DEFAULT '',
                    is_published INTEGER NOT NULL DEFAULT 0,
                    published_at TIMESTAMP,
                    approval_status TEXT DEFAULT 'not_submitted',
                    submitted_at TIMESTAMP,
                    submitted_by TEXT,
                    reviewed_at TIMESTAMP,
                    reviewed_by TEXT,
                    review_note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(school_id, classname, term, academic_year)
                )''')
    
    # Immutable snapshot of published student results per term
    op.execute('''CREATE TABLE IF NOT EXISTS published_student_results (
                    id SERIAL PRIMARY KEY,
                    school_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    firstname TEXT NOT NULL,
                    classname TEXT NOT NULL,
                    academic_year TEXT,
                    term TEXT NOT NULL,
                    stream TEXT NOT NULL,
                    number_of_subject INTEGER NOT NULL,
                    subjects TEXT NOT NULL,
                    scores TEXT NOT NULL,
                    teacher_comment TEXT,
                    average_marks REAL NOT NULL DEFAULT 0,
                    grade TEXT NOT NULL,
                    status TEXT NOT NULL,
                    published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(school_id, student_id, academic_year, term)
                )''')
    
    # Track when students view published results
    op.execute('''CREATE TABLE IF NOT EXISTS result_views (
                    id SERIAL PRIMARY KEY,
                    school_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    term TEXT NOT NULL,
                    academic_year TEXT DEFAULT '',
                    first_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    view_count INTEGER NOT NULL DEFAULT 1,
                    UNIQUE(school_id, student_id, term, academic_year)
                )''')
    
    # Reports table
    op.execute('''CREATE TABLE IF NOT EXISTS reports (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT DEFAULT 'unread',
                    read_at TEXT
                )''')
    
    # Login attempt tracking for brute-force protection
    op.execute('''CREATE TABLE IF NOT EXISTS login_attempts (
                    id SERIAL PRIMARY KEY,
                    endpoint TEXT NOT NULL,
                    username TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    failures INTEGER NOT NULL DEFAULT 0,
                    first_failed_at TIMESTAMP,
                    last_failed_at TIMESTAMP,
                    locked_until TIMESTAMP,
                    UNIQUE(endpoint, username, ip_address)
                )''')

    # App metadata (for schema versioning)
    op.execute('''CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')

    # Create indexes
    op.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users(LOWER(username))')
    op.execute('CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_students_school ON students(school_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_students_student_id_lower ON students(LOWER(student_id))')
    op.execute('CREATE INDEX IF NOT EXISTS idx_students_class ON students(school_id, classname)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_students_school_class_term ON students(school_id, classname, term)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_students_school_term ON students(school_id, term)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_teachers_school ON teachers(school_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_teachers_school_user ON teachers(school_id, user_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_class_subject_configs_school_class ON class_subject_configs(school_id, classname)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_global_subject_catalog_class_bucket ON global_class_subject_catalog(classname, bucket)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_assessment_configs_school_level ON assessment_configs(school_id, level)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_result_views_lookup ON result_views(school_id, term, student_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_result_views_lookup_year ON result_views(school_id, term, academic_year, student_id)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_login_attempts_lookup ON login_attempts(endpoint, username, ip_address)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_login_attempts_locked_until ON login_attempts(locked_until)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_result_publications_school_class_term_year ON result_publications(school_id, classname, term, academic_year)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_published_school_class_term_year ON published_student_results(school_id, classname, term, academic_year)')
    op.execute('CREATE INDEX IF NOT EXISTS idx_published_school_student_term_year ON published_student_results(school_id, student_id, term, academic_year)')

    # Create uniqueness constraints for conflict resolution
    op.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_students_school_student ON students(school_id, student_id)')
    op.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_teachers_school_user ON teachers(school_id, user_id)')
    op.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_class_assignments ON class_assignments(school_id, teacher_id, classname, term, academic_year)')
    op.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_class_term_assignment ON class_assignments(school_id, classname, term, academic_year)')
    op.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_result_publications ON result_publications(school_id, classname, term, academic_year)')

    # Ensure schools.school_id has a unique index for FK references on legacy DBs.
    op.execute('CREATE UNIQUE INDEX IF NOT EXISTS uq_schools_school_id ON schools(school_id)')

    # Add foreign key constraints for multi-school isolation.
    # Keep this migration resilient on existing/legacy databases: if FK creation
    # is not possible (dirty data or missing uniqueness), continue migration.
    op.execute('''
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE students
                ADD CONSTRAINT fk_students_school
                FOREIGN KEY (school_id) REFERENCES schools(school_id)
                ON DELETE CASCADE NOT VALID;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
                WHEN invalid_foreign_key THEN
                    RAISE NOTICE 'Skipping fk_students_school due to missing/invalid referenced uniqueness';
            END;
        END $$;
    ''')
    op.execute('''
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE teachers
                ADD CONSTRAINT fk_teachers_school
                FOREIGN KEY (school_id) REFERENCES schools(school_id)
                ON DELETE CASCADE NOT VALID;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
                WHEN invalid_foreign_key THEN
                    RAISE NOTICE 'Skipping fk_teachers_school due to missing/invalid referenced uniqueness';
            END;
        END $$;
    ''')
    op.execute('''
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE class_assignments
                ADD CONSTRAINT fk_class_assignments_school
                FOREIGN KEY (school_id) REFERENCES schools(school_id)
                ON DELETE CASCADE NOT VALID;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
                WHEN invalid_foreign_key THEN
                    RAISE NOTICE 'Skipping fk_class_assignments_school due to missing/invalid referenced uniqueness';
            END;
        END $$;
    ''')
    op.execute('''
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE class_assignments
                ADD CONSTRAINT fk_class_assignments_teacher
                FOREIGN KEY (school_id, teacher_id) REFERENCES teachers(school_id, user_id)
                ON DELETE CASCADE NOT VALID;
            EXCEPTION
                WHEN duplicate_object THEN NULL;
                WHEN invalid_foreign_key THEN
                    RAISE NOTICE 'Skipping fk_class_assignments_teacher due to missing/invalid referenced uniqueness';
            END;
        END $$;
    ''')


def downgrade() -> None:
    """Drop all tables (destructive)."""
    op.execute('DROP TABLE IF EXISTS login_attempts CASCADE')
    op.execute('DROP TABLE IF EXISTS reports CASCADE')
    op.execute('DROP TABLE IF EXISTS result_views CASCADE')
    op.execute('DROP TABLE IF EXISTS published_student_results CASCADE')
    op.execute('DROP TABLE IF EXISTS result_publications CASCADE')
    op.execute('DROP TABLE IF EXISTS assessment_configs CASCADE')
    op.execute('DROP TABLE IF EXISTS global_class_subject_catalog CASCADE')
    op.execute('DROP TABLE IF EXISTS class_subject_configs CASCADE')
    op.execute('DROP TABLE IF EXISTS class_assignments CASCADE')
    op.execute('DROP TABLE IF EXISTS teachers CASCADE')
    op.execute('DROP TABLE IF EXISTS students CASCADE')
    op.execute('DROP TABLE IF EXISTS users CASCADE')
    op.execute('DROP TABLE IF EXISTS schools CASCADE')
    op.execute('DROP TABLE IF EXISTS app_meta CASCADE')
