"""
Migrate app data from SQLite to PostgreSQL.

Usage (PowerShell):
  $env:DATABASE_URL="postgresql://user:pass@host:5432/dbname"
  python tools/migrate_to_postgres.py

Optional:
  python tools/migrate_to_postgres.py --sqlite-path student_score.db --dry-run
"""

import argparse
import os
import sqlite3
import sys
from typing import Iterable, Sequence

import psycopg2
from psycopg2.extras import execute_batch


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate SQLite data to PostgreSQL.")
    parser.add_argument("--sqlite-path", default="student_score.db", help="Path to SQLite source DB")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""), help="Target PostgreSQL URL")
    parser.add_argument("--dry-run", action="store_true", help="Read and count only, do not write to PostgreSQL")
    return parser.parse_args()


def ensure_target_schema(cur) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'teacher',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT DEFAULT 'teacher'")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            firstname TEXT NOT NULL,
            classname TEXT NOT NULL,
            number_of_subject INTEGER NOT NULL,
            subjects TEXT NOT NULL,
            scores TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, student_id)
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS reports (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            description TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT DEFAULT 'unread',
            read_at TEXT
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_students_user_id ON students(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_students_user_class ON students(user_id, classname)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reports_status_time ON reports(status, timestamp)")


def fetch_all(cur, query: str) -> Sequence[sqlite3.Row]:
    cur.execute(query)
    return cur.fetchall()


def print_counts(users: Sequence, students: Sequence, reports: Sequence) -> None:
    print(f"users: {len(users)}")
    print(f"students: {len(students)}")
    print(f"reports: {len(reports)}")


def migrate_users(pg_cur, users: Iterable[sqlite3.Row]) -> None:
    execute_batch(
        pg_cur,
        """
        INSERT INTO users (username, password_hash, role, created_at)
        VALUES (%s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))
        ON CONFLICT (username) DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            role = EXCLUDED.role
        """,
        [(u["username"], u["password_hash"], (u["role"] or "teacher"), u["created_at"]) for u in users],
        page_size=500,
    )


def migrate_students(pg_cur, students: Iterable[sqlite3.Row]) -> None:
    execute_batch(
        pg_cur,
        """
        INSERT INTO students (
            user_id, student_id, firstname, classname,
            number_of_subject, subjects, scores, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP))
        ON CONFLICT (user_id, student_id) DO UPDATE SET
            firstname = EXCLUDED.firstname,
            classname = EXCLUDED.classname,
            number_of_subject = EXCLUDED.number_of_subject,
            subjects = EXCLUDED.subjects,
            scores = EXCLUDED.scores
        """,
        [
            (
                s["user_id"],
                s["student_id"],
                s["firstname"],
                s["classname"],
                s["number_of_subject"],
                s["subjects"],
                s["scores"],
                s["created_at"],
            )
            for s in students
        ],
        page_size=500,
    )


def migrate_reports(pg_cur, reports: Iterable[sqlite3.Row]) -> None:
    execute_batch(
        pg_cur,
        """
        INSERT INTO reports (user_id, description, timestamp, status, read_at)
        VALUES (%s, %s, %s, %s, %s)
        """,
        [(r["user_id"], r["description"], r["timestamp"], r["status"], r["read_at"]) for r in reports],
        page_size=500,
    )


def main() -> int:
    args = parse_args()
    if not args.database_url:
        print("Error: DATABASE_URL is required (or pass --database-url).", file=sys.stderr)
        return 2

    if not os.path.exists(args.sqlite_path):
        print(f"Error: SQLite file not found: {args.sqlite_path}", file=sys.stderr)
        return 2

    sqlite_conn = sqlite3.connect(args.sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    users = fetch_all(sqlite_cur, "SELECT username, password_hash, COALESCE(role,'teacher') AS role, created_at FROM users")
    students = fetch_all(
        sqlite_cur,
        """
        SELECT user_id, student_id, firstname, classname,
               number_of_subject, subjects, scores, created_at
        FROM students
        """,
    )
    reports = fetch_all(sqlite_cur, "SELECT user_id, description, timestamp, status, read_at FROM reports")

    print_counts(users, students, reports)
    if args.dry_run:
        print("Dry run complete. No data written.")
        return 0

    pg_conn = psycopg2.connect(args.database_url)
    try:
        with pg_conn:
            with pg_conn.cursor() as pg_cur:
                ensure_target_schema(pg_cur)
                migrate_users(pg_cur, users)
                migrate_students(pg_cur, students)
                migrate_reports(pg_cur, reports)
        print("Migration complete.")
    finally:
        pg_conn.close()
        sqlite_conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
