"""
fetchers/himalayas.py — Fetch remote jobs from Himalayas public API.

Free public API, no auth required.
Endpoint: https://himalayas.app/api/jobs
"""
import requests
import logging
import time

from .base import Job, clean_html, title_matches_targets, title_excluded
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS

logger = logging.getLogger(__name__)
TIMEOUT = 20
DELAY   = 0.5

SEARCH_TERMS = [
    "solutions engineer",
    "sales engineer",
    "pre-sales engineer",
    "solution consultant",
    "solutions consultant",
]


def fetch_himalayas() -> list[Job]:
    """Fetch remote SE/pre-sales jobs from Himalayas."""
    all_jobs: list[Job] = []
    seen_urls: set[str] = set()

    for term in SEARCH_TERMS:
        try:
            resp = requests.get(
                "https://himalayas.app/api/jobs",
                params={"q": term, "limit": 50},
                timeout=TIMEOUT,
            )
            if resp.status_code != 200:
                logger.debug(f"Himalayas: '{term}' returned {resp.status_code}")
                time.sleep(DELAY)
                continue
            jobs = resp.json().get("jobs", [])
        except Exception as e:
            logger.warning(f"Himalayas fetch failed for '{term}': {e}")
            time.sleep(DELAY)
            continue

        for job in jobs:
            title   = job.get("title", "")
            company = job.get("companyName", "") or job.get("company", {}).get("name", "")
            job_url = job.get("applicationLink", "") or job.get("url", "")
            location = "Remote"   # Himalayas is remote-only
            description = clean_html(job.get("description", "") or "")[:3000]
            date_posted = (job.get("createdAt") or "")[:10]

            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)

            if not title_matches_targets(title, TARGET_TITLES):
                continue
            if title_excluded(title, EXCLUDE_TITLE_KEYWORDS):
                continue

            all_jobs.append(Job(
                company=company,
                title=title,
                location=location,
                url=job_url,
                description=description,
                date_posted=date_posted,
                source="himalayas",
            ))

        time.sleep(DELAY)

    logger.info(f"Himalayas: found {len(all_jobs)} matching jobs.")
    return all_jobs
