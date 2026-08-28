# radiocalico

Local prototyping environment: Python/Flask web server + SQLite database. No Docker, no separate DB server to install — everything runs from a single Python virtual environment.

## Prerequisites

- Python 3.11+ (already verified present on this machine).

## Setup

1. Create and activate a virtual environment:
   ```
   python -m venv .venv

   # PowerShell / cmd.exe
   .venv\Scripts\activate

   # Git Bash
   source .venv/Scripts/activate
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the server:
   ```
   python app.py
   ```
4. Verify:
   - `http://localhost:3000/` — web server health check
   - `http://localhost:3000/health/db` — confirms the app can read/write the SQLite database

## Tests

Install dev dependencies and run the suite from the terminal:
```
# PowerShell / cmd.exe
.venv\Scripts\activate

# Git Bash
source .venv/Scripts/activate

pip install -r requirements-dev.txt
pytest
```
Or without activating the venv first: `.venv\Scripts\python.exe -m pytest -v` from the repo root.

`test_app.py` covers `app.py` using Flask's test client, each test against its own temporary SQLite file (never `instance/radiocalico.db`):

- `test_index_returns_ok` — hits `/` and checks the exact JSON body.
- `test_health_db_returns_ok_with_timestamp` — hits `/health/db` once and checks it returns `status: ok`, a `dbTime`, and `totalChecks == 1`.
- `test_health_db_increments_across_requests` — hits `/health/db` twice and checks the count goes 1 → 2, proving state actually persists in SQLite across requests.
- `test_health_db_reports_error_for_unwritable_path` — points the DB path at a nonexistent directory and checks the route returns a 500 with `status: error`, proving the error-handling branch actually triggers.

## Notes

- The SQLite database file lives at `instance/radiocalico.db` (auto-created on first run, gitignored).
- Flask runs in debug mode with auto-reload, so editing `app.py` restarts the server automatically.
- To start fresh, just delete `instance/radiocalico.db` and restart the app — it will recreate the schema.
