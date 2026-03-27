# Agent Guide (toys/asset_mgt)

This folder is a small FastAPI service plus static HTML pages. It expects Postgres + Redis (via Docker Compose) and runs an API server on port 8000.

Note: `README.md` is currently empty; treat code + scripts as the source of truth.

## Commands (Run/Test)

Run commands from `toys/asset_mgt/`.

- Python env
  - If the checked-in `venv/` works for you: `source venv/bin/activate`
  - Otherwise:
    - `python3 -m venv venv`
    - `source venv/bin/activate`
    - `python3 -m pip install -r requirements.txt`

- Start dependencies
  - `docker-compose up -d`
  - Services from `docker-compose.yml`:
    - Postgres: `localhost:5432` (db `assetmgmt`, user `postgres`, password `password`)
    - Redis: `localhost:6379`

- Run API server
  - `venv/bin/uvicorn app.main:app --reload --port 8000`
  - Convenience script: `./start.sh` (starts compose + uvicorn)

- Useful URLs
  - API docs: `http://localhost:8000/docs`
  - Health: `http://localhost:8000/health`
  - Static UI: `http://localhost:8000/` or `http://localhost:8000/static/index.html`

- Tests
  - System-style script: `venv/bin/python3 test_system.py`

## Project Layout

- `app/main.py`: FastAPI app (`app.main:app`), mounts `/static`, serves pages
- `app/api/`: routers under `/api/v1/*`
- `app/database/`: DB/Redis clients
- `app/models/`: SQLAlchemy models
- `app/services/`: market/strategy/OCR services
- `app/static/`: `index.html`, `spy_dashboard.html`, `fire_calc.html`
- `docker-compose.yml`: Postgres + Redis
- `start.sh`: local dev convenience

## Gotchas / Safety

- Run uvicorn from `toys/asset_mgt/` so `StaticFiles(directory="app/static")` resolves.
- There is a committed `.env`, `app.db`, `output.log`, and a committed `venv/`.
  - Treat `.env` as sensitive; do not copy secrets into issues/PRs.
  - Avoid committing changes inside `venv/`, local DBs, and logs unless explicitly intended.
- No repo-pinned linter/formatter is configured; keep diffs minimal and local to this project.
