import os

import psycopg2
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash


def main():
    load_dotenv()
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    username = (os.getenv("RESET_USERNAME") or "").strip()
    raw_password = os.getenv("RESET_PASSWORD") or ""

    if not database_url:
        raise RuntimeError("DATABASE_URL not found. Set it in .env")
    if not username:
        raise RuntimeError("RESET_USERNAME is required.")
    if not raw_password:
        raise RuntimeError("RESET_PASSWORD is required.")

    password_hash = generate_password_hash(raw_password)

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as c:
            c.execute(
                "UPDATE users SET password_hash = %s WHERE LOWER(username) = LOWER(%s)",
                (password_hash, username),
            )
            updated = int(c.rowcount or 0)
        conn.commit()

    if updated:
        print(f"Password reset successfully for {username}.")
    else:
        print(f"No user found for {username}.")


if __name__ == "__main__":
    main()

