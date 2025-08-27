# backend/routes/analytics.py
from flask import Blueprint, request, jsonify
from ..db import get_conn_ro  # uses your existing DB helper

analytics_bp = Blueprint("analytics", __name__)

# Keep semesters in a consistent order
SEM_ORDER = """
CASE t.semester
  WHEN 'Spring' THEN 1
  WHEN 'Summer' THEN 2
  WHEN 'Fall'   THEN 3
  WHEN 'Winter' THEN 4
  ELSE 5
END
"""

def _filters():
    where, args = [], []

    # subjects=CS,MATH
    subjects = request.args.get("subjects")
    if subjects:
        codes = [s.strip() for s in subjects.split(",") if s.strip()]
        if codes:
            where.append(f"sub.code IN ({','.join(['?']*len(codes))})")
            args.extend(codes)

    # level=100,200 (filters on course_number LIKE '1__', '2__')
    levels = request.args.get("level")
    if levels:
        lvls = [l.strip() for l in levels.split(",") if l.strip()]
        like_parts = []
        for l in lvls:
            if l and l[0].isdigit():
                like_parts.append("c.course_number LIKE ?")
                args.append(f"{l[0]}__")
        if like_parts:
            where.append("(" + " OR ".join(like_parts) + ")")

    # start_year/end_year
    start_year = request.args.get("start_year", type=int)
    end_year   = request.args.get("end_year", type=int)
    if start_year is not None:
        where.append("t.year >= ?")
        args.append(start_year)
    if end_year is not None:
        where.append("t.year <= ?")
        args.append(end_year)

    return where, args

@analytics_bp.get("/analytics/enrollment_over_time")
def enrollment_over_time():
    """
    Timeseries by term:
      - SUM current_enrollment, SUM max_enrollment, COUNT sections
    Grouped by subject if `subjects` provided.
    """
    conn = get_conn_ro(); cur = conn.cursor()
    where, args = _filters()
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    group_by_subject = bool(request.args.get("subjects"))
    subject_select = "sub.code AS subject," if group_by_subject else "'' AS subject,"
    subject_group  = "subject," if group_by_subject else ""

    sql = f"""
      SELECT
        {subject_select}
        t.year, t.semester,
        SUM(COALESCE(s.current_enrollment,0)) AS cur_enroll,
        SUM(COALESCE(s.max_enrollment,0))     AS max_enroll,
        COUNT(*) AS sections
      FROM sections s
      JOIN courses  c   ON c.course_id   = s.course_id
      JOIN subjects sub ON sub.subject_id = c.subject_id
      JOIN terms    t   ON t.term_id     = s.term_id
      {where_sql}
      GROUP BY {subject_group} t.year, t.semester
      ORDER BY t.year ASC, {SEM_ORDER} ASC
    """
    rows = cur.execute(sql, args).fetchall()
    out = [dict(zip([d[0] for d in cur.description], r)) for r in rows]
    conn.close()
    return jsonify(out)

@analytics_bp.get("/analytics/sections_over_time")
def sections_over_time():
    conn = get_conn_ro(); cur = conn.cursor()
    where, args = _filters()
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    group_by_subject = bool(request.args.get("subjects"))
    subject_select = "sub.code AS subject," if group_by_subject else "'' AS subject,"
    subject_group  = "subject," if group_by_subject else ""

    sql = f"""
      SELECT
        {subject_select}
        t.year, t.semester,
        COUNT(*) AS sections
      FROM sections s
      JOIN courses  c   ON c.course_id   = s.course_id
      JOIN subjects sub ON sub.subject_id = c.subject_id
      JOIN terms    t   ON t.term_id     = s.term_id
      {where_sql}
      GROUP BY {subject_group} t.year, t.semester
      ORDER BY t.year ASC, {SEM_ORDER} ASC
    """
    rows = cur.execute(sql, args).fetchall()
    out = [dict(zip([d[0] for d in cur.description], r)) for r in rows]
    conn.close()
    return jsonify(out)

@analytics_bp.get("/analytics/course_birth_death")
def course_birth_death():
    """
    For each term: count how many (subject, course_number) appear for the first time (birth)
    or last time (death).
    """
    conn = get_conn_ro(); cur = conn.cursor()
    where, args = _filters()
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
      WITH course_terms AS (
        SELECT
          sub.code AS subject,
          c.course_number,
          MIN(t.year*10 + {SEM_ORDER}) AS first_key,
          MAX(t.year*10 + {SEM_ORDER}) AS last_key
        FROM sections s
        JOIN courses  c   ON c.course_id   = s.course_id
        JOIN subjects sub ON sub.subject_id = c.subject_id
        JOIN terms    t   ON t.term_id     = s.term_id
        {where_sql}
        GROUP BY sub.code, c.course_number
      ),
      term_keys AS (
        SELECT t.year, t.semester, (t.year*10 + {SEM_ORDER}) AS term_key
        FROM terms t
      )
      SELECT
        tk.year, tk.semester,
        SUM(CASE WHEN ct.first_key = tk.term_key THEN 1 ELSE 0 END) AS births,
        SUM(CASE WHEN ct.last_key  = tk.term_key THEN 1 ELSE 0 END) AS deaths
      FROM term_keys tk
      LEFT JOIN course_terms ct ON 1=1
      GROUP BY tk.year, tk.semester
      HAVING births > 0 OR deaths > 0
      ORDER BY tk.year ASC, {SEM_ORDER} ASC
    """
    rows = cur.execute(sql, args).fetchall()
    out = [dict(zip([d[0] for d in cur.description], r)) for r in rows]
    conn.close()
    return jsonify(out)

@analytics_bp.get("/analytics/meeting_heatmap")
def meeting_heatmap():
    """Heatmap of section counts over Day x Start-Hour."""
    conn = get_conn_ro(); cur = conn.cursor()
    where, args = _filters()
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
      SELECT
        m.days AS days,
        CAST(substr(m.start_time, 1, instr(m.start_time, ':') - 1) AS INTEGER) AS hour,
        COUNT(*) AS n
      FROM meetings m
      JOIN sections s ON s.section_id = m.section_id
      JOIN courses  c ON c.course_id  = s.course_id
      JOIN subjects sub ON sub.subject_id = c.subject_id
      JOIN terms t ON t.term_id = s.term_id
      {where_sql}
      GROUP BY m.days, hour
      ORDER BY hour ASC
    """
    rows = cur.execute(sql, args).fetchall()
    out = [dict(zip([d[0] for d in cur.description], r)) for r in rows]
    conn.close()
    return jsonify(out)

@analytics_bp.get("/analytics/credits_distribution")
def credits_distribution():
    """Distribution of average credits per section (by term)."""
    conn = get_conn_ro(); cur = conn.cursor()
    where, args = _filters()
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
      SELECT
        t.year, t.semester,
        ROUND((COALESCE(s.credits_min, s.credits_max) + COALESCE(s.credits_max, s.credits_min)) / 2.0, 1) AS credits,
        COUNT(*) AS n
      FROM sections s
      JOIN courses  c   ON c.course_id   = s.course_id
      JOIN subjects sub ON sub.subject_id = c.subject_id
      JOIN terms    t   ON t.term_id     = s.term_id
      {where_sql}
      GROUP BY t.year, t.semester, credits
      ORDER BY t.year ASC, {SEM_ORDER} ASC, credits ASC
    """
    rows = cur.execute(sql, args).fetchall()
    out = [dict(zip([d[0] for d in cur.description], r)) for r in rows]
    conn.close()
    return jsonify(out)
