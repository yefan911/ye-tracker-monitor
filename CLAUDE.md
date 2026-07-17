# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture

This is a Google Sheets → Discord webhook monitor for tracking "Ye Tracker" spreadsheet entries. It polls a Google Sheet every 2 minutes and sends Discord embed notifications when new rows are detected.

### Key files

- **`sheets.py`** — Active production script. Reads from the `📄 Trackers` sheet, detects new rows, and sends rich Discord embeds with color-coded categories (trackers=green, websites=yellow, archive=purple).
- **`sheet2(test).py`** — Older/simpler test version. Same logic but sends plain text Discord messages without embed formatting or type categorization.
- **`credentials.json`** — Google service account credentials for Sheets API access.
- **`sheet_output.txt`** — Persistent cache of previously seen rows (used to detect new rows across restarts).

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

## Configuration

- `CREDS_FILE` — path to Google service account JSON (default: `credentials.json`)
- `SPREADSHEET_ID` — target Google Sheet ID
- `WEBHOOK_URL` — Discord webhook URL
- `OUTPUT_FILE` — path to row cache (default: `sheet_output.txt`)
- Loop interval: 120 seconds in `sheets.py`, 3600 seconds in `sheet2(test).py`