from flask import Blueprint, jsonify
from ..db import get_conn_ro

meetings_bp = Blueprint("meetings", __name__)

@meetings_bp.get("/meetings/<int:section_id>")
def get_meetings(section_id):
    conn = get_conn_ro()
    cur = conn.cursor()
    cur.execute("""
        SELECT meeting_id, days, start_time, end_time, bldg, room, location
        FROM meetings
        WHERE section_id = ?
        ORDER BY meeting_id
    """, (section_id,))
    rows = [
        {
            "meeting_id": r[0],
            "days": r[1],
            "start_time": r[2],
            "end_time": r[3],
            "bldg": r[4],
            "room": r[5],
            "location": r[6],
        }
        for r in cur.fetchall()
    ]
    conn.close()
    return jsonify(rows)
