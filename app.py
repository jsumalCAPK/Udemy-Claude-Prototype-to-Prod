import os
import sqlite3
from datetime import datetime, timezone

from flask import Flask, g, jsonify

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
    db.commit()


@app.route("/")
def index():
    return jsonify(status="ok", message="radiocalico web server is running")


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
