# Transaction Webhook Service

FastAPI service that acknowledges payment webhooks immediately (202) and processes
them in the background after a 30-second simulated delay.

**Live URL:** `https://confluncer-nine.vercel.app/`

## Endpoints
| Method | Path | Notes |
|---|---|---|
| GET | `/` | `{"status":"HEALTHY","current_time":"..."}` |
| POST | `/v1/webhooks/transactions` | Returns `202`; idempotent on `transaction_id` |
| GET | `/v1/transactions/{transaction_id}` | Returns a list with status `PROCESSING` / `PROCESSED`; 404 if unknown |

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # uses SQLite by default
or Postgres:
DATABASE_URL=
```

## Technical choices
- **FastAPI**: async, fast, built-in validation.
- **Postgres (any cloud, e.g. Neon) via SQLAlchemy**; SQLite fallback for local dev.
- **Idempotency**: `transaction_id` is the primary key. Duplicate inserts hit an `IntegrityError` that is swallowed, so repeats return 202 and create no extra row or processing.
- **Fast ack**: the handler only does one small insert; the 30s work never blocks a request.
- **Reliable background processing**: instead of in-memory timers, the row is saved as `PROCESSING` and a worker loop polls the DB for rows older than 30s and marks them `PROCESSED`. Pending work survives restarts/crashes, nothing is lost, and `FOR UPDATE SKIP LOCKED` makes it safe to run multiple instances.
- Config via env: `DATABASE_URL`, `PROCESSING_DELAY_SECONDS` (30), `WORKER_POLL_INTERVAL_SECONDS` (1).
