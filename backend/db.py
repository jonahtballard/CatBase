import sqlite3, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", "processed", "university_courses.db")

def get_conn_ro():
    # read-only: if path is wrong, this will error instead of making an empty DB
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

def rows_to_dicts(rows):
    cols = [c[0] for c in rows.description]
    return [dict(zip(cols, r)) for r in rows.fetchall()]

def query(sql, params=()):
    conn = get_conn_ro()
    conn.row_factory = None  # we’ll convert manually for speed
    cur = conn.cursor()
    cur.execute(sql, params)
    result = rows_to_dicts(cur)
    conn.close()
    return result
