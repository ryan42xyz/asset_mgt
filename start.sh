#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

echo "Starting dependencies (Postgres + Redis)..."
docker-compose up -d

echo "Waiting for Postgres to be ready..."
until docker-compose exec -T postgres pg_isready -U postgres -q 2>/dev/null; do
  sleep 1
done

echo "Starting API server on http://localhost:8000 ..."
# Load .env if present (export all vars)
if [ -f .env ]; then
  set -a; source .env; set +a
fi
venv/bin/uvicorn app.main:app --reload --port 8000
