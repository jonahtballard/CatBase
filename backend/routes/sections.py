from flask import Blueprint, request, jsonify
from ..db import get_conn_ro

sections_bp = Blueprint("sections", __name__)

def _semester_sort_sql(alias="t"):
    return f"""
        CASE {alias}.semester
            WHEN 'Spring' THEN 1
            WHEN 'Summer' THEN 2
            WHEN 'Fall'   THEN 3
            WHEN 'Winter' THEN 4
            ELSE 5
        END
    """

@sections_bp.get("/sections")
def list_sections():
    search = (request.args.get("search") or "").strip()
    instructor = (request.args.get("instructor") or "").strip()
    instructor_id = request.args.get("instructor_id", type=int)
    subject = (request.args.get("subject") or "").strip()
    term_id = request.args.get("term_id", type=int)
    limit = request.args.get("limit", type=int) or 50
    offset = request.args.get("offset", type=int) or 0

    conn = get_conn_ro()
    cur = conn.cursor()

    where = ["1=1"]
    params = []

    if search:
        where.append("(c.title LIKE ? OR c.course_number LIKE ? OR sub.code LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    if subject:
        where.append("sub.code = ?")
        params.append(subject)

    if term_id:
        where.append("t.term_id = ?")
        params.append(term_id)

    if instructor_id:
        where.append("""
            s.section_id IN (
                SELECT section_id FROM section_instructors
                WHERE instructor_id = ?
            )
        """)
        params.append(instructor_id)

    if instructor:
        where.append("""
            s.section_id IN (
                SELECT si.section_id
                FROM section_instructors si
                JOIN instructors i ON si.instructor_id = i.instructor_id
                WHERE i.name LIKE ?
            )
        """)
        params.append(f"%{instructor}%")

    where_sql = " AND ".join(where)

    sql = f"""
        SELECT s.section_id, s.crn, s.lec_lab, s.credits_min, s.credits_max,
               s.max_enrollment, s.current_enrollment,
               c.course_id, c.course_number, c.title,
               sub.code AS subject,
               t.term_id, t.semester, t.year
        FROM sections s
        JOIN courses c ON c.course_id = s.course_id
        JOIN subjects sub ON sub.subject_id = c.subject_id
        JOIN terms t ON t.term_id = s.term_id
        WHERE {where_sql}
        ORDER BY t.year DESC, {_semester_sort_sql('t')}, sub.code, c.course_number
        LIMIT ? OFFSET ?
    """
    cur.execute(sql, params + [limit, offset])
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    # Attach instructors and meetings
    for r in rows:
        sec_id = r["section_id"]

        cur.execute("""
            SELECT i.instructor_id, i.name, i.netid, i.email
            FROM section_instructors si
            JOIN instructors i ON si.instructor_id = i.instructor_id
            WHERE si.section_id = ?
            ORDER BY i.name
        """, (sec_id,))
        r["instructors"] = [dict(zip([d[0] for d in cur.description], x)) for x in cur.fetchall()]

        cur.execute("""
            SELECT meeting_id, days, start_time, end_time, bldg, room, location
            FROM meetings
            WHERE section_id = ?
        """, (sec_id,))
        r["meetings"] = [dict(zip([d[0] for d in cur.description], x)) for x in cur.fetchall()]

    conn.close()

    return jsonify({"items": rows, "limit": limit, "offset": offset})
