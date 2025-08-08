from flask import Blueprint, jsonify
from ..db import get_conn_ro

subjects_bp = Blueprint("subjects", __name__)

@subjects_bp.get("/subjects")
def list_subjects():
    conn = get_conn_ro()
    cur = conn.cursor()
    cur.execute("SELECT subject_id, code FROM subjects ORDER BY code")
    rows = [{"subject_id": r[0], "code": r[1]} for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)
