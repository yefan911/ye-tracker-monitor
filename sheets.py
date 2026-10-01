import ast
import json
import os
import re
import time
from urllib.parse import quote

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Pattern to detect update-log rows like [x/xx/xx] reason...
UPDATE_LOG_PATTERN = re.compile(r'^\[\d{1,2}/\d{1,2}/\d{2,4}\]')

try:
    import requests
except ImportError:
    raise SystemExit("Install requests first with: pip install requests")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
CREDS_FILE = os.environ.get("GOOGLE_CREDS_FILE", "credentials.json")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID", "1DUc-LSJlJb0x_jNqr5j75E39wa_VqRGdx5xPt4ao1Qs")
OUTPUT_FILE = "sheet_output.txt"
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://discord.com/api/webhooks/1527083499033723002/tfURdbbB323zwb7e_I3In-7t_uWqp16o9B0eNw9JccwJUpQjA0RSSxlCntyFc46nS-vF")
LOOP_INTERVAL = int(os.environ.get("LOOP_INTERVAL", "120"))
# Tabs to monitor, comma-separated. Default to original tracker tab.
SHEET_TABS_ENV = os.environ.get("SHEET_TABS", "📄 Trackers")
SHEET_TABS = [tab.strip() for tab in SHEET_TABS_ENV.split(",") if tab.strip()]
TYPE_COLORS = {
    "trackers": 0x2ECC71,
    "websites": 0xF1C40F,
    "archive": 0x9B59B6,
    "star": 0xF1C40F,
    "trash": 0x99AAB5,
}
TYPE_SIDEBARS = {
    "trackers": "🟩",
    "websites": "🟨",
    "archive": "🟪",
    "star": "⭐",
    "trash": "🗑️",
}


def is_update_log_row(row):
    """Check if a row is an internal update log entry (e.g., [8/6/24] Updated tracker X)."""
    if not row or len(row) < 1:
        return False
    first_cell = str(row[0]).strip()
    return bool(UPDATE_LOG_PATTERN.match(first_cell))


def load_previous_rows(file_path):
    """Load previous rows, supporting both legacy format and tab-prefixed format."""
    if not os.path.exists(file_path):
        return {}

    # Returns dict: {tab_name: [rows]}
    previous_rows_by_tab = {}
    with open(file_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                # Check if line is in new format: "TAB_NAME::: ROW_DATA"
                if ":::" in line:
                    tab_name, row_data_str = line.split(":::", 1)
                    tab_name = tab_name.strip()
                    row_data = ast.literal_eval(row_data_str.strip())
                    if tab_name not in previous_rows_by_tab:
                        previous_rows_by_tab[tab_name] = []
                    previous_rows_by_tab[tab_name].append(row_data)
                else:
                    # Legacy format: entire line is row data, assume default tab
                    row_data = ast.literal_eval(line)
                    default_tab = "📄 Trackers"
                    if default_tab not in previous_rows_by_tab:
                        previous_rows_by_tab[default_tab] = []
                    previous_rows_by_tab[default_tab].append(row_data)
            except (ValueError, SyntaxError):
                continue
    return previous_rows_by_tab


def normalize_row(row):
    return [str(cell).strip() if cell is not None else "" for cell in row]


def get_new_rows(current_rows, previous_rows):
    """Get new rows by comparing current rows to previous rows."""
    previous_set = {tuple(normalize_row(row)) for row in previous_rows}
    new_rows = [normalize_row(row) for row in current_rows if tuple(normalize_row(row)) not in previous_set]
    # Filter out update log rows
    return [row for row in new_rows if not is_update_log_row(row)]


def normalize_entry_type(value):
    if value is None:
        return "Unknown"

    text = str(value).strip()
    if not text:
        return "Unknown"

    lowered = text.lower()
    if lowered == "trackers":
        return "Trackers"
    if lowered == "websites":
        return "Websites"
    if lowered == "archive":
        return "Archive"
    if "⭐" in text or "✨" in text:
        return "Star"
    if "🗑️" in text or "🗑" in text:
        return "Trash"
    return text


def get_type_color(entry_type):
    return TYPE_COLORS.get(normalize_entry_type(entry_type).lower(), 0x5865F2)


def get_type_sidebar(entry_type):
    return TYPE_SIDEBARS.get(normalize_entry_type(entry_type).lower(), "⚪")


def extract_rows(current_rows, previous_rows):
    previous_set = {tuple(normalize_row(row)) for row in previous_rows}
    entries = []
    for index, row in enumerate(current_rows[1:], start=2):
        if not row:
            continue

        normalized_row = normalize_row(row)
        row_key = tuple(normalized_row)
        if row_key in previous_set:
            continue

        # Skip update log rows (e.g., [8/6/24] Updated tracker X)
        if is_update_log_row(normalized_row):
            continue

        if not any(normalized_row):
            continue

        full_row = normalized_row
        entry_type = full_row[0] if len(full_row) > 0 else ""
        name = full_row[1] if len(full_row) > 1 else f"Row {index}"
        information = full_row[2] if len(full_row) > 2 else ""
        status = full_row[3] if len(full_row) > 3 else ""
        availability = full_row[4] if len(full_row) > 4 else ""
        link = full_row[5] if len(full_row) > 5 else ""

        entries.append({
            "row": index,
            "type": entry_type,
            "type_label": normalize_entry_type(entry_type),
            "name": name,
            "information": information,
            "status": status,
            "availability": availability,
            "link": link,
            "full_row": full_row,
        })
    return entries


def split_message(text, max_length=1900):
    if not text:
        return [""]

    chunks = []
    current = ""

    for line in text.splitlines():
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) <= max_length:
            current = candidate
            if line.strip() == "```":
                chunks.append(current)
                current = ""
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(line) > max_length:
            chunks.append(line[:max_length])
            continue

        current = line
        if line.strip() == "```":
            chunks.append(current)
            current = ""

    if current:
        chunks.append(current)

    return chunks or [text[:max_length]]


def send_discord_message(webhook_url, blocks):
    if not blocks:
        blocks = [{}]

    for index, block in enumerate(blocks, start=1):
        payload = block if isinstance(block, dict) else {"embeds": [{"description": str(block)}]}
        while True:
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 429:
                retry_after = response.json().get("retry_after", 1) if response.content else 1
                print(f"Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after + 0.2)
                continue
            break

        print(f"Webhook message {index} status: {response.status_code}")
        if response.text:
            print(response.text)

        time.sleep(1.2)


def delete_webhook_message(webhook_url, message_id):
    if not message_id:
        return

    delete_url = f"{webhook_url}/messages/{message_id}"
    response = requests.delete(delete_url, timeout=10)
    print(f"Delete status: {response.status_code}")
    if response.text:
        print(response.text)


def build_message_blocks(entries, max_entries_per_message=8):
    blocks = []
    current_batch = []

    for item in entries:
        current_batch.append(item)
        if len(current_batch) >= max_entries_per_message:
            blocks.append(format_entry_batch(current_batch))
            current_batch = []

    if current_batch:
        blocks.append(format_entry_batch(current_batch))

    return blocks


def format_entry_batch(items):
    if not items:
        return {"embeds": [{"description": "No entries found"}]}

    type_names = {item.get("type_label", "Unknown") for item in items}
    primary_type = next(iter(type_names)) if len(type_names) == 1 else "Mixed"
    sidebar = get_type_sidebar(primary_type)
    color = get_type_color(primary_type)

    entry_lines = []
    for item in items:
        entry_lines.append(
            f"**{item['name']}**\n"
            f"Info: {item['information'] or 'No info provided'}\n"
            f"Status: {item['status'] or 'Not listed'}\n"
            f"Available: {item['availability'] or 'Not listed'}\n"
            f"Link: {item['link'] or 'No link provided'}"
        )

    description = "\n\n".join(entry_lines)
    return {
        "embeds": [{
            "title": f"{sidebar} {primary_type}",
            "description": description,
            "color": color,
            "footer": {"text": f"{len(items)} entr{'y' if len(items) == 1 else 'ies'}"},
        }],
    }


def get_credentials():
    """Load Google credentials from env var JSON string or fall back to file."""
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")
    if creds_json:
        creds_dict = json.loads(creds_json)
        return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)


previous_rows_by_tab = load_previous_rows(OUTPUT_FILE)
had_cache = os.path.exists(OUTPUT_FILE)  # track if we had a cache file (prevents re-sending ALL rows on Railway restarts)
buffer_rows = 20

last_message_id = None
while True:
    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)

    all_new_rows = []
    all_entries = []
    all_current_rows = []  # For caching
    tabs_data = {}  # Store tab data to avoid redundant API calls

    # Process each tab
    for tab_name in SHEET_TABS:
        # Format tab name for Google Sheets API range
        # If tab name contains spaces or special characters, wrap in single quotes
        if any(c in tab_name for c in [' ', '(', ')', '+', '-', '=', '~', '!', '@', '#', '$', '%', '^', '&', '*']):
            formatted_tab_name = f"'{tab_name}'"
        else:
            formatted_tab_name = tab_name

        range_limit = max(1204, len(previous_rows_by_tab.get(tab_name, [])) + buffer_rows)
        RANGE_NAME = f"{formatted_tab_name}!A1:F{range_limit}"

        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME
        ).execute()

        rows = result.get("values", [])
        tabs_data[tab_name] = rows  # Store for reuse
        all_current_rows.extend(rows)  # Combine all rows for caching

        # Get previous rows for this tab (default to empty list if tab not seen before)
        previous_rows = previous_rows_by_tab.get(tab_name, [])
        new_rows = get_new_rows(rows, previous_rows)
        entries = extract_rows(rows, previous_rows)

        all_new_rows.extend(new_rows)
        all_entries.extend(entries)

        # Use backslashreplace to safely represent non-ASCII characters in ASCII
        safe_tab_name = tab_name.encode('ascii', errors='backslashreplace').decode('ascii')
        print(f"Tab '{safe_tab_name}': {len(rows)} rows, {len(new_rows)} new")

    # Save all rows with tab prefixes
    with open(OUTPUT_FILE, "w", encoding="utf-8") as output_file:
        # Write all rows with tab prefixes
        for tab_name, rows in tabs_data.items():
            for row in rows:
                output_file.write(f"{tab_name}::: {str(row)}\n")

    if all_new_rows and not had_cache:
        print(f"First run (no cache) — saving {len(all_current_rows)} rows without sending notifications.")
        had_cache = True
    elif all_new_rows:
        summary = {
            "embeds": [{
                "title": "🆕 New rows detected",
                "description": f"{len(all_new_rows)} new row(s) were found across all tabs.",
                "color": 0x5865F2,
            }],
        }
        try:
            send_discord_message(WEBHOOK_URL, [summary])
            blocks = build_message_blocks(all_entries)
            send_discord_message(WEBHOOK_URL, blocks)
        except Exception as exc:
            print(f"Webhook failed: {exc}")
    else:
        if last_message_id:
            delete_webhook_message(WEBHOOK_URL, last_message_id)
            last_message_id = None
        print("No new rows detected; skipping webhook update.")

    # Update previous_rows_by_tab for next iteration using stored data
    previous_rows_by_tab = tabs_data

    # Safely print tab names by handling Unicode encoding issues
    safe_tab_names = [name.encode('utf-8', errors='replace').decode('utf-8') for name in SHEET_TABS]
    print(f"Saved rows from {len(SHEET_TABS)} tabs to {OUTPUT_FILE}")
    time.sleep(LOOP_INTERVAL)

