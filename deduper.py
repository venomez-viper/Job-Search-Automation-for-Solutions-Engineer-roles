"""
deduper.py — SQLite-backed seen-jobs store to prevent duplicate daily emails.
"""
import sqlite3
import logging
from datetime import datetime, timezone
from fetchers.base import Job

logger = logging.getLogger(__name__)

DB_PATH = "seen_jobs.db"


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            url       TEXT PRIMARY KEY,
            title     TEXT,
            company   TEXT,
            date_seen TEXT
        )
    """)
    conn.commit()
    return conn


def filter_new_jobs(jobs: list[Job]) -> list[Job]:
    """Return only jobs that have NOT been seen before."""
    conn = _get_conn()
    new_jobs = []
    try:
        for job in jobs:
            row = conn.execute(
                "SELECT 1 FROM seen_jobs WHERE url = ?", (job.url,)
            ).fetchone()
            if row is None:
                new_jobs.append(job)
    finally:
        conn.close()

    logger.info(f"Deduper: {len(jobs)} total -> {len(new_jobs)} new (unseen) jobs.")
    return new_jobs


def mark_seen(jobs: list[Job]) -> None:
    """Record jobs as seen so they won't appear in future runs."""
    if not jobs:
        return
    conn = _get_conn()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        conn.executemany(
            "INSERT OR IGNORE INTO seen_jobs (url, title, company, date_seen) VALUES (?, ?, ?, ?)",
            [(j.url, j.title, j.company, today) for j in jobs],
        )
        conn.commit()
        logger.info(f"Deduper: marked {len(jobs)} jobs as seen.")
    finally:
        conn.close()


def get_seen_count() -> int:
    """Return the total number of jobs ever seen."""
    conn = _get_conn()
    try:
        return conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
    finally:
        conn.close()
