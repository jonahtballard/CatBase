from flask import Blueprint, jsonify
from ..db import get_conn_ro

terms_bp = Blueprint("terms", __name__)

@terms_bp.get("/terms")
def list_terms():
    conn = get_conn_ro()
    cur = conn.cursor()
    cur.execute("""
        SELECT term_id, semester, year
        FROM terms
        ORDER BY year DESC,
                 CASE semester
                   WHEN 'Spring' THEN 1
                   WHEN 'Summer' THEN 2
                   WHEN 'Fall' THEN 3
                   WHEN 'Winter' THEN 4
                   ELSE 5
                 END
    """)
    rows = [{"term_id": r[0], "semester": r[1], "year": r[2]} for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)
