# Transaction Webhook Service

FastAPI service that acknowledges payment webhooks immediately (202) and processes
them in the background after a 30-second simulated delay.

**Live URL:** `<paste deployed URL here>`

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
# or with Postgres:
DATABASE_URL=postgresql://user:pass@host/db uvicorn app.main:app
```

## Test
```bash
pytest                                  # automated (uses a 1s delay)

curl -X POST localhost:8000/v1/webhooks/transactions -H 'Content-Type: application/json' \
  -d '{"transaction_id":"txn_abc123def456","source_account":"acc_user_789","destination_account":"acc_merchant_456","amount":1500,"currency":"INR"}'
# send it several times, then:
curl localhost:8000/v1/transactions/txn_abc123def456   # PROCESSING, then PROCESSED after ~30s
```

## Technical choices
- **FastAPI**: async, fast, built-in validation.
- **Postgres (any cloud, e.g. Neon/Supabase/Render) via SQLAlchemy**; SQLite fallback for local dev. Set `DATABASE_URL`.
- **Idempotency**: `transaction_id` is the primary key. Duplicate inserts hit an `IntegrityError` that is swallowed, so repeats return 202 and create no extra row or processing.
- **Fast ack**: the handler only does one small insert; the 30s work never blocks a request.
- **Reliable background processing**: instead of in-memory timers, the row is saved as `PROCESSING` and a worker loop polls the DB for rows older than 30s and marks them `PROCESSED`. Pending work survives restarts/crashes, nothing is lost, and `FOR UPDATE SKIP LOCKED` makes it safe to run multiple instances.
- Config via env: `DATABASE_URL`, `PROCESSING_DELAY_SECONDS` (30), `WORKER_POLL_INTERVAL_SECONDS` (1).

## Deploy (Render example)
Push to GitHub, create a Render Web Service from the repo (`render.yaml` included) and a free Postgres (Neon/Render), then set `DATABASE_URL`.
