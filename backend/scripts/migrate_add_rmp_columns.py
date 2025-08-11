#!/usr/bin/env python3
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "university_courses.db"

COLUMNS = [
    ("rmp_id", "TEXT"),
    ("rmp_school_id", "TEXT"),
    ("rmp_url", "TEXT"),
    ("rmp_avg_rating", "REAL"),
    ("rmp_num_ratings", "INTEGER"),
    ("rmp_would_take_again", "REAL"),
    ("rmp_difficulty", "REAL"),
    ("rmp_last_refreshed", "TEXT"),
]

def ensure_columns(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(instructors)")
    existing = {row[1] for row in cur.fetchall()}
    for name, coltype in COLUMNS:
        if name not in existing:
            print(f"Adding column {name} {coltype} to instructors...")
            cur.execute(f"ALTER TABLE instructors ADD COLUMN {name} {coltype}")
    conn.commit()

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_columns(conn)
        print("Migration complete.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
