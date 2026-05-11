"""
Detect and fix case-insensitive username duplicates in users table.

Usage:
  python tools/fix_username_duplicates.py            # audit only
  python tools/fix_username_duplicates.py --apply    # apply safe renames

Notes:
- Keeps the earliest row (lowest id) unchanged.
- Renames later duplicates to: <username>__dup<id>
- Updates dependent tables where usernames are referenced as IDs:
  - students.student_id (role=student)
  - teachers.user_id (role=teacher)
  - class_assignments.teacher_id (role=teacher)
  - teacher_subject_assignments.teacher_id (role=teacher)
"""

import argparse
import os
import sys

import psycopg2
import psycopg2.extras
try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def _connect():
    if load_dotenv:
        load_dotenv()
    db_url = (os.environ.get("DATABASE_URL", "") or "").strip()
    if not db_url:
        raise RuntimeError("DATABASE_URL is required. Set it in env vars or .env before running this script.")
    return psycopg2.connect(db_url)


def _load_duplicates(cur):
    cur.execute(
        """
        SELECT LOWER(username) AS uname_lower, COUNT(*) AS cnt
        FROM users
        GROUP BY LOWER(username)
        HAVING COUNT(*) > 1
        ORDER BY uname_lower
        """
    )
    groups = [r[0] for r in (cur.fetchall() or [])]
    out = []
    for uname_lower in groups:
        cur.execute(
            """
            SELECT id, username, role, COALESCE(school_id, '') AS school_id, created_at
            FROM users
            WHERE LOWER(username) = %s
            ORDER BY id ASC
            """,
            (uname_lower,),
        )
        rows = cur.fetchall() or []
        out.append((uname_lower, rows))
    return out


def _build_fix_plan(dupes):
    plan = []
    for uname_lower, rows in dupes:
        keeper = rows[0]
        for row in rows[1:]:
            rid, username, role, school_id, _created = row
            new_username = f"{username}__dup{rid}"
            plan.append(
                {
                    "id": rid,
                    "old_username": username,
                    "new_username": new_username,
                    "role": (role or "").strip().lower(),
                    "school_id": (school_id or "").strip(),
                    "group": uname_lower,
                    "keeper_id": keeper[0],
                    "keeper_username": keeper[1],
                }
            )
    return plan


def _apply_plan(cur, plan):
    for item in plan:
        old_u = item["old_username"]
        new_u = item["new_username"]
        role = item["role"]

        cur.execute("UPDATE users SET username = %s WHERE id = %s", (new_u, item["id"]))

        if role == "student":
            cur.execute(
                "UPDATE students SET student_id = %s WHERE LOWER(student_id) = LOWER(%s)",
                (new_u, old_u),
            )
        elif role == "teacher":
            cur.execute(
                "UPDATE teachers SET user_id = %s WHERE LOWER(user_id) = LOWER(%s)",
                (new_u, old_u),
            )
            cur.execute(
                "UPDATE class_assignments SET teacher_id = %s WHERE LOWER(teacher_id) = LOWER(%s)",
                (new_u, old_u),
            )
            cur.execute(
                "UPDATE teacher_subject_assignments SET teacher_id = %s WHERE LOWER(teacher_id) = LOWER(%s)",
                (new_u, old_u),
            )


def _ensure_unique_lower_index(cur):
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_users_username_lower ON users(LOWER(username))")


def main():
    parser = argparse.ArgumentParser(description="Fix case-insensitive duplicate usernames.")
    parser.add_argument("--apply", action="store_true", help="Apply renames and create unique lower(username) index.")
    args = parser.parse_args()

    with _connect() as conn:
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        dupes = _load_duplicates(cur)
        if not dupes:
            print("[OK] No case-insensitive duplicate usernames found.")
            if args.apply:
                _ensure_unique_lower_index(cur)
                conn.commit()
                print("[OK] Enforced unique lower(username) index.")
            return 0

        plan = _build_fix_plan(dupes)
        print(f"[WARN] Found {len(dupes)} duplicate username groups.")
        for group, rows in dupes:
            print(f"  - {group}: {len(rows)} rows")
        print(f"[INFO] Planned renames: {len(plan)}")
        for item in plan[:20]:
            print(
                f"    id={item['id']} {item['old_username']} -> {item['new_username']} "
                f"(role={item['role']}, school_id={item['school_id']})"
            )
        if len(plan) > 20:
            print(f"    ... and {len(plan) - 20} more")

        if not args.apply:
            print("[INFO] Dry run only. Re-run with --apply to execute.")
            conn.rollback()
            return 0

        _apply_plan(cur, plan)
        _ensure_unique_lower_index(cur)
        conn.commit()
        print("[OK] Duplicate usernames fixed and unique lower(username) index enforced.")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise
