#!/usr/bin/env python3
"""
Ingest UVM *current* sections CSV into SQLite.

- Schema is section-centric (course → many sections/CRNs), with meetings split out.
- Safe to re-run: upserts sections by (term_id, crn) and refreshes meetings.
- Paths assume repo layout:
    data/raw/uvm_current_sections_cleaned.csv
    data/processed/university_courses.db
"""

import csv
import sqlite3
from pathlib import Path

# === Paths ===
REPO_ROOT = Path(__file__).resolve().parents[2] if len(Path(__file__).resolve().parents) >= 2 else Path(".")
RAW_CSV = REPO_ROOT / "data" / "processed" / "uvm_current_sections_cleaned.csv"
DB_PATH = REPO_ROOT / "data" / "processed" / "university_courses.db"

# === Helpers ===
def parse_credits(s):
    if not s or str(s).strip().upper() in ("", "N/A", "NA", "NONE"):
        return None, None
    s = str(s).strip()
    if "-" in s:
        a, b = [x.strip() for x in s.split("-", 1)]
        try:
            return float(a), float(b)
        except Exception:
            return None, None
    try:
        v = float(s)
        return v, v
    except Exception:
        return None, None

def to_int_or_none(v):
    try:
        return int(str(v).strip())
    except Exception:
        return None

def semester_title(s):
    s = (s or "").strip().lower()
    mapping = {"spring":"Spring","summer":"Summer","fall":"Fall","winter":"Winter"}
    return mapping.get(s, None)

def ensure_dirs():
    (REPO_ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)

# === Schema ===
def ensure_schema(conn: sqlite3.Connection):
    conn.executescript("""
    PRAGMA foreign_keys = ON;

    CREATE TABLE IF NOT EXISTS terms (
      term_id     INTEGER PRIMARY KEY,
      semester    TEXT NOT NULL CHECK (semester IN ('Spring','Summer','Fall','Winter')),
      year        INTEGER NOT NULL,
      UNIQUE (semester, year)
    );

    CREATE TABLE IF NOT EXISTS subjects (
      subject_id  INTEGER PRIMARY KEY,
      code        TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS courses (
      course_id     INTEGER PRIMARY KEY,
      subject_id    INTEGER NOT NULL REFERENCES subjects(subject_id),
      course_number TEXT NOT NULL,
      title         TEXT NOT NULL,
      UNIQUE (subject_id, course_number, title)
    );

    CREATE TABLE IF NOT EXISTS instructors (
      instructor_id INTEGER PRIMARY KEY,
      name          TEXT NOT NULL,
      netid         TEXT,
      email         TEXT,
      UNIQUE (name, netid, email)   -- no expressions in UNIQUE for SQLite
    );

    CREATE TABLE IF NOT EXISTS sections (
      section_id         INTEGER PRIMARY KEY,
      course_id          INTEGER NOT NULL REFERENCES courses(course_id) ON DELETE CASCADE,
      term_id            INTEGER NOT NULL REFERENCES terms(term_id) ON DELETE CASCADE,
      crn                TEXT NOT NULL,   -- "Comp Numb"
      lec_lab            TEXT,
      credits_min        REAL,
      credits_max        REAL,
      max_enrollment     INTEGER,
      current_enrollment INTEGER,
      UNIQUE (term_id, crn)
    );

    CREATE TABLE IF NOT EXISTS meetings (
      meeting_id   INTEGER PRIMARY KEY,
      section_id   INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
      start_time   TEXT,
      end_time     TEXT,
      days         TEXT,
      bldg         TEXT,
      room         TEXT,
      location     TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_courses_subject_number ON courses(subject_id, course_number);
    CREATE INDEX IF NOT EXISTS idx_courses_title ON courses(title);
    CREATE INDEX IF NOT EXISTS idx_sections_term_course ON sections(term_id, course_id);
    CREATE INDEX IF NOT EXISTS idx_sections_crn ON sections(crn);
    CREATE INDEX IF NOT EXISTS idx_instructors_name ON instructors(name);
    """)
    conn.commit()

def get_or_create(conn: sqlite3.Connection, select_sql: str, insert_sql: str, params):
    row = conn.execute(select_sql, params).fetchone()
    if row:
        return row[0]
    cur = conn.execute(insert_sql, params)
    return cur.lastrowid

def upsert_section(conn: sqlite3.Connection, vals: tuple):
    conn.execute("""
        INSERT INTO sections(course_id, term_id, crn, lec_lab, credits_min, credits_max,
                             max_enrollment, current_enrollment)
        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(term_id, crn) DO UPDATE SET
            course_id=excluded.course_id,
            lec_lab=excluded.lec_lab,
            credits_min=excluded.credits_min,
            credits_max=excluded.credits_max,
            max_enrollment=excluded.max_enrollment,
            current_enrollment=excluded.current_enrollment
    """, vals)

def load_current_csv(conn: sqlite3.Connection, csv_path: Path) -> tuple[int, int]:
    inserted = 0
    updated = 0

    with csv_path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            subj = (row.get("Subj") or "").strip()
            number = (row.get("Number") or "").strip()
            title = (row.get("Title") or "").strip()
            crn = (row.get("Comp Numb") or "").strip()
            lec_lab = (row.get("Lec Lab") or "").strip()
            credits_min, credits_max = parse_credits(row.get("Credits"))
            start_time = (row.get("Start Time") or "").strip() or None
            end_time = (row.get("End Time") or "").strip() or None
            days = (row.get("Days") or "").strip() or None
            bldg = (row.get("Bldg") or "").strip() or None
            room = (row.get("Room") or "").strip() or None
            location = (row.get("Location") or "").strip() or None
            instructor_name = (row.get("Instructor") or "").strip()
            netid = (row.get("NetId") or "").strip() or None
            email = (row.get("Email") or "").strip() or None
            max_enrl = to_int_or_none(row.get("Max Enrollment"))
            cur_enrl = to_int_or_none(row.get("Current Enrollment"))
            semester = semester_title(row.get("Semester"))
            year = to_int_or_none(row.get("Year"))

            # Skip incomplete essentials
            if not (subj and number and title and crn and semester and year):
                continue

            # term
            term_id = get_or_create(
                conn,
                "SELECT term_id FROM terms WHERE semester=? AND year=?",
                "INSERT INTO terms(semester, year) VALUES(?, ?)",
                (semester, year),
            )

            # subject
            subject_id = get_or_create(
                conn,
                "SELECT subject_id FROM subjects WHERE code=?",
                "INSERT INTO subjects(code) VALUES(?)",
                (subj,),
            )

            # course
            course_id = get_or_create(
                conn,
                "SELECT course_id FROM courses WHERE subject_id=? AND course_number=? AND title=?",
                "INSERT INTO courses(subject_id, course_number, title) VALUES(?, ?, ?)",
                (subject_id, number, title),
            )

            # instructor (optional)
            instructor_id = None
            if instructor_name:
                instructor_id = get_or_create(
                    conn,
                    "SELECT instructor_id FROM instructors WHERE name=? AND netid IS ? AND email IS ?",
                    "INSERT INTO instructors(name, netid, email) VALUES(?, ?, ?)",
                    (instructor_name, netid, email),
                )
                # NOTE: We are not linking instructor to section yet (can add a junction table later).

            # sections upsert
            pre = conn.execute("SELECT section_id FROM sections WHERE term_id=? AND crn=?", (term_id, crn)).fetchone()
            upsert_section(conn, (course_id, term_id, crn, lec_lab, credits_min, credits_max, max_enrl, cur_enrl))
            post = conn.execute("SELECT section_id FROM sections WHERE term_id=? AND crn=?", (term_id, crn)).fetchone()

            if pre is None and post is not None:
                inserted += 1
            else:
                updated += 1

            section_id = post[0]

            # meetings: replace for this section
            conn.execute("DELETE FROM meetings WHERE section_id=?", (section_id,))
            conn.execute("""
                INSERT INTO meetings(section_id, start_time, end_time, days, bldg, room, location)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (section_id, start_time, end_time, days, bldg, room, location))

    conn.commit()
    return inserted, updated

def main():
    ensure_dirs()
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"Could not find CSV at {RAW_CSV}. Place 'uvm_current_sections_cleaned.csv' in data/raw/")
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_schema(conn)
        ins, upd = load_current_csv(conn, RAW_CSV)
        print(f"✅ Ingestion complete: inserted={ins}, updated={upd}")
        print(f"DB: {DB_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
