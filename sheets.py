"""
sheets.py — Log daily job results to jobs_log.csv in the repository.

The CSV file accumulates every day and is committed back to GitHub
by the Actions workflow, making it accessible online at any time.
No Google credentials or external services required.
"""
import csv
import logging
from datetime import datetime
from pathlib import Path
from fetchers.base import Job

logger = logging.getLogger(__name__)

CSV_FILE = "jobs_log.csv"
HEADERS = ["Date", "Company", "Title", "Location", "URL", "Score", "Label", "Source", "Posted", "Match Signals"]


def log_to_sheets(jobs: list[Job], dry_run: bool = False) -> bool:
    """
    Append job rows to jobs_log.csv.
    Creates the file with a header row if it doesn't exist yet.
    Returns True on success, False on error.
    """
    if dry_run:
        logger.info("DRY RUN — skipping CSV log.")
        return True

    try:
        path = Path(CSV_FILE)
        today = datetime.now().strftime("%Y-%m-%d")
        write_header = not path.exists()

        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if write_header:
                writer.writerow(HEADERS)

            for job in jobs:
                bd = getattr(job, "breakdown", None)
                signals = ""
                if bd:
                    parts = []
                    if bd.core_matches:
                        parts.append("Core: " + ", ".join(m.split("(")[0] for m in bd.core_matches[:3]))
                    if bd.tool_matches:
                        parts.append("Tools: " + ", ".join(m.split("(")[0] for m in bd.tool_matches[:2]))
                    if bd.transferable_matches:
                        parts.append("Transfer: " + ", ".join(m.split("->")[0] for m in bd.transferable_matches[:2]))
                    signals = " | ".join(parts)

                writer.writerow([
                    today,
                    job.company,
                    job.title,
                    job.location,
                    job.url,
                    job.score,
                    getattr(job, "label", ""),
                    job.source,
                    job.date_posted or "",
                    signals,
                ])

        logger.info(f"CSV: logged {len(jobs)} rows to {CSV_FILE}.")
        return True

    except Exception as e:
        logger.error(f"CSV log failed: {e}")
        return False
