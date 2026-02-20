# Election Manager

Full-stack election/voting management system.

## Stack
- Backend: FastAPI + SQLAlchemy
- Frontend: React + TypeScript + Vite

## Local Development

### Backend
1. Create env file (optional for dev): `backend/.env` or repo `.env`
2. Install deps: `pip install -r backend/requirements.txt`
3. Run: `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000` (from `backend/`)

### Telegram Bot Runner
Run the polling bot runner (from `backend/`):

`python bot_runner.py`

### Frontend
1. Install deps: `npm install` (from `frontend/`)
2. Run dev server: `npm run dev`

Frontend: http://127.0.0.1:5173
Backend: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs

## Share on the Internet (Quick Testing)

For a step-by-step guide (Windows-friendly) to run the panel + bot and share a public URL via Cloudflare Tunnel or ngrok, see:

- [RUN_PUBLIC.md](RUN_PUBLIC.md)

## Production Notes (Security)

### Required environment variables
- `APP_ENV=production`
- `SECRET_KEY` (strong random, >= 32 chars)
- `REFRESH_SECRET_KEY` (strong random, >= 32 chars)
- `DATABASE_URL` (recommend Postgres for production)
- `CORS_ALLOW_ORIGINS` (comma-separated list of allowed origins)

### Reverse proxy
Run the backend behind Nginx/Caddy with HTTPS enabled.

### Rate limiting
The API includes a minimal in-memory rate limiter for auth endpoints. For multi-worker production,
use a shared store (e.g. Redis) or a reverse-proxy rate limit.

## Production Notes (High Load)

### Key constraints
- For a single Telegram bot token, you must run only one polling process at a time (Telegram will return conflicts if you run multiple pollers for the same token).
- If you expect high write volume, SQLite can become a bottleneck. Prefer PostgreSQL for real production loads.

### Backend API (multi-worker)
Use a multi-worker server (Gunicorn + Uvicorn workers). A sample systemd unit is included at `deploy/systemd/election-api.service`.

Suggested environment variables:
- `DATABASE_URL` (Postgres recommended)
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT_SEC` (non-SQLite engine pooling)

### Telegram bot runner throughput
The bot runner supports higher throughput by processing updates concurrently and by increasing the Telegram HTTP connection pool.

Environment variables:
- `BOT_CONCURRENT_UPDATES` (default 64; example 128)
- `TELEGRAM_CONNECTION_POOL_SIZE` (default 32; example 64)

A sample systemd unit is included at `deploy/systemd/election-bot-runner.service`.

### SQLite tuning (if you must use SQLite)
When using SQLite, the backend enables WAL mode and uses a configurable busy timeout.

Environment variables:
- `SQLITE_BUSY_TIMEOUT_SEC` (default 30)
