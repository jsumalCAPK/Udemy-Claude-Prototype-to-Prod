import os

import pytest

from app import app as flask_app


@pytest.fixture
def client(tmp_path):
    flask_app.config["DATABASE"] = os.path.join(tmp_path, "test.db")
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


def test_index_returns_ok(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "message": "radiocalico web server is running",
    }


def test_health_db_returns_ok_with_timestamp(client):
    response = client.get("/health/db")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["totalChecks"] == 1
    assert "dbTime" in body


def test_health_db_increments_across_requests(client):
    first = client.get("/health/db").get_json()
    second = client.get("/health/db").get_json()
    assert first["totalChecks"] == 1
    assert second["totalChecks"] == 2


def test_health_db_reports_error_for_unwritable_path(client, tmp_path):
    flask_app.config["DATABASE"] = os.path.join(tmp_path, "no_such_dir", "test.db")
    response = client.get("/health/db")
    assert response.status_code == 500
    assert response.get_json()["status"] == "error"
