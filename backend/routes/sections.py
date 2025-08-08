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
    """
    Query params:
      search        -> matches course title, number, subject code
      subject       -> exact subject code
      semester      -> 'Spring','Summer','Fall','Winter'
      year          -> int
      crn           -> exact CRN
      instructor_id -> int
      instructor    -> partial instructor name
      limit         -> page size
      offset        -> page offset
    """
    q             = (request.args.get("search") or "").strip()
    subject       = (request.args.get("subject") or "").strip()
    semester      = (request.args.get("semester") or "").strip()
    year          = request.args.get("year", type=int)
    crn           = (request.args.get("crn") or "").strip()
    instructor_id = request.args.get("instructor_id", type=int)
    instructor    = (request.args.get("instructor") or "").strip()
    limit         = request.args.get("limit", type=int) or 50
    offset        = request.args.get("offset", type=int) or 0

    conn = get_conn_ro()
    cur  = conn.cursor()

    where = ["1=1"]
    params = []

    if q:
        where.append("(c.title LIKE ? OR c.course_number LIKE ? OR sub.code LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    if subject:
        where.append("sub.code = ?")
        params.append(subject)

    if semester:
        where.append("t.semester = ?")
        params.append(semester)

    if year is not None:
        where.append("t.year = ?")
        params.append(year)

    if crn:
        where.append("s.crn = ?")
        params.append(crn)

    if instructor_id:
        where.append("""
            s.section_id IN (
              SELECT section_id FROM section_instructors WHERE instructor_id = ?
            )
        """)
        params.append(instructor_id)

    if instructor:
        where.append("""
            s.section_id IN (
              SELECT si.section_id
              FROM section_instructors si
              JOIN instructors i ON i.instructor_id = si.instructor_id
              WHERE i.name LIKE ?
            )
        """)
        params.append(f"%{instructor}%")

    where_sql = " AND ".join(where)

    # --- Correct total: count DISTINCT matching sections BEFORE pagination ---
    total_sql = f"""
        SELECT COUNT(*) FROM (
          SELECT DISTINCT s.section_id
          FROM sections s
          JOIN courses  c   ON c.course_id   = s.course_id
          JOIN subjects sub ON sub.subject_id= c.subject_id
          JOIN terms    t   ON t.term_id     = s.term_id
          WHERE {where_sql}
        )
    """
    cur.execute(total_sql, params)
    total = cur.fetchone()[0] or 0

    # --- Page query: fetch sections + aggregate meetings (one row per section) ---
    page_sql = f"""
        SELECT
          c.course_id,
          sub.code                      AS subject,
          c.course_number,
          c.title,
          s.section_id,
          s.crn,
          t.term_id,
          t.semester,
          t.year,
          s.lec_lab,
          s.credits_min,
          s.credits_max,
          s.max_enrollment,
          s.current_enrollment,
          GROUP_CONCAT(
            printf(
              '%s|%s|%s|%s|%s|%s',
              IFNULL(m.days,''),
              IFNULL(m.start_time,''),
              IFNULL(m.end_time,''),
              IFNULL(m.bldg,''),
              IFNULL(m.room,''),
              IFNULL(m.location,'')
            ),
            ';;'
          ) AS meetings_concat
        FROM sections s
        JOIN courses  c   ON c.course_id   = s.course_id
        JOIN subjects sub ON sub.subject_id= c.subject_id
        JOIN terms    t   ON t.term_id     = s.term_id
        LEFT JOIN meetings m ON m.section_id = s.section_id
        WHERE {where_sql}
        GROUP BY s.section_id
        ORDER BY t.year DESC, {_semester_sort_sql('t')}, sub.code, c.course_number
        LIMIT ? OFFSET ?
    """
    cur.execute(page_sql, params + [limit, offset])
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    # expand meetings + attach instructors for each section
    for r in rows:
        mc = r.pop("meetings_concat", None)
        meetings = []
        if mc:
            for chunk in mc.split(";;"):
                parts = chunk.split("|")
                if len(parts) == 6:
                    meetings.append({
                        "days": parts[0] or None,
                        "start_time": parts[1] or None,
                        "end_time": parts[2] or None,
                        "bldg": parts[3] or None,
                        "room": parts[4] or None,
                        "location": parts[5] or None,
                    })
        r["meetings"] = meetings

        sec_id = r["section_id"]
        cur.execute("""
            SELECT i.instructor_id, i.name, i.netid, i.email
            FROM section_instructors si
            JOIN instructors i ON si.instructor_id = i.instructor_id
            WHERE si.section_id = ?
            ORDER BY i.name
        """, (sec_id,))
        instr_cols = [d[0] for d in cur.description]
        r["instructors"] = [dict(zip(instr_cols, x)) for x in cur.fetchall()]

    conn.close()
    return jsonify({
        "items": rows,
        "total": total,   # real total across all pages
        "limit": limit,
        "offset": offset,
    })
