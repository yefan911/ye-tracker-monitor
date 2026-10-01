# Ye Tracker Monitor

A Google Sheets → Discord webhook monitor for tracking spreadsheet entries. It polls Google Sheets every 2 minutes and sends Discord embed notifications when new rows are detected.

## Features

- Monitors multiple tabs/sheets within a single Google Spreadsheet
- Detects new rows and sends formatted Discord embed notifications
- Color-coded entries by type (Trackers=green, Websites=yellow, Archive=purple, etc.)
- Skips internal update-log rows (like `[8/6/24] Updated tracker X`)
- Batched notifications (8 entries per Discord message)
- Persistent caching to avoid duplicate notifications
- Railway.app ready for 24/7 deployment

## Key Files

- **`sheets.py`** — Main production script. Reads from configured tabs, detects new rows, and sends rich Discord embeds.
- **`sheet2(test).py`** — Older/simpler test version. Same logic but sends plain text Discord messages.
- **`credentials.json`** — Local Google service account credentials (gitignored).
- **`sheet_output.txt`** — Persistent cache of previously seen rows (gitignored).
- **`railway.json`** — Railway.app deployment configuration.
- **`.env.example`** — Template for required environment variables.
- **`requirements.txt`** — Python dependencies.

## Data Flow

1. Loads previously seen rows from `sheet_output.txt`
2. Fetches current sheet data from all configured tabs via Google Sheets API
3. Compares current vs. previous rows to find new entries across all tabs
4. Formats new entries as Discord embeds (batched 8 per message)
5. Sends via webhook to Discord, then saves current rows to `sheet_output.txt`
6. Sleeps for the configured interval and repeats

## Sheet Structure

Columns: Type, Name, Information, Up to date? // Evidence, Working // Available?, Link(s)

## Configuration

### Environment Variables

The following environment variables can be configured:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SPREADSHEET_ID` | Yes | (hardcoded fallback) | Google Sheet ID to monitor |
| `WEBHOOK_URL` | Yes | (hardcoded fallback) | Discord webhook URL |
| `GOOGLE_CREDS_JSON` | On Railway | — | Full service account JSON as a single string |
| `GOOGLE_CREDS_FILE` | Local | `credentials.json` | Path to local credentials file |
| `LOOP_INTERVAL` | No | `120` | Poll interval in seconds |
| `SHEET_TABS` | No | `📄 Trackers` | Comma-separated list of tab names to monitor |

### Available Tabs

The script can monitor any tabs in your spreadsheet. Just add them to the `SHEET_TABS` variable:
- `📄 Trackers` (default)
- `🎭 LEAKTIONARY - MISC 🖼️`
- `🛠️ Templates`
- Or any other tabs in your spreadsheet

## Running Locally

The project uses a `.venv` virtual environment. Activate it before running:

```bash
# Git Bash
source .venv/Scripts/activate

# CMD
.venv\Scripts\activate

# PowerShell
.venv\Scripts\Activate.ps1
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the main script:
```bash
python sheets.py
```

## Deployment (Railway.app)

The project is set up for Railway.app with auto-deploy from GitHub:

1. Push to a GitHub repo
2. In Railway, create a **new project** → **Deploy from GitHub repo**
3. Railway auto-detects the Python builder via `railway.json`
4. Set the environment variables in Railway's dashboard:
   - `SPREADSHEET_ID`
   - `WEBHOOK_URL`
   - `GOOGLE_CREDS_JSON` (paste the entire `credentials.json` content)
   - `SHEET_TABS` (optional, defaults to `📄 Trackers`)
5. Railway starts `python sheets.py` as a worker — it runs 24/7

To update the running script, push to the GitHub repo and Railway redeploys automatically.

## Example Configuration

To monitor all three tabs mentioned in the project:
```
SHEET_TABS=📄 Trackers,🎭 LEAKTIONARY - MISC 🖼️,🛠️ Templates
```
