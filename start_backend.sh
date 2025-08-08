#!/usr/bin/env bash
set -e
cd /Users/jonahballard/Downloads/CatBase
source backend/venv/bin/activate
export FRONTEND_ORIGIN="http://localhost:5173"   # or 3000; optional

# Run update scripts
python backend/scraper/fetch_current.py
python backend/scripts/clean_current.py
python backend/scripts/ingest_uvm_current.py

# Start backend
python -m backend.app
