import os
import subprocess
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from importlib.metadata import version as pkg_version

from flask import (
    Flask,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STREAM_URL = "https://d3d4yli4hf5bmh.cloudfront.net/hls/live.m3u8"

SEED_TRACKS = [
    {
        "artist": "Shandi Sinnamon",
        "title": "He's A Dream (1983)",
        "album": "Flashdance (Original Motion Picture Soundtrack)",
        "source_quality": "16-bit 44.1kHz",
        "stream_quality": "48kHz FLAC / HLS Lossless",
    },
    {"artist": "TLC", "title": "Ain't 2 Proud 2 Beg"},
    {"artist": "The Raconteurs", "title": "Steady, As She Goes"},
    {"artist": "Mick Jagger", "title": "Just Another Night"},
    {"artist": "Beyoncé", "title": "Irreplaceable (Album Version)"},
    {"artist": "Etta James", "title": "I'd Rather Go Blind"},
]


def _detect_repo_name():
    try:
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=BASE_DIR, text=True
        ).strip()
        name = url.rstrip("/").split("/")[-1]
        return name[:-4] if name.endswith(".git") else name
    except (subprocess.CalledProcessError, FileNotFoundError):
        return os.path.basename(BASE_DIR)


REPO_NAME = _detect_repo_name()
TECH_STACK = f"Python {sys.version.split()[0]} · Flask {pkg_version('flask')} · SQLite"

app = Flask(__name__)
app.config["DATABASE"] = os.path.join(app.instance_path, "radiocalico.db")
app.secret_key = "dev-only-secret-do-not-use-in-production"

os.makedirs(app.instance_path, exist_ok=True)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS health_check (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checked_at TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            artist TEXT NOT NULL,
            title TEXT NOT NULL,
            album TEXT,
            source_quality TEXT,
            stream_quality TEXT,
            played_at TEXT NOT NULL
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS track_ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL REFERENCES tracks(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
            rated_at TEXT NOT NULL,
            UNIQUE (track_id, user_id)
        )
        """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS track_plays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL REFERENCES tracks(id),
            user_id INTEGER REFERENCES users(id),
            played_at TEXT NOT NULL
        )
        """
    )
    db.commit()

    if db.execute("SELECT COUNT(*) AS count FROM tracks").fetchone()["count"] == 0:
        now = datetime.now(timezone.utc)
        for offset, track in enumerate(SEED_TRACKS):
            db.execute(
                """
                INSERT INTO tracks (artist, title, album, source_quality, stream_quality, played_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    track["artist"],
                    track["title"],
                    track.get("album"),
                    track.get("source_quality"),
                    track.get("stream_quality"),
                    (now - timedelta(minutes=offset)).isoformat(),
                ),
            )
        db.commit()


def current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    db = get_db()
    return db.execute(
        "SELECT id, name, email FROM users WHERE id = ?", (user_id,)
    ).fetchone()


@app.route("/demo")
def demo():
    init_db()
    db = get_db()
    users = db.execute(
        "SELECT name, email, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    return render_template(
        "demo.html", repo_name=REPO_NAME, tech_stack=TECH_STACK, users=users
    )


@app.route("/users", methods=["POST"])
def add_user():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    if name and email:
        init_db()
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, created_at) VALUES (?, ?, ?)",
            (name, email, datetime.now(timezone.utc).isoformat()),
        )
        db.commit()
    return redirect(url_for("demo"))


@app.route("/")
def index():
    init_db()
    db = get_db()
    recent = db.execute(
        "SELECT * FROM tracks ORDER BY played_at DESC LIMIT 6"
    ).fetchall()
    now_playing = recent[0] if recent else None
    previous_tracks = recent[1:]

    rating_counts = {"up": 0, "down": 0}
    user_rating = None
    if now_playing is not None:
        for row in db.execute(
            "SELECT rating, COUNT(*) AS count FROM track_ratings "
            "WHERE track_id = ? GROUP BY rating",
            (now_playing["id"],),
        ):
            rating_counts[row["rating"]] = row["count"]

        me = current_user()
        if me is not None:
            existing = db.execute(
                "SELECT rating FROM track_ratings WHERE track_id = ? AND user_id = ?",
                (now_playing["id"], me["id"]),
            ).fetchone()
            user_rating = existing["rating"] if existing else None

    users = db.execute("SELECT id, name FROM users ORDER BY name").fetchall()

    return render_template(
        "index.html",
        repo_name=REPO_NAME,
        tech_stack=TECH_STACK,
        stream_url=STREAM_URL,
        now_playing=now_playing,
        previous_tracks=previous_tracks,
        rating_counts=rating_counts,
        user_rating=user_rating,
        users=users,
        current_user=current_user(),
    )


@app.route("/whoami", methods=["POST"])
def whoami():
    user_id = request.form.get("user_id", "").strip()
    if user_id:
        session["user_id"] = int(user_id)
    return redirect(url_for("index"))


@app.route("/tracks/<int:track_id>/rate", methods=["POST"])
def rate_track(track_id):
    direction = request.form.get("direction")
    me = current_user()
    if me is not None and direction in ("up", "down"):
        db = get_db()
        db.execute(
            """
            INSERT INTO track_ratings (track_id, user_id, rating, rated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (track_id, user_id)
            DO UPDATE SET rating = excluded.rating, rated_at = excluded.rated_at
            """,
            (track_id, me["id"], direction, datetime.now(timezone.utc).isoformat()),
        )
        db.commit()
    return redirect(url_for("index"))


@app.route("/tracks/<int:track_id>/play", methods=["POST"])
def log_play(track_id):
    me = current_user()
    db = get_db()
    db.execute(
        "INSERT INTO track_plays (track_id, user_id, played_at) VALUES (?, ?, ?)",
        (track_id, me["id"] if me else None, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()
    return ("", 204)


@app.route("/health/db")
def health_db():
    try:
        db = get_db()
        init_db()
        now = datetime.now(timezone.utc).isoformat()
        db.execute("INSERT INTO health_check (checked_at) VALUES (?)", (now,))
        db.commit()
        row = db.execute(
            "SELECT COUNT(*) AS count FROM health_check"
        ).fetchone()
        return jsonify(status="ok", dbTime=now, totalChecks=row["count"])
    except sqlite3.Error as err:
        return jsonify(status="error", message=str(err)), 500


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=3000, debug=True)
