import argparse
import os
import sqlite3
from contextlib import closing

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


TABLES = [
    "users",
    "schools",
    "students",
    "teachers",
    "class_assignments",
    "class_subject_configs",
    "assessment_configs",
    "result_publications",
    "published_student_results",
    "result_views",
    "reports",
]


def sqlite_columns(conn, table_name):
    with closing(conn.cursor()) as cur:
        cur.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cur.fetchall()]


def postgres_columns(conn, table_name):
    with closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )
        return [row[0] for row in cur.fetchall()]


def has_existing_data(conn, table_name):
    with closing(conn.cursor()) as cur:
        cur.execute(sql.SQL("SELECT 1 FROM {} LIMIT 1").format(sql.Identifier(table_name)))
        return cur.fetchone() is not None


def main():
    parser = argparse.ArgumentParser(description="Migrate local SQLite data into PostgreSQL.")
    parser.add_argument(
        "--sqlite-path",
        default=os.path.join(os.getcwd(), "student_score.db"),
        help="Path to SQLite database file (default: ./student_score.db)",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Dangerous: truncate PostgreSQL target tables before import.",
    )
    args = parser.parse_args()

    load_dotenv()
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set in environment/.env")

    sqlite_path = os.path.abspath(args.sqlite_path)
    if not os.path.exists(sqlite_path):
        raise RuntimeError(f"SQLite DB not found: {sqlite_path}")

    with closing(sqlite3.connect(sqlite_path)) as sconn, closing(psycopg2.connect(database_url)) as pconn:
        sconn.row_factory = sqlite3.Row
        pconn.autocommit = False

        if not args.truncate:
            existing = [t for t in TABLES if has_existing_data(pconn, t)]
            if existing:
                raise RuntimeError(
                    "Target PostgreSQL has existing data in: "
                    + ", ".join(existing)
                    + ". Re-run with --truncate if you intentionally want a full replace."
                )

        with closing(sconn.cursor()) as scur, closing(pconn.cursor()) as pcur:
            if args.truncate:
                pcur.execute(
                    "TRUNCATE TABLE " + ", ".join(TABLES) + " RESTART IDENTITY CASCADE;"
                )

            for table in TABLES:
                src_cols = sqlite_columns(sconn, table)
                dst_cols = set(postgres_columns(pconn, table))
                shared_cols = [c for c in src_cols if c in dst_cols]
                if not shared_cols:
                    print(f"{table}: skipped (no shared columns)")
                    continue

                col_csv = ", ".join(shared_cols)
                scur.execute(f"SELECT {col_csv} FROM {table}")
                rows = scur.fetchall()

                if rows:
                    placeholders = ", ".join(["%s"] * len(shared_cols))
                    pcur.executemany(
                        f"INSERT INTO {table} ({col_csv}) VALUES ({placeholders})",
                        [tuple(row[c] for c in shared_cols) for row in rows],
                    )
                print(f"{table}: {len(rows)} row(s)")

            # Keep serial sequences aligned when explicit id values were inserted.
            for table in TABLES:
                dst_cols = set(postgres_columns(pconn, table))
                if "id" not in dst_cols:
                    continue
                pcur.execute(
                    sql.SQL(
                        "SELECT setval(pg_get_serial_sequence(%s, 'id'), "
                        "COALESCE((SELECT MAX(id) FROM {}), 1), true)"
                    ).format(sql.Identifier(table)),
                    (table,),
                )

            pconn.commit()
            print("Migration completed successfully.")


if __name__ == "__main__":
    main()

