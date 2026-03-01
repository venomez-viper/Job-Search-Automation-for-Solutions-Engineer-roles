"""
sheets.py — Log daily job results to a Google Sheet.
"""
import os
import json
import logging
from datetime import datetime
from fetchers.base import Job

logger = logging.getLogger(__name__)


def log_to_sheets(jobs: list[Job], dry_run: bool = False) -> bool:
    """
    Append job rows to the configured Google Sheet.
    Each row: [Date, Company, Title, Location, URL, Score, Source]
    Returns True on success, False otherwise.
    """
    if dry_run:
        logger.info("DRY RUN — skipping Google Sheets log.")
        return True

    sheet_id = os.environ.get("GOOGLE_SHEET_ID", "")
    creds_json_str = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")

    if not sheet_id or not creds_json_str:
        logger.warning("GOOGLE_SHEET_ID / GOOGLE_CREDENTIALS_JSON not set. Skipping Sheets log.")
        return False

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_dict = json.loads(creds_json_str)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        sheet = client.open_by_key(sheet_id)

        # Use first worksheet, or create "Jobs" tab
        try:
            ws = sheet.worksheet("Jobs")
        except Exception:
            ws = sheet.add_worksheet(title="Jobs", rows=5000, cols=10)
            # Add header row
            ws.append_row(
                ["Date", "Company", "Title", "Location", "URL", "Score", "Source"],
                value_input_option="USER_ENTERED",
            )

        today = datetime.now().strftime("%Y-%m-%d")
        rows = [
            [today, job.company, job.title, job.location, job.url, job.score, job.source]
            for job in jobs
        ]
        ws.append_rows(rows, value_input_option="USER_ENTERED")
        logger.info(f"Sheets: logged {len(jobs)} rows to Google Sheet '{sheet_id}'.")
        return True

    except ImportError:
        logger.error("gspread / google-auth not installed. Run: pip install gspread google-auth")
        return False
    except Exception as e:
        logger.error(f"Sheets log failed: {e}")
        return False
