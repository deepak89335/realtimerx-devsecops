import pytest
import json
from app.app import app, db


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


def _add_drug(client, overrides=None):
    payload = {
        "name":        "Paracetamol 500mg",
        "batch_no":    "BATCH-001",
        "quantity":    50,
        "expiry_date": "2027-12-31",
        "supplier":    "MedSupply Co.",
        "unit":        "tablets",
    }
    if overrides:
        payload.update(overrides)
    return client.post("/api/drugs", json=payload)


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


# ── CRUD ──────────────────────────────────────────────────────────────────────

def test_add_drug(client):
    r = _add_drug(client)
    assert r.status_code == 201
    data = r.get_json()
    assert data["name"] == "Paracetamol 500mg"
    assert data["quantity"] == 50


def test_add_drug_missing_fields(client):
    r = client.post("/api/drugs", json={"name": "Amoxicillin"})
    assert r.status_code == 400


def test_add_drug_bad_date(client):
    r = _add_drug(client, {"expiry_date": "31-12-2027"})
    assert r.status_code == 400


def test_list_drugs_empty(client):
    r = client.get("/api/drugs")
    assert r.status_code == 200
    assert r.get_json() == []


def test_list_drugs(client):
    _add_drug(client)
    r = client.get("/api/drugs")
    assert len(r.get_json()) == 1


def test_get_drug(client):
    _add_drug(client)
    r = client.get("/api/drugs/1")
    assert r.status_code == 200
    assert r.get_json()["batch_no"] == "BATCH-001"


def test_get_drug_not_found(client):
    r = client.get("/api/drugs/999")
    assert r.status_code == 404


def test_update_stock(client):
    _add_drug(client)
    r = client.patch("/api/drugs/1", json={"quantity": 5})
    assert r.status_code == 200
    assert r.get_json()["quantity"] == 5


def test_delete_drug(client):
    _add_drug(client)
    r = client.delete("/api/drugs/1")
    assert r.status_code == 200
    assert client.get("/api/drugs/1").status_code == 404


# ── Alerts ────────────────────────────────────────────────────────────────────

def test_low_stock_alert(client):
    _add_drug(client, {"batch_no": "BATCH-LOW", "quantity": 3})
    r = client.get("/api/alerts/low-stock")
    assert r.status_code == 200
    body = r.get_json()
    assert body["count"] == 1
    assert body["drugs"][0]["batch_no"] == "BATCH-LOW"


def test_no_low_stock(client):
    _add_drug(client)   # quantity=50, above threshold
    r = client.get("/api/alerts/low-stock")
    assert r.get_json()["count"] == 0


def test_expiring_soon(client):
    from datetime import date, timedelta
    soon = (date.today() + timedelta(days=10)).isoformat()
    _add_drug(client, {"batch_no": "BATCH-EXP", "expiry_date": soon})
    r = client.get("/api/alerts/expiring-soon")
    assert r.get_json()["count"] == 1


def test_expired(client):
    _add_drug(client, {"batch_no": "BATCH-OLD", "expiry_date": "2020-01-01"})
    r = client.get("/api/alerts/expired")
    assert r.get_json()["count"] == 1
    assert r.get_json()["drugs"][0]["days_overdue"] > 0
