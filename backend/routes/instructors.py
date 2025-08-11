# backend/routes/instructors.py
from __future__ import annotations

from flask import Blueprint, request, jsonify, abort
from typing import Any, Dict, List, Optional
import json

# Reuse your project's DB helper. If your app uses a different import path,
# adjust this import to match (e.g., from app.db import get_conn_ro).
from ..db import get_conn_ro

instructors_bp = Blueprint("instructors", __name__)

# ------------------------- helpers -------------------------

def _row_to_dict(cur, row):
    """sqlite row -> dict helper."""
    return {d[0]: row[i] for i, d in enumerate(cur.description)}

def _parse_json_safe(txt: Optional[str]):
    if not txt:
        return None
    try:
        return json.loads(txt)
    except Exception:
        return None

def _row_to_instructor_basic(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "instructor_id": r["instructor_id"],
        "name": r["name"],
        "netid": r.get("netid"),
        "email": r.get("email"),
    }

def _row_to_rmp(r: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rmp_id": r.get("rmp_id"),
        "rmp_url": r.get("rmp_url"),
        "avg_rating": r.get("rmp_avg_rating"),
        "num_ratings": r.get("rmp_num_ratings"),
        "would_take_again": r.get("rmp_would_take_again"),
        "difficulty": r.get("rmp_difficulty"),
        "top_tags": _parse_json_safe(r.get("rmp_top_tags_json")) or [],
        "rating_distribution": _parse_json_safe(r.get("rmp_rating_distribution_json")) or {},
        "last_refreshed": r.get("rmp_last_refreshed"),
    }

def _build_where_and_params() -> tuple[str, List[Any]]:
    """
    Build WHERE clause from query params.
    Supported filters:
      - search: substring match on instructor name
      - has_rmp=1: only rows with an RMP ID
      - rmp_min_rating: float (>=)
      - rmp_min_count: int (>=)
      - rmp_max_difficulty: float (<=)
    """
    where = []
    params: List[Any] = []

    search = (request.args.get("search") or "").strip()
    has_rmp = request.args.get("has_rmp")
    rmp_min_rating = request.args.get("rmp_min_rating", type=float)
    rmp_min_count = request.args.get("rmp_min_count", type=int)
    rmp_max_difficulty = request.args.get("rmp_max_difficulty", type=float)

    if search:
        where.append("i.name LIKE ?")
        params.append(f"%{search}%")

    if has_rmp in ("1", "true", "True"):
        where.append("i.rmp_id IS NOT NULL")

    if rmp_min_rating is not None:
        where.append("i.rmp_avg_rating >= ?")
        params.append(rmp_min_rating)

    if rmp_min_count is not None:
        where.append("i.rmp_num_ratings >= ?")
        params.append(rmp_min_count)

    if rmp_max_difficulty is not None:
        where.append("i.rmp_difficulty <= ?")
        params.append(rmp_max_difficulty)

    where_sql = " AND ".join(where) if where else "1=1"
    return where_sql, params

def _build_order_by() -> str:
    """
    Sorting:
      - sort=name|avg_rating|num_ratings|difficulty (default: name)
      - dir=asc|desc (default: asc for name; desc for numeric fields)
    """
    sort = (request.args.get("sort") or "name").lower()
    direction = (request.args.get("dir") or "").lower()

    if sort == "avg_rating":
        # default desc: highest rating first
        dir_sql = "ASC" if direction == "asc" else "DESC"
        # Put NULLs last
        return f"CASE WHEN i.rmp_avg_rating IS NULL THEN 1 ELSE 0 END, i.rmp_avg_rating {dir_sql}, i.rmp_num_ratings DESC, i.name"

    if sort == "num_ratings":
        dir_sql = "ASC" if direction == "asc" else "DESC"
        return f"CASE WHEN i.rmp_num_ratings IS NULL THEN 1 ELSE 0 END, i.rmp_num_ratings {dir_sql}, i.rmp_avg_rating DESC, i.name"

    if sort == "difficulty":
        # default asc: easiest first (lower difficulty)
        dir_sql = "DESC" if direction == "desc" else "ASC"
        return f"CASE WHEN i.rmp_difficulty IS NULL THEN 1 ELSE 0 END, i.rmp_difficulty {dir_sql}, i.rmp_avg_rating DESC, i.rmp_num_ratings DESC, i.name"

    # name (default)
    dir_sql = "DESC" if direction == "desc" else "ASC"
    return f"i.name {dir_sql}"

# ------------------------- routes -------------------------

@instructors_bp.get("/instructors")
def list_instructors():
    """
    List instructors with optional RMP payload.

    Query params:
      - search               : substring match on name
      - limit (default 50)   : page size
      - offset (default 0)   : pagination offset
      - include_rmp=1        : include full RMP block per instructor
      - has_rmp=1            : only with RMP attached
      - rmp_min_rating       : float (>=)
      - rmp_min_count        : int (>=)
      - rmp_max_difficulty   : float (<=)
      - sort                 : name | avg_rating | num_ratings | difficulty
      - dir                  : asc | desc
    """
    include_rmp = request.args.get("include_rmp") in ("1", "true", "True")
    limit = request.args.get("limit", type=int) or 50
    offset = request.args.get("offset", type=int) or 0

    where_sql, params = _build_where_and_params()
    order_sql = _build_order_by()

    conn = get_conn_ro()
    conn.row_factory = _row_to_dict
    cur = conn.cursor()

    cur.execute(f"""
        SELECT
            i.instructor_id, i.name, i.netid, i.email,
            i.rmp_id, i.rmp_url, i.rmp_avg_rating, i.rmp_num_ratings,
            i.rmp_would_take_again, i.rmp_difficulty,
            i.rmp_top_tags_json, i.rmp_rating_distribution_json,
            i.rmp_last_refreshed
        FROM instructors i
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT ? OFFSET ?
    """, params + [limit, offset])
    rows = cur.fetchall()

    # Optional: total count for pagination
    cur.execute(f"SELECT COUNT(*) as cnt FROM instructors i WHERE {where_sql}", params)
    total = cur.fetchone()["cnt"]

    conn.close()

    out = []
    for r in rows:
        item = _row_to_instructor_basic(r)
        if include_rmp:
            item["rmp"] = _row_to_rmp(r)
        else:
            # light preview fields for list cards
            item["rmp_avg_rating"] = r.get("rmp_avg_rating")
            item["rmp_num_ratings"] = r.get("rmp_num_ratings")
            item["rmp_difficulty"] = r.get("rmp_difficulty")
        out.append(item)

    return jsonify({
        "total": total,
        "count": len(out),
        "items": out,
    })

@instructors_bp.get("/instructors/<int:instructor_id>")
def get_instructor(instructor_id: int):
    """
    Instructor detail. Add ?include_rmp=1 to embed the RMP payload.
    """
    include_rmp = request.args.get("include_rmp") in ("1", "true", "True")

    conn = get_conn_ro()
    conn.row_factory = _row_to_dict
    cur = conn.cursor()
    cur.execute("""
        SELECT i.*
        FROM instructors i
        WHERE i.instructor_id = ?
    """, (instructor_id,))
    r = cur.fetchone()
    conn.close()

    if not r:
        abort(404, description="instructor not found")

    data = _row_to_instructor_basic(r)
    if include_rmp:
        data["rmp"] = _row_to_rmp(r)
    else:
        data["rmp_avg_rating"] = r.get("rmp_avg_rating")
        data["rmp_num_ratings"] = r.get("rmp_num_ratings")
        data["rmp_difficulty"] = r.get("rmp_difficulty")
    return jsonify(data)

@instructors_bp.get("/instructors/<int:instructor_id>/rmp")
def get_instructor_rmp(instructor_id: int):
    """
    RMP-only payload. Handy for lazy-loading on the details page.
    """
    conn = get_conn_ro()
    conn.row_factory = _row_to_dict
    cur = conn.cursor()
    cur.execute("""
        SELECT
            i.rmp_id, i.rmp_url, i.rmp_avg_rating, i.rmp_num_ratings,
            i.rmp_would_take_again, i.rmp_difficulty,
            i.rmp_top_tags_json, i.rmp_rating_distribution_json,
            i.rmp_last_refreshed
        FROM instructors i
        WHERE i.instructor_id = ?
    """, (instructor_id,))
    r = cur.fetchone()
    conn.close()

    if not r:
        abort(404, description="instructor not found")

    return jsonify(_row_to_rmp(r))
