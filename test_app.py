import os

import pytest

from app import app as flask_app, REPO_NAME, TECH_STACK


@pytest.fixture
def client(tmp_path):
    flask_app.config["DATABASE"] = os.path.join(tmp_path, "test.db")
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


def test_index_shows_title_and_tech_stack(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert f"<title>{REPO_NAME}</title>" in body
    assert TECH_STACK in body
    assert "No users yet." in body


def test_add_user_appears_in_list(client):
    response = client.post(
        "/users", data={"name": "Ada Lovelace", "email": "ada@example.com"}
    )
    assert response.status_code == 302

    body = client.get("/").get_data(as_text=True)
    assert "Ada Lovelace" in body
    assert "ada@example.com" in body
    assert "No users yet." not in body


def test_add_user_requires_name_and_email(client):
    client.post("/users", data={"name": "", "email": "no-name@example.com"})
    body = client.get("/").get_data(as_text=True)
    assert "no-name@example.com" not in body
    assert "No users yet." in body


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
