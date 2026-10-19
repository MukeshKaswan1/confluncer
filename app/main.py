import asyncio
import logging
from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .db import Base, SessionLocal, engine
from .models import Transaction, utcnow
from .worker import run_worker

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    stop = asyncio.Event()
    task = asyncio.create_task(run_worker(stop))
    yield
    stop.set()
    await task


app = FastAPI(title="Transaction Webhook Service", lifespan=lifespan)


class WebhookPayload(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=128)
    source_account: str = Field(min_length=1, max_length=128)
    destination_account: str = Field(min_length=1, max_length=128)
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=1, max_length=8)


def _iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:  # SQLite drops tzinfo
        from datetime import timezone
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@app.get("/")
def health():
    return {"status": "HEALTHY", "current_time": _iso(utcnow())}


def _save(payload: WebhookPayload) -> None:
    with SessionLocal() as session:
        session.add(Transaction(**payload.model_dump()))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()  # duplicate transaction_id: already accepted, ignore


@app.post("/v1/webhooks/transactions", status_code=202)
async def receive_webhook(payload: WebhookPayload):
    # Persist only (fast); the worker does the delayed processing.
    await asyncio.to_thread(_save, payload)
    return {"status": "accepted", "transaction_id": payload.transaction_id}


@app.get("/v1/transactions/{transaction_id}")
def get_transaction(transaction_id: str):
    with SessionLocal() as session:
        rows = session.execute(
            select(Transaction).where(Transaction.transaction_id == transaction_id)
        ).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return [
        {
            "transaction_id": t.transaction_id,
            "source_account": t.source_account,
            "destination_account": t.destination_account,
            "amount": float(t.amount),
            "currency": t.currency,
            "status": t.status,
            "created_at": _iso(t.created_at),
            "processed_at": _iso(t.processed_at),
        }
        for t in rows
    ]
