import ast
import os
import re
import time

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Pattern to detect update-log rows like [x/xx/xx] reason...
UPDATE_LOG_PATTERN = re.compile(r'^\[\d{1,2}/\d{1,2}/\d{2,4}\]')


def is_update_log_row(row):
    """Check if a row is an internal update log entry (e.g., [8/6/24] Updated tracker X)."""
    if not row or len(row) < 1:
        return False
    first_cell = str(row[0]).strip()
    return bool(UPDATE_LOG_PATTERN.match(first_cell))

try:
    import requests
except ImportError:
    raise SystemExit("Install requests first with: pip install requests")

