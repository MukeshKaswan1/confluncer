"""Durable background processor.

The webhook handler only persists a PROCESSING row. This worker polls the DB for
rows older than the processing delay and marks them PROCESSED. Because state lives
in the DB (not in memory), pending transactions survive restarts/crashes, and
FOR UPDATE SKIP LOCKED (Postgres) lets several instances share the work safely.
"""
import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select

from . import config
from .db import SessionLocal
from .models import Transaction, utcnow

log = logging.getLogger("worker")


def process_due_transactions() -> int:
    cutoff = utcnow() - timedelta(seconds=config.PROCESSING_DELAY_SECONDS)
    with SessionLocal() as session:
        stmt = (
            select(Transaction)
            .where(Transaction.status == "PROCESSING", Transaction.created_at <= cutoff)
            .limit(100)
            .with_for_update(skip_locked=True)  # no-op on SQLite
        )
        rows = session.execute(stmt).scalars().all()
        for txn in rows:
            txn.status = "PROCESSED"
            txn.processed_at = utcnow()
        session.commit()
        return len(rows)


async def run_worker(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            n = await asyncio.to_thread(process_due_transactions)
            if n:
                log.info("processed %d transaction(s)", n)
        except Exception:
            log.exception("worker iteration failed; will retry")
        try:
            await asyncio.wait_for(stop.wait(), timeout=config.WORKER_POLL_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            pass
