from flask import Blueprint, jsonify
import os, sqlite3
from ..db import get_conn_ro

meta_bp = Blueprint("meta", __name__)

@meta_bp.get("/health")
def health():
    return {"status": "ok"}

@meta_bp.get("/debug-db")
def debug_db():
    # reveal resolved path + size
    # (kept simple so you can sanity-check quickly)
    conn = get_conn_ro()
    path = conn.execute("PRAGMA database_list;").fetchone()[2]
    size = os.path.getsize(path) if os.path.exists(path) else 0
    conn.close()
    return {"db_path": path, "size_bytes": size}

@meta_bp.get("/schema")
def schema():
    """Return tables and their columns using PRAGMA."""
    conn = get_conn_ro()
    cur = conn.cursor()
    tables = cur.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    out = []
    for (tname,) in tables:
        cols = conn.execute(f"PRAGMA table_info('{tname}')").fetchall()
        out.append({
            "table": tname,
            "columns": [
                {"cid": c[0], "name": c[1], "type": c[2], "notnull": bool(c[3]), "default": c[4], "pk": c[5]}
                for c in cols
            ]
        })
    conn.close()
    return jsonify(out)
