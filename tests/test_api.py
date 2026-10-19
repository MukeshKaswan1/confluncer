import os
import tempfile
import time

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/t.db"
os.environ["PROCESSING_DELAY_SECONDS"] = "1"
os.environ["WORKER_POLL_INTERVAL_SECONDS"] = "0.2"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

PAYLOAD = {
    "transaction_id": "txn_abc123def456",
    "source_account": "acc_user_789",
    "destination_account": "acc_merchant_456",
    "amount": 1500,
    "currency": "INR",
}


def test_health_and_idempotent_processing():
    with TestClient(app) as c:
        assert c.get("/").json()["status"] == "HEALTHY"
        for _ in range(3):
            start = time.time()
            r = c.post("/v1/webhooks/transactions", json=PAYLOAD)
            assert r.status_code == 202
            assert time.time() - start < 0.5
        rows = c.get(f"/v1/transactions/{PAYLOAD['transaction_id']}").json()
        assert len(rows) == 1 and rows[0]["status"] == "PROCESSING"
        assert rows[0]["processed_at"] is None
        time.sleep(2)
        rows = c.get(f"/v1/transactions/{PAYLOAD['transaction_id']}").json()
        assert len(rows) == 1 and rows[0]["status"] == "PROCESSED"
        assert rows[0]["processed_at"] is not None


def test_unknown_and_invalid():
    with TestClient(app) as c:
        assert c.get("/v1/transactions/nope").status_code == 404
        assert c.post("/v1/webhooks/transactions", json={"x": 1}).status_code == 422
