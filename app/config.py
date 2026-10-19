import os

# Postgres URL for production (e.g. Neon/Supabase/Render); SQLite fallback for local dev.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./transactions.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

PROCESSING_DELAY_SECONDS = float(os.getenv("PROCESSING_DELAY_SECONDS", "30"))
WORKER_POLL_INTERVAL_SECONDS = float(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "1"))
