# radiocalico

Local prototyping environment: Python/Flask web server + SQLite database. No Docker, no separate DB server to install — everything runs from a single Python virtual environment.

## Prerequisites

- Python 3.11+ (already verified present on this machine).

## Setup

1. Create and activate a virtual environment:
   ```
   python -m venv .venv
   .venv\Scripts\activate
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

Install dev dependencies and run the pytest suite (uses Flask's test client against a temporary SQLite file, not `instance/radiocalico.db`):
```
pip install -r requirements-dev.txt
pytest
```

## Notes

- The SQLite database file lives at `instance/radiocalico.db` (auto-created on first run, gitignored).
- Flask runs in debug mode with auto-reload, so editing `app.py` restarts the server automatically.
- To start fresh, just delete `instance/radiocalico.db` and restart the app — it will recreate the schema.
