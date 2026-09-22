from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from services.api.app.main import app
from services.common.config import SERVICE_VERSION

SERVICE_ERROR = "connection refused"


def test_health_live_reports_service(client):
    response = client.get("/health/live")

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "api"
    assert payload["status"] == "ok"


def test_health_ready_reports_database_dependency(client):
    response = client.get("/health/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["database"] == "ok"
    assert payload["version"] == SERVICE_VERSION


def test_health_ready_returns_503_when_database_probe_fails(client, db_session, monkeypatch):
    def failing_execute(*args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception(SERVICE_ERROR))

    monkeypatch.setattr(db_session, "execute", failing_execute)

    # The route handles the failure itself, so the client must observe the
    # 503 response rather than an unhandled server error.
    response = TestClient(app).get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["service"] == "api"
    assert payload["status"] == "unavailable"
    assert payload["error"] == "database"
