import os
import sqlite3

import pytest

from app import app as flask_app, REPO_NAME, STREAM_URL, TECH_STACK


@pytest.fixture
def db_path(tmp_path):
    return os.path.join(tmp_path, "test.db")


@pytest.fixture
def client(db_path):
    flask_app.config["DATABASE"] = db_path
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


def add_user(client, name, email):
    client.post("/users", data={"name": name, "email": email})


def user_id_for(db_path, email):
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row[0]


def now_playing_id(db_path):
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT id FROM tracks ORDER BY played_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row[0]


def ratings_for(db_path, track_id):
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT user_id, rating FROM track_ratings WHERE track_id = ?", (track_id,)
    ).fetchall()
    conn.close()
    return rows


def become(client, db_path, email):
    client.post("/whoami", data={"user_id": user_id_for(db_path, email)})


def test_demo_shows_title_and_tech_stack(client):
    response = client.get("/demo")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert f"<title>{REPO_NAME}</title>" in body
    assert TECH_STACK in body
    assert "No users yet." in body


def test_add_user_appears_in_demo_list(client):
    response = client.post(
        "/users", data={"name": "Ada Lovelace", "email": "ada@example.com"}
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/demo"

    body = client.get("/demo").get_data(as_text=True)
    assert "Ada Lovelace" in body
    assert "ada@example.com" in body
    assert "No users yet." not in body


def test_add_user_requires_name_and_email(client):
    client.post("/users", data={"name": "", "email": "no-name@example.com"})
    body = client.get("/demo").get_data(as_text=True)
    assert "no-name@example.com" not in body
    assert "No users yet." in body


def test_index_shows_station_and_stream(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Radio Calico" in body
    assert STREAM_URL in body
    assert 'id="play-pause"' in body


def test_index_shows_seeded_now_playing_and_previous_tracks(client):
    body = client.get("/").get_data(as_text=True)
    assert "Shandi Sinnamon" in body
    assert "He&#39;s A Dream (1983)" in body or "He's A Dream (1983)" in body
    assert "TLC" in body
    assert "Etta James" in body


def test_rate_without_identity_does_not_persist(client, db_path):
    client.get("/")
    track_id = now_playing_id(db_path)
    client.post(f"/tracks/{track_id}/rate", data={"direction": "up"})
    assert ratings_for(db_path, track_id) == []


def test_rate_with_identity_persists_and_shows_count(client, db_path):
    add_user(client, "Ada Lovelace", "ada@example.com")
    become(client, db_path, "ada@example.com")

    track_id = now_playing_id(db_path)
    client.post(f"/tracks/{track_id}/rate", data={"direction": "up"})

    rows = ratings_for(db_path, track_id)
    assert len(rows) == 1
    assert rows[0][1] == "up"

    body = client.get("/").get_data(as_text=True)
    assert "👍 1" in body


def test_rerating_replaces_rather_than_duplicates(client, db_path):
    add_user(client, "Ada Lovelace", "ada@example.com")
    become(client, db_path, "ada@example.com")
    track_id = now_playing_id(db_path)

    client.post(f"/tracks/{track_id}/rate", data={"direction": "up"})
    client.post(f"/tracks/{track_id}/rate", data={"direction": "down"})

    rows = ratings_for(db_path, track_id)
    assert len(rows) == 1
    assert rows[0][1] == "down"


def test_multiple_users_rate_independently(client, db_path):
    add_user(client, "Ada Lovelace", "ada@example.com")
    add_user(client, "Grace Hopper", "grace@example.com")
    track_id = now_playing_id(db_path)

    become(client, db_path, "ada@example.com")
    client.post(f"/tracks/{track_id}/rate", data={"direction": "up"})

    become(client, db_path, "grace@example.com")
    client.post(f"/tracks/{track_id}/rate", data={"direction": "down"})

    rows = {user: rating for user, rating in ratings_for(db_path, track_id)}
    assert len(rows) == 2

    body = client.get("/").get_data(as_text=True)
    assert "👍 1" in body
    assert "👎 1" in body


def test_log_play_records_anonymous_and_identified(client, db_path):
    client.get("/")
    track_id = now_playing_id(db_path)

    response = client.post(f"/tracks/{track_id}/play")
    assert response.status_code == 204

    add_user(client, "Ada Lovelace", "ada@example.com")
    become(client, db_path, "ada@example.com")
    client.post(f"/tracks/{track_id}/play")

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT user_id FROM track_plays WHERE track_id = ?", (track_id,)
    ).fetchall()
    conn.close()
    assert len(rows) == 2
    assert rows[0][0] is None
    assert rows[1][0] is not None


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
