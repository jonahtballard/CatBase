#!/usr/bin/env python3
"""
Ingest ALL cleaned term CSVs (historical + current) into SQLite.

- Scans data/processed/*_cleaned.csv
- Robust header aliasing: handles CRN/Comp Numb, #/Number, Subject/Subj, etc.
- Falls back to term from filename if Semester/Year columns are missing.
- Idempotent: sections unique on (term_id, crn); meetings rebuilt; instructor links OR IGNORE.

If a row truly lacks required fields (subject, number, title, crn), it's skipped.
"""

import csv, os, re, sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parents[1]       # .../backend
DATA_DIR = BASE_DIR.parent / "data"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = PROCESSED_DIR / "university_courses.db"

# ---- Header alias map --------------------------------------------------------
ALIASES: Dict[str, List[str]] = {
    # required fields
    "Subj":        ["Subj", "SUBJ", "Subject", "Subject Code", "Dept", "Dept Code"],
    "Number":      ["Number", "#", "Course Number", "Course #", "Catalog Nbr", "Catalog Number"],
    "Title":       ["Title", "Course Title", "Long Title"],
    "Comp Numb":   ["Comp Numb", "CRN", "Crn", "Course Reference Number"],

    # optional / nice-to-have
    "Lec Lab":     ["Lec Lab", "Component", "Cmpnt", "Type"],
    "Credits":     ["Credits", "Credit Hrs", "Credit Hours"],
    "Start Time":  ["Start Time", "Start", "Begin Time", "Meeting Start Time"],
    "End Time":    ["End Time", "End", "Finish Time", "Meeting End Time"],
    "Days":        ["Days", "Day", "Meeting Days"],
    "Bldg":        ["Bldg", "Building", "Bldg Code"],
    "Room":        ["Room", "Room Nbr", "Room Number"],
    "Location":    ["Location", "Campus", "Bldg/Room", "Loc"],
    "Instructor":  ["Instructor", "Primary Instructor", "Instr", "Instructor Name"],
    "NetId":       ["NetId", "NetID", "Net Id", "Netid"],
    "Email":       ["Email", "E-mail", "Instructor Email", "Email Address"],
    "Max Enrollment":     ["Max Enrollment", "Cap", "Capacity", "Enrollment Cap", "Max Enrl"],
    "Current Enrollment": ["Current Enrollment", "Enrolled", "Enrollment", "Current Enrl"],

    # term hints
    "Semester":    ["Semester", "Term", "Term Name"],
    "Year":        ["Year", "Term Year"],
}

RE_FILENAME_TERM = re.compile(r"uvm_(spring|summer|fall|winter)_(\d{4})_cleaned\.csv", re.I)

def norm(s): return (s if s is not None else "").strip()

def is_missing(x):
    s = str(x) if x is not None else ""
    return s.strip() == "" or s.strip().lower() == "nan"

def to_int(x):
    s = norm(x)
    if not s or s.lower() == "nan":
        return None
    try:
        return int(float(s))
    except Exception:
        return None

def parse_credits(s: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """
    Accepts '3', '1 - 18', '1 to 18', and en/em dashes.
    """
    s = norm(s)
    if not s:
        return (None, None)
    s = s.replace("to", "-").replace("–", "-").replace("—", "-")
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*$", s)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    try:
        v = float(s)
        return (v, v)
    except Exception:
        return (None, None)

# ---- DB schema helpers -------------------------------------------------------

def init_schema(conn: sqlite3.Connection):
    conn.executescript("""
    PRAGMA foreign_keys=ON;

    CREATE TABLE IF NOT EXISTS terms (
      term_id   INTEGER PRIMARY KEY,
      semester  TEXT NOT NULL,
      year      INTEGER NOT NULL,
      UNIQUE(semester, year)
    );

    CREATE TABLE IF NOT EXISTS subjects (
      subject_id INTEGER PRIMARY KEY,
      code       TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS courses (
      course_id     INTEGER PRIMARY KEY,
      subject_id    INTEGER NOT NULL REFERENCES subjects(subject_id),
      course_number TEXT NOT NULL,
      title         TEXT NOT NULL,
      UNIQUE(subject_id, course_number, title)
    );

    CREATE TABLE IF NOT EXISTS instructors (
      instructor_id INTEGER PRIMARY KEY,
      name   TEXT NOT NULL,
      netid  TEXT,
      email  TEXT,
      rmp_id TEXT, rmp_school_id TEXT, rmp_url TEXT,
      rmp_avg_rating REAL, rmp_num_ratings INTEGER,
      rmp_would_take_again REAL, rmp_difficulty REAL,
      rmp_last_refreshed TEXT, rmp_top_tags_json TEXT, rmp_rating_distribution_json TEXT,
      UNIQUE(name, COALESCE(netid,''), COALESCE(email,''))
    );

    CREATE TABLE IF NOT EXISTS sections (
      section_id  INTEGER PRIMARY KEY,
      course_id   INTEGER NOT NULL REFERENCES courses(course_id),
      term_id     INTEGER NOT NULL REFERENCES terms(term_id),
      crn         TEXT NOT NULL,
      lec_lab     TEXT,
      credits_min REAL,
      credits_max REAL,
      max_enrollment INTEGER,
      current_enrollment INTEGER,
      UNIQUE(term_id, crn)
    );

    CREATE TABLE IF NOT EXISTS meetings (
      meeting_id INTEGER PRIMARY KEY,
      section_id INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
      start_time TEXT, end_time TEXT, days TEXT, bldg TEXT, room TEXT, location TEXT
    );

    CREATE TABLE IF NOT EXISTS section_instructors (
      section_id    INTEGER NOT NULL REFERENCES sections(section_id) ON DELETE CASCADE,
      instructor_id INTEGER NOT NULL REFERENCES instructors(instructor_id) ON DELETE CASCADE,
      role TEXT,
      PRIMARY KEY (section_id, instructor_id)
    );
    """)

def get_term_id(conn, semester, year):
    r = conn.execute("SELECT term_id FROM terms WHERE semester=? AND year=?", (semester, year)).fetchone()
    if r: return r[0]
    conn.execute("INSERT OR IGNORE INTO terms (semester, year) VALUES (?,?)", (semester, year))
    return conn.execute("SELECT term_id FROM terms WHERE semester=? AND year=?", (semester, year)).fetchone()[0]

def get_subject_id(conn, code):
    code = norm(code)
    if not code: return None
    conn.execute("INSERT OR IGNORE INTO subjects(code) VALUES (?)", (code,))
    return conn.execute("SELECT subject_id FROM subjects WHERE code=?", (code,)).fetchone()[0]

def get_course_id(conn, subject_id, number, title):
    number, title = norm(number), norm(title)
    r = conn.execute(
        "SELECT course_id FROM courses WHERE subject_id=? AND course_number=? AND title=?",
        (subject_id, number, title)
    ).fetchone()
    if r: return r[0]
    conn.execute("INSERT INTO courses(subject_id, course_number, title) VALUES (?,?,?)",
                 (subject_id, number, title))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

def get_instructor_id(conn, name, netid, email):
    name, netid, email = norm(name), (norm(netid) or None), (norm(email) or None)
    if not name: return None
    r = conn.execute(
        "SELECT instructor_id FROM instructors WHERE name=? AND COALESCE(netid,'')=COALESCE(?,'') AND COALESCE(email,'')=COALESCE(?,'')",
        (name, netid, email)
    ).fetchone()
    if r: return r[0]
    conn.execute("INSERT OR IGNORE INTO instructors(name, netid, email) VALUES (?,?,?)",
                 (name, netid, email))
    return conn.execute(
        "SELECT instructor_id FROM instructors WHERE name=? AND COALESCE(netid,'')=COALESCE(?,'') AND COALESCE(email,'')=COALESCE(?,'')",
        (name, netid, email)
    ).fetchone()[0]

def upsert_section_and_get_id(conn, course_id, term_id, crn, lec_lab, cmin, cmax, max_enr, cur_enr):
    conn.execute("""
        INSERT INTO sections
          (course_id, term_id, crn, lec_lab, credits_min, credits_max, max_enrollment, current_enrollment)
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(term_id, crn) DO UPDATE SET
          course_id=excluded.course_id,
          lec_lab=excluded.lec_lab,
          credits_min=excluded.credits_min,
          credits_max=excluded.credits_max,
          max_enrollment=excluded.max_enrollment,
          current_enrollment=excluded.current_enrollment
    """, (course_id, term_id, crn, lec_lab, cmin, cmax, max_enr, cur_enr))
    return conn.execute(
        "SELECT section_id FROM sections WHERE term_id=? AND crn=?",
        (term_id, crn)
    ).fetchone()[0]

# ---- Column mapping per file -------------------------------------------------

def build_keymap(headers: List[str]) -> Dict[str, Optional[str]]:
    H = {h.strip(): h.strip() for h in headers if h is not None}
    hset = set(H.keys())
    keymap = {}
    for canon, alts in ALIASES.items():
        chosen = None
        for a in alts:
            if a in hset:
                chosen = H[a]; break
            # case-insensitive match as fallback
            for h in hset:
                if h.lower() == a.lower():
                    chosen = H[h]; break
            if chosen: break
        keymap[canon] = chosen
    return keymap

def getv(row: Dict[str, str], keymap: Dict[str, Optional[str]], canon: str) -> Optional[str]:
    k = keymap.get(canon)
    return norm(row.get(k)) if k else None

def term_from_filename(path: Path) -> Tuple[str, Optional[int]]:
    m = RE_FILENAME_TERM.match(path.name)
    if not m: return ("Unknown", None)
    sem = m.group(1).capitalize()   # Spring/Summer/Fall/Winter
    yr = int(m.group(2))
    return (sem, yr)

# ---- Ingest one CSV ----------------------------------------------------------

def ingest_csv(conn, csv_path: Path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print(f"[warn] {csv_path.name}: empty file")
        return 0

    keymap = build_keymap(reader.fieldnames or [])

    # derive term
    semester = getv(rows[0], keymap, "Semester")
    year_str = getv(rows[0], keymap, "Year")
    if is_missing(semester) or is_missing(year_str):
        # fall back to filename
        semester, year = term_from_filename(csv_path)
    else:
        try:
            year = int(float(year_str))
        except Exception:
            _, year = term_from_filename(csv_path)

    term_id = get_term_id(conn, semester, year)

    processed, skipped = 0, 0
    # sanity for required columns: we’ll allow multiple aliases
    for idx, r in enumerate(rows, start=2):
        subj   = getv(r, keymap, "Subj")
        number = getv(r, keymap, "Number")
        title  = getv(r, keymap, "Title")

        crn = getv(r, keymap, "Comp Numb")  # alias includes CRN/Comp Numb etc.

        if any(is_missing(v) for v in (subj, number, title, crn)):
            skipped += 1
            continue

        lec   = getv(r, keymap, "Lec Lab")
        cmin, cmax = parse_credits(getv(r, keymap, "Credits"))
        max_enr    = to_int(getv(r, keymap, "Max Enrollment"))
        cur_enr    = to_int(getv(r, keymap, "Current Enrollment"))

        subject_id = get_subject_id(conn, subj)
        if subject_id is None:
            skipped += 1
            continue

        course_id  = get_course_id(conn, subject_id, number, title)
        section_id = upsert_section_and_get_id(conn, course_id, term_id, crn, lec, cmin, cmax, max_enr, cur_enr)

        # Rebuild meetings
        conn.execute("DELETE FROM meetings WHERE section_id=?", (section_id,))
        start = getv(r, keymap, "Start Time") or None
        end   = getv(r, keymap, "End Time") or None
        days  = getv(r, keymap, "Days") or None
        bldg  = getv(r, keymap, "Bldg") or None
        room  = getv(r, keymap, "Room") or None
        loc   = getv(r, keymap, "Location") or None

        conn.execute(
            "INSERT INTO meetings(section_id,start_time,end_time,days,bldg,room,location) VALUES (?,?,?,?,?,?,?)",
            (section_id, start, end, days, bldg, room, loc)
        )

        # Instructors
        inst_name = getv(r, keymap, "Instructor") or None
        if inst_name:
            inst_id = get_instructor_id(conn, inst_name, getv(r, keymap, "NetId"), getv(r, keymap, "Email"))
            if inst_id:
                conn.execute(
                    "INSERT OR IGNORE INTO section_instructors(section_id,instructor_id,role) VALUES (?,?,?)",
                    (section_id, inst_id, None)
                )
        processed += 1

    if skipped:
        print(f"[note] {csv_path.name}: skipped {skipped} malformed row(s)")
    return processed

# ---- Main --------------------------------------------------------------------

def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys=ON;")
    init_schema(conn)

    total = 0
    for f in sorted(PROCESSED_DIR.glob("*_cleaned.csv")):
        n = ingest_csv(conn, f)
        conn.commit()
        print(f"[ingested] {f.name}: {n} rows")
        total += n
    print(f"Done. Total rows processed: {total}")
    conn.close()

if __name__ == "__main__":
    main()
