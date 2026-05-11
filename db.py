import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not found. Set it in .env")

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()
try:
    cursor.execute("SELECT COUNT(*) FROM users;")
    count = int((cursor.fetchone() or [0])[0] or 0)
    print(f"DB connection OK. users={count}")
except psycopg2.Error as exc:
    print(f"DB connection OK, but schema check failed: {exc.pgerror or str(exc)}")
    print("Run: python migrate.py (or apply missing ALTER TABLE statements).")
cursor.close()
conn.close()
