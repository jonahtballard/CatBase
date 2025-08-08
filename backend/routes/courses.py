from flask import Blueprint, request, jsonify
from ..db import get_conn_ro

courses_bp = Blueprint("courses", __name__)

@courses_bp.get("/courses")
def list_courses():
    search = (request.args.get("search") or "").strip()
    subject = (request.args.get("subject") or "").strip()
    limit = request.args.get("limit", type=int) or 50
    offset = request.args.get("offset", type=int) or 0

    conn = get_conn_ro()
    cur = conn.cursor()

    where = ["1=1"]
    params = []

    if search:
        where.append("(c.title LIKE ? OR c.course_number LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like])

    if subject:
        where.append("sub.code = ?")
        params.append(subject)

    where_sql = " AND ".join(where)

    cur.execute(f"""
        SELECT c.course_id, c.course_number, c.title,
               sub.code AS subject
        FROM courses c
        JOIN subjects sub ON sub.subject_id = c.subject_id
        WHERE {where_sql}
        ORDER BY sub.code, c.course_number
        LIMIT ? OFFSET ?
    """, params + [limit, offset])

    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)
