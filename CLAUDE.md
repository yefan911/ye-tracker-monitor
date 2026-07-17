# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

This is a Google Sheets → Discord webhook monitor for tracking "Ye Tracker" spreadsheet entries. It polls a Google Sheet every 2 minutes and sends Discord embed notifications when new rows are detected.

### Key files

- **`sheets.py`** — Active production script. Reads from the `📄 Trackers` sheet, detects new rows, and sends rich Discord embeds with color-coded categories (trackers=green, websites=yellow, archive=purple).
- **`sheet2(test).py`** — Older/simpler test version. Same logic but sends plain text Discord messages without embed formatting or type categorization.
- **`credentials.json`** — Local Google service account credentials (gitignored — not committed to GitHub).
- **`sheet_output.txt`** — Persistent cache of previously seen rows (gitignored).
- **`railway.json`** — Railway.app deployment config defining the worker process.
- **`.env.example`** — Template for required environment variables.
- **`requirements.txt`** — Python dependencies.

### Data flow

1. `sheets.py` loads previously seen rows from `sheet_output.txt`
2. Fetches current sheet data via Google Sheets API (range `📄 Trackers!A1:F{limit}`)
3. Compares current vs. previous rows to find new entries
4. Formats new entries as Discord embeds (batched 8 per message)
5. Sends via webhook to Discord, then saves current rows to `sheet_output.txt`
6. Sleeps 120 seconds and repeats

### Sheet structure

Columns: Type, Name, Information, Up to date? // Evidence, Working // Available?, Link(s)

## Running

The project uses a `.venv` virtual environment. Activate it before running:

```bash
source .venv/Scripts/activate  # Git Bash
# or
.venv\Scripts\activate  # CMD
# or
.venv\Scripts\Activate.ps1  # PowerShell
```

Run the main script:
```bash
python sheets.py
```

Dependencies: `google-api-python-client`, `google-auth`, `requests` (all installed in `.venv`).

## Configuration (Environment Variables)

Secrets are read from environment variables, with fallbacks for local development:

| Variable | Required | Default | Description |
|---|---|---|---|
| `SPREADSHEET_ID` | Yes | (hardcoded fallback) | Google Sheet ID to monitor |
| `WEBHOOK_URL` | Yes | (hardcoded fallback) | Discord webhook URL |
| `GOOGLE_CREDS_JSON` | On Railway | — | Full service account JSON as a single string |
| `GOOGLE_CREDS_FILE` | Local | `credentials.json` | Path to local credentials file |
| `LOOP_INTERVAL` | No | `120` | Poll interval in seconds |

For local dev, either set `GOOGLE_CREDS_JSON` or keep `credentials.json` in the project root.

## Deployment (Railway.app)

The project is set up for Railway.app with auto-deploy from GitHub:

1. Push to a GitHub repo
2. In Railway, create a **new project** → **Deploy from GitHub repo**
3. Railway auto-detects the Python builder via `railway.json`
4. Set the environment variables in Railway's dashboard:
   - `SPREADSHEET_ID`
   - `WEBHOOK_URL`
   - `GOOGLE_CREDS_JSON` (paste the entire `credentials.json` content)
5. Railway starts `python sheets.py` as a worker — it runs 24/7

To update the running script, push to the GitHub repo and Railway redeploys automatically.