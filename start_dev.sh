#!/usr/bin/env bash
set -euo pipefail

# Resolve repo root no matter where you run this from
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# ---- Python venv + CORS origin ----
if [[ ! -d "$BACKEND/venv" ]]; then
  echo "❌ Missing backend/venv. Create it and install deps first."
  echo "   python -m venv backend/venv && source backend/venv/bin/activate && pip install -r backend/requirements.txt"
  exit 1
fi
source "$BACKEND/venv/bin/activate"

# Default CORS origin for dev if not set
export FRONTEND_ORIGIN="${FRONTEND_ORIGIN:-http://localhost:5173}"

# ---- Update data (fetch → clean → ingest) ----
echo "📥 Fetching current data…"
if [[ -f "$BACKEND/scraper/fetch_current.py" ]]; then
  python "$BACKEND/scraper/fetch_current.py"
else
  echo "⚠️  Skipping fetch (not found: backend/scraper/fetch_current.py)"
fi

echo "🧹 Cleaning…"
if [[ -f "$BACKEND/scripts/clean_current.py" ]]; then
  python "$BACKEND/scripts/clean_current.py"
else
  echo "⚠️  Skipping clean (not found: backend/scripts/clean_current.py)"
fi

echo "📦 Ingesting into SQLite…"
# Adjust to your actual ingest filename; you mentioned ingest_uvm_current.py
if [[ -f "$BACKEND/scripts/ingest_uvm_current.py" ]]; then
  python "$BACKEND/scripts/ingest_uvm_current.py"
elif [[ -f "$BACKEND/scripts/ingest_current.py" ]]; then
  python "$BACKEND/scripts/ingest_current.py"
else
  echo "⚠️  Skipping ingest (not found: backend/scripts/ingest_uvm_current.py or ingest_current.py)"
fi

# ---- Start backend (background) ----
echo "🚀 Starting backend on http://127.0.0.1:5001 …"
python -m backend.app & 
BACKEND_PID=$!

# Ensure backend is cleaned up when we exit
cleanup() {
  echo ""
  echo "🛑 Stopping backend (PID $BACKEND_PID)…"
  kill "$BACKEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ---- Start frontend (foreground) ----
if [[ ! -d "$FRONTEND" ]]; then
  echo "❌ Missing frontend directory at $FRONTEND"
  exit 1
fi

cd "$FRONTEND"

# Install node deps if needed
if [[ ! -d "node_modules" ]]; then
  echo "📦 Installing frontend dependencies…"
  npm install
fi

echo "🌐 Starting frontend on http://localhost:5173 …"
echo "   (CORS allowed origin: $FRONTEND_ORIGIN)"
npm run dev
