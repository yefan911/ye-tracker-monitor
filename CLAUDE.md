# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

This is a Google Sheets → Discord webhook monitor for tracking spreadsheet entries. It polls multiple configured Google Sheets tabs (`📄 Trackers`, `🎭 LEAKTIONARY - MISC 🖼️`, `🛠️ Templates`, etc.) every 2 minutes and sends Discord embed notifications when new rows are detected.

### Key files

- **`sheets.py`** — Active production script. Reads from configured tabs, detects new rows, and sends rich Discord embeds with color-coded categories.
- **`sheet2(test).py`** — Older/simpler test version.
- **`credentials.json`** — Local Google service account credentials (gitignored).
- **`sheet_output.txt`** — Persistent cache of previously seen rows with tab prefixes (gitignored).
- **`railway.json`** — Railway.app deployment config defining the worker process.
- **`.env.example`** — Template for required environment variables.
- **`requirements.txt`** — Python dependencies.

### Data flow

1. `sheets.py` loads previously seen rows per tab from `sheet_output.txt`
2. Fetches current sheet data for each configured tab via Google Sheets API
3. Compares current vs. previous rows to find new entries across all tabs
4. Formats new entries as Discord embeds (batched 8 per message)
5. Sends via webhook to Discord, then saves current rows to `sheet_output.txt`
6. Sleeps for the configured interval (`LOOP_INTERVAL`) and repeats

## Running

Activate the virtual environment:
```bash
source .venv/Scripts/activate  # Git Bash / Linux
.venv\Scripts\Activate.ps1     # PowerShell
```

Run the main script:
```bash
python sheets.py
```

## Configuration (Environment Variables)

| Variable | Required | Default | Description |
|---|---|---|---|
| `SPREADSHEET_ID` | Yes | (hardcoded fallback) | Google Sheet ID to monitor |
| `WEBHOOK_URL` | Yes | (hardcoded fallback) | Discord webhook URL |
| `GOOGLE_CREDS_JSON` | On Railway | — | Full service account JSON as a single string |
| `GOOGLE_CREDS_FILE` | Local | `credentials.json` | Path to local credentials file |
| `LOOP_INTERVAL` | No | `120` | Poll interval in seconds |
| `SHEET_TABS` | No | `📄 Trackers` | Comma-separated list of tab names to monitor (e.g., `📄 Trackers,🎭 LEAKTIONARY - MISC 🖼️,🛠️ Templates`) |
