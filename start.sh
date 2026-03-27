#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

# Load .env if present
if [ -f .env ]; then
  set -a; source .env; set +a
fi

echo "Starting Asset Management Platform..."
echo "Dashboard: http://localhost:8000"
echo "Data:      ./app.db  (SQLite, persists locally)"
echo ""

venv/bin/uvicorn app.main:app --reload --port 8000
