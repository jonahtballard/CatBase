#!/usr/bin/env python3
"""
Add RMP columns to instructors if they don't exist.
Run:
  python backend/scripts/migrate_add_rmp_columns.py
"""
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "university_courses.db"

COLUMNS = {
    "rmp_id": "INTEGER",
    "rmp_url": "TEXT",
    "rmp_avg_rating": "REAL",
    "rmp_num_ratings": "INTEGER",
    "rmp_would_take_again": "REAL",
    "rmp_difficulty": "REAL",
    "rmp_top_tags_json": "TEXT",
    "rmp_rating_distribution_json": "TEXT",
    "rmp_last_refreshed": "TEXT"  # ISO datetime string
}

def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def main():
    conn = sqlite3.connect(DB_PATH)
    try:
        for col, typ in COLUMNS.items():
            if not column_exists(conn, "instructors", col):
                print(f"Adding column {col} {typ} …")
                conn.execute(f"ALTER TABLE instructors ADD COLUMN {col} {typ}")
        conn.commit()
        print("Migration complete.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
