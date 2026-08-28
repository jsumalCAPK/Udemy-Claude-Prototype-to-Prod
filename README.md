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
   - `http://localhost:3000/` — shows the app: the repo name as the title, the tech stack as a caption, a form to add a user (name + email), and the current list of users (auto-creates the `users` table on first load)
   - `http://localhost:3000/health/db` — a separate JSON endpoint confirming the app can read/write the SQLite database

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

- `test_index_shows_title_and_tech_stack` — hits `/` and checks the page title, tech-stack caption, and empty-state message.
- `test_add_user_appears_in_list` — posts a new user to `/users`, follows up with a `GET /`, and checks the user's name and email now appear in the list.
- `test_add_user_requires_name_and_email` — posts with a blank name and checks the user is not added.
- `test_health_db_returns_ok_with_timestamp` — hits `/health/db` once and checks it returns `status: ok`, a `dbTime`, and `totalChecks == 1`.
- `test_health_db_increments_across_requests` — hits `/health/db` twice and checks the count goes 1 → 2, proving state actually persists in SQLite across requests.
- `test_health_db_reports_error_for_unwritable_path` — points the DB path at a nonexistent directory and checks the route returns a 500 with `status: error`, proving the error-handling branch actually triggers.

## Notes

- The SQLite database file lives at `instance/radiocalico.db` (auto-created on first run, gitignored).
- Flask runs in debug mode with auto-reload, so editing `app.py` restarts the server automatically.
- To start fresh, just delete `instance/radiocalico.db` and restart the app — it will recreate the schema.
