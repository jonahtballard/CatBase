from __future__ import annotations

from flask import Blueprint, request, jsonify
from typing import Any, Dict, List, Tuple, Optional
from ..db import get_conn_ro

sections_bp = Blueprint("sections", __name__)

# Try these in order; the first existing column will be used
DIFFICULTY_CANDIDATES = ["rmp_difficulty", "rmp_avg_difficulty", "difficulty"]

def _semester_sort_sql(alias: str = "t") -> str:
    return f"""
        CASE {alias}.semester
            WHEN 'Spring' THEN 1
            WHEN 'Summer' THEN 2
            WHEN 'Fall'   THEN 3
            WHEN 'Winter' THEN 4
            ELSE 5
        END
    """

def _parse_params() -> Dict[str, Any]:
    q             = (request.args.get("search") or "").strip()
    subject       = (request.args.get("subject") or "").strip()
    semester      = (request.args.get("semester") or "").strip()
    year          = request.args.get("year", type=int)
    crn           = (request.args.get("crn") or "").strip()
    instructor_id = request.args.get("instructor_id", type=int)
    instructor    = (request.args.get("instructor") or "").strip()

    min_credits   = request.args.get("min_credits", type=float)
    max_credits   = request.args.get("max_credits", type=float)

    status        = (request.args.get("status") or "").strip().lower()
    if status not in ("open", "closed"):
        status = None

    # RMP filters (NULLs should PASS)
    rmp_min_rating     = request.args.get("rmp_min_rating", type=float)
    rmp_min_count      = request.args.get("rmp_min_count", type=int)
    rmp_max_difficulty = request.args.get("rmp_max_difficulty", type=float)

    limit         = request.args.get("limit", type=int) or 50
    offset        = request.args.get("offset", type=int) or 0

    return {
        "q": q,
        "subject": subject,
        "semester": semester,
        "year": year,
        "crn": crn,
        "instructor_id": instructor_id,
        "instructor": instructor,
        "min_credits": min_credits,
        "max_credits": max_credits,
        "status": status,
        "rmp_min_rating": rmp_min_rating,
        "rmp_min_count": rmp_min_count,
        "rmp_max_difficulty": rmp_max_difficulty,
        "limit": limit,
        "offset": offset,
    }

def _build_where(params: Dict[str, Any], difficulty_col: Optional[str]) -> Tuple[str, List[Any]]:
    where: List[str] = ["1=1"]
    args: List[Any] = []

    q = params["q"]
    if q:
        like = f"%{q}%"
        where.append("""
            (
                c.title LIKE ? OR c.course_number LIKE ? OR sub.code LIKE ?
                OR EXISTS (
                    SELECT 1
                    FROM section_instructors si
                    JOIN instructors i ON i.instructor_id = si.instructor_id
                    WHERE si.section_id = s.section_id
                      AND i.name LIKE ?
                )
            )
        """)
        args.extend([like, like, like, like])

    if params["subject"]:
        where.append("sub.code = ?")
        args.append(params["subject"])

    if params["semester"]:
        where.append("t.semester = ?")
        args.append(params["semester"])

    if params["year"] is not None:
        where.append("t.year = ?")
        args.append(params["year"])

    if params["crn"]:
        where.append("s.crn = ?")
        args.append(params["crn"])

    if params["instructor_id"]:
        where.append("""
            EXISTS (
              SELECT 1 FROM section_instructors si
              WHERE si.section_id = s.section_id AND si.instructor_id = ?
            )
        """)
        args.append(params["instructor_id"])

    if params["instructor"]:
        like = f"%{params['instructor']}%"
        where.append("""
            EXISTS (
              SELECT 1
              FROM section_instructors si
              JOIN instructors i ON i.instructor_id = si.instructor_id
              WHERE si.section_id = s.section_id
                AND i.name LIKE ?
            )
        """)
        args.append(like)

    # Credits
    if params["min_credits"] is not None:
        where.append("COALESCE(s.credits_min, 0) >= ?")
        args.append(params["min_credits"])

    if params["max_credits"] is not None:
        where.append("COALESCE(s.credits_max, s.credits_min) <= ?")
        args.append(params["max_credits"])

    # Status
    if params["status"] == "open":
        where.append("""
            s.max_enrollment IS NOT NULL
            AND s.current_enrollment IS NOT NULL
            AND s.current_enrollment < s.max_enrollment
        """)
    elif params["status"] == "closed":
        where.append("""
            s.max_enrollment IS NOT NULL
            AND s.current_enrollment IS NOT NULL
            AND s.current_enrollment >= s.max_enrollment
        """)

    # RMP filters (NULLs pass)
    rmin = params["rmp_min_rating"]
    if rmin is not None:
        where.append("""
            EXISTS (
              SELECT 1
              FROM section_instructors si
              JOIN instructors i ON i.instructor_id = si.instructor_id
              WHERE si.section_id = s.section_id
                AND (i.rmp_avg_rating IS NULL OR i.rmp_avg_rating >= ?)
            )
        """)
        args.append(rmin)

    rcnt = params["rmp_min_count"]
    if rcnt is not None:
        where.append("""
            EXISTS (
              SELECT 1
              FROM section_instructors si
              JOIN instructors i ON i.instructor_id = si.instructor_id
              WHERE si.section_id = s.section_id
                AND (i.rmp_num_ratings IS NULL OR i.rmp_num_ratings >= ?)
            )
        """)
        args.append(rcnt)

    rdiff = params["rmp_max_difficulty"]
    if rdiff is not None and difficulty_col:
        where.append(f"""
            EXISTS (
              SELECT 1
              FROM section_instructors si
              JOIN instructors i ON i.instructor_id = si.instructor_id
              WHERE si.section_id = s.section_id
                AND (i.{difficulty_col} IS NULL OR i.{difficulty_col} <= ?)
            )
        """)
        args.append(rdiff)

    return " AND ".join(where), args

def _detect_difficulty_col(conn) -> Optional[str]:
    cur = conn.execute("PRAGMA table_info(instructors)")
    cols = {row[1] for row in cur.fetchall()}
    for cand in DIFFICULTY_CANDIDATES:
        if cand in cols:
            return cand
    return None

@sections_bp.get("/sections")
def list_sections():
    p = _parse_params()
    limit  = int(p["limit"])
    offset = max(0, int(p["offset"]))

    conn = get_conn_ro()
    try:
        difficulty_col = _detect_difficulty_col(conn)  # should be "rmp_difficulty" for your DB
        where_sql, args = _build_where(p, difficulty_col)

        count_sql = f"""
            SELECT COUNT(*)
            FROM sections s
            JOIN courses  c   ON c.course_id   = s.course_id
            JOIN subjects sub ON sub.subject_id = c.subject_id
            JOIN terms    t   ON t.term_id     = s.term_id
            WHERE {where_sql}
        """

        data_sql = f"""
            SELECT
                s.section_id, s.crn, s.lec_lab,
                s.credits_min, s.credits_max, s.max_enrollment, s.current_enrollment,
                c.course_id, c.course_number, c.title,
                sub.code AS subject,
                t.semester, t.year,
                GROUP_CONCAT(
                  printf(
                    '%s|%s|%s|%s|%s|%s',
                    IFNULL(m.days,''), IFNULL(m.start_time,''), IFNULL(m.end_time,''),
                    IFNULL(m.bldg,''), IFNULL(m.room,''), IFNULL(m.location,'')
                  ),
                  ';;'
                ) AS meetings_concat
            FROM sections s
            JOIN courses  c   ON c.course_id   = s.course_id
            JOIN subjects sub ON sub.subject_id = c.subject_id
            JOIN terms    t   ON t.term_id     = s.term_id
            LEFT JOIN meetings m ON m.section_id = s.section_id
            WHERE {where_sql}
            GROUP BY s.section_id
            ORDER BY t.year DESC, {_semester_sort_sql('t')}, sub.code, c.course_number, c.title, s.crn
            LIMIT ? OFFSET ?
        """

        cur = conn.cursor()
        total = cur.execute(count_sql, args).fetchone()[0]

        page_rows = cur.execute(data_sql, args + [limit, offset]).fetchall()
        cols = [d[0] for d in cur.description]
        items: List[Dict[str, Any]] = [dict(zip(cols, r)) for r in page_rows]

        # Parse meetings
        for r in items:
            r["meetings"] = []
            mc = (r.pop("meetings_concat") or "").strip()
            if mc:
                for chunk in mc.split(";;"):
                    d, st, et, b, room, loc = (chunk.split("|") + [""]*6)[:6]
                    r["meetings"].append({
                        "days": d or None,
                        "start_time": st or None,
                        "end_time": et or None,
                        "bldg": b or None,
                        "room": room or None,
                        "location": loc or None,
                    })

        # Instructors: include difficulty twice for compatibility
        if items:
            sec_ids = [r["section_id"] for r in items]
            qmarks = ",".join(["?"] * len(sec_ids))
            diff_select = ""
            if difficulty_col:
                diff_select = f", i.{difficulty_col} AS rmp_difficulty, i.{difficulty_col} AS rmp_avg_difficulty"

            inst_sql = f"""
                SELECT si.section_id,
                       i.instructor_id, i.name, i.netid, i.email,
                       i.rmp_id, i.rmp_url,
                       i.rmp_avg_rating, i.rmp_num_ratings
                       {diff_select}
                FROM section_instructors si
                JOIN instructors i ON i.instructor_id = si.instructor_id
                WHERE si.section_id IN ({qmarks})
                ORDER BY i.name
            """

            inst_rows = cur.execute(inst_sql, sec_ids).fetchall()
            icolumns = [d[0] for d in cur.description]
            by_sec: Dict[int, List[Dict[str, Any]]] = {}
            for row in inst_rows:
                d = dict(zip(icolumns, row))
                sid = d.pop("section_id")
                by_sec.setdefault(sid, []).append(d)
            for r in items:
                r["instructors"] = by_sec.get(r["section_id"], [])

        return jsonify({
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "difficulty_col_used": difficulty_col,
        })
    finally:
        conn.close()
