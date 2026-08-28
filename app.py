import os
import subprocess
import sqlite3
import sys
from datetime import datetime, timezone
from importlib.metadata import version as pkg_version

from flask import Flask, g, jsonify, redirect, render_template, request, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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
    db.commit()


@app.route("/")
def index():
    init_db()
    db = get_db()
    users = db.execute(
        "SELECT name, email, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    return render_template(
        "index.html", repo_name=REPO_NAME, tech_stack=TECH_STACK, users=users
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
    return redirect(url_for("index"))


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
