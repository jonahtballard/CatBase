from flask import Blueprint, request, jsonify
from ..db import get_conn_ro

instructors_bp = Blueprint("instructors", __name__)

@instructors_bp.get("/instructors")
def list_instructors():
    search = (request.args.get("search") or "").strip()
    limit = request.args.get("limit", type=int) or 50
    offset = request.args.get("offset", type=int) or 0

    conn = get_conn_ro()
    cur = conn.cursor()

    if search:
        cur.execute("""
            SELECT instructor_id, name, netid, email
            FROM instructors
            WHERE name LIKE ?
            ORDER BY name
            LIMIT ? OFFSET ?
        """, (f"%{search}%", limit, offset))
    else:
        cur.execute("""
            SELECT instructor_id, name, netid, email
            FROM instructors
            ORDER BY name
            LIMIT ? OFFSET ?
        """, (limit, offset))

    rows = [
        {"instructor_id": r[0], "name": r[1], "netid": r[2], "email": r[3]}
        for r in cur.fetchall()
    ]
    conn.close()
    return jsonify(rows)
