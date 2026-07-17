import ast
import os
import time

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

try:
    import requests
except ImportError:
    raise SystemExit("Install requests first with: pip install requests")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
CREDS_FILE = "credentials.json"
SPREADSHEET_ID = "ID"
OUTPUT_FILE = "sheet_output.txt"
WEBHOOK_URL = "INSERT_WEBHOOK_URL"


def load_previous_rows(file_path):
    if not os.path.exists(file_path):
        return []

    previous_rows = []
    with open(file_path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                previous_rows.append(ast.literal_eval(line))
            except (ValueError, SyntaxError):
                continue
    return previous_rows


def get_new_rows(current_rows, previous_rows):
    previous_set = {tuple(row) for row in previous_rows}
    return [row for row in current_rows if tuple(row) not in previous_set]


def extract_rows(rows):
    entries = []
    for index, row in enumerate(rows[1:], start=2):
        if not row:
            continue

        values = [
            str(cell).strip() if cell is not None else ""
            for cell in row
        ]
        if not any(values):
            continue

        full_row = values
        name = full_row[1] if len(full_row) > 1 else f"Row {index}"
        information = full_row[2] if len(full_row) > 2 else ""
        status = full_row[3] if len(full_row) > 3 else ""
        availability = full_row[4] if len(full_row) > 4 else ""
        link = full_row[5] if len(full_row) > 5 else ""

        entries.append({
            "row": index,
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
        blocks = ["No entries found"]

    for index, block in enumerate(blocks, start=1):
        for chunk in split_message(block):
            payload = {"content": chunk}
            while True:
                response = requests.post(webhook_url, data=payload, timeout=10)
                if response.status_code == 429:
                    retry_after = response.json().get("retry_after", 1)
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
    lines = ["```", "**Entries**"]
    for item in items:
        full_row_text = " | ".join(item.get("full_row", [])) or "No row content"
        lines.extend([
            f"**Name:** {item['name']}",
            f"**Row:** {item['row']}",
            f"**Info:** {item['information']}",
            f"**Status:** {item['status']}",
            f"**Available:** {item['availability']}",
            f"**Link:** {item['link'] or 'No link provided'}",
            f"**Full row:** {full_row_text}",
            ""
        ])
    lines.append("```")
    return "\n".join(lines)


previous_rows = load_previous_rows(OUTPUT_FILE)
buffer_rows = 20
range_limit = max(511, len(previous_rows) + buffer_rows)
RANGE_NAME = f"📄 Trackers!A1:F{range_limit}"

last_message_id = None
while True:
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)

    result = service.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME
    ).execute()

    rows = result.get("values", [])
    new_rows = get_new_rows(rows, previous_rows)
    entries = extract_rows(new_rows)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as output_file:
        for row in rows:
            print(row)
            output_file.write(str(row) + "\n")

    if new_rows:
        summary = f"**New rows detected:** {len(new_rows)}"
        try:
            send_discord_message(WEBHOOK_URL, [summary])
            blocks = build_message_blocks(entries)
            send_discord_message(WEBHOOK_URL, blocks)
        except Exception as exc:
            print(f"Webhook failed: {exc}")
    else:
        if last_message_id:
            delete_webhook_message(WEBHOOK_URL, last_message_id)
            last_message_id = None
        print("No new rows detected; skipping webhook update.")

    previous_rows = rows
    print(f"Saved {len(rows)} rows to {OUTPUT_FILE}")
    time.sleep(3600)
