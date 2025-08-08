from flask import Blueprint, jsonify
from ..db import get_conn_ro

health_bp = Blueprint("health", __name__)

@health_bp.get("/health")
def health():
    return jsonify({"status": "ok"})

@health_bp.get("/ping-db")
def ping_db():
    try:
        conn = get_conn_ro()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return jsonify({"status": "ok", "db": "reachable"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
