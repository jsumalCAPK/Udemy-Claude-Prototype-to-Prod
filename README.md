# Radio Calico

An internet radio station site: a branded homepage with a lossless HLS stream player, backed by a Python/Flask web server + SQLite database. No Docker, no separate DB server to install — everything runs from a single Python virtual environment.

UI work should follow `RadioCalico_Style_Guide.txt` (colors, type, components, voice/tone) — it's the source of truth for styling, even where the `RadioCalicoLayout.png` mockup differs in the details.

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
   - `http://localhost:3000/` — the Radio Calico homepage: branded nav bar, a "who am I" picker (pick an existing user to rate tracks), the now-playing/previous-tracks panel (seeded with placeholder data), and the lossless HLS player (play/pause, volume, live elapsed time)
   - `http://localhost:3000/demo` — the earlier Flask+SQLite exercise: repo name as title, tech-stack caption, a form to add a user (name + email), and the current list of users
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

- `test_demo_shows_title_and_tech_stack` — hits `/demo` and checks the page title, tech-stack caption, and empty-state message.
- `test_add_user_appears_in_demo_list` — posts a new user to `/users`, follows up with a `GET /demo`, and checks the user's name and email now appear in the list.
- `test_add_user_requires_name_and_email` — posts with a blank name and checks the user is not added.
- `test_index_shows_station_and_stream` — hits `/` and checks the branding, the embedded stream URL, and the play control.
- `test_index_shows_seeded_now_playing_and_previous_tracks` — checks the placeholder track data seeded by `init_db()` actually renders.
- `test_rate_without_identity_does_not_persist` — rating with no "who am I" selected writes nothing to `track_ratings`.
- `test_rate_with_identity_persists_and_shows_count` — rating after picking a user persists and the count shows on the page.
- `test_rerating_replaces_rather_than_duplicates` — a user changing their rating updates their existing row instead of creating a second one.
- `test_multiple_users_rate_independently` — two different users rating the same track both persist independently.
- `test_log_play_records_anonymous_and_identified` — play events log with and without an identity picked (`user_id` nullable).
- `test_health_db_returns_ok_with_timestamp` — hits `/health/db` once and checks it returns `status: ok`, a `dbTime`, and `totalChecks == 1`.
- `test_health_db_increments_across_requests` — hits `/health/db` twice and checks the count goes 1 → 2, proving state actually persists in SQLite across requests.
- `test_health_db_reports_error_for_unwritable_path` — points the DB path at a nonexistent directory and checks the route returns a 500 with `status: error`, proving the error-handling branch actually triggers.

## Notes

- The SQLite database file lives at `instance/radiocalico.db` (auto-created on first run, gitignored).
- Schema: `users`, `tracks` (now-playing/previous-tracks history, seeded with placeholder data), `track_ratings` (one row per track+user, upserted on re-rating), `track_plays` (one row per play, `user_id` nullable for anonymous listens), and `health_check`.
- There's no login system — identity is a lightweight "who am I" picker (pick an existing `users` row, remembered in a signed session cookie). Listening never requires an identity; only rating does.
- Flask runs in debug mode with auto-reload, so editing `app.py` restarts the server automatically.
- To start fresh, just delete `instance/radiocalico.db` and restart the app — it will recreate and reseed the schema.
