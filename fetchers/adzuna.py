"""
fetchers/adzuna.py — Fetch jobs from Adzuna API.

Free tier: 250 calls/month — no credit card needed.
Covers millions of jobs across Indeed, company sites, and more.

Setup:
  1. Go to https://developer.adzuna.com/
  2. Register free → get App ID + API Key
  3. Add ADZUNA_APP_ID and ADZUNA_API_KEY to GitHub Secrets

If not set, this fetcher is silently skipped.
"""
import os
import time
import requests
import logging

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS

logger = logging.getLogger(__name__)
TIMEOUT = 20
DELAY   = 1.0

BASE_URL = "https://api.adzuna.com/v1/api/jobs/us/search/{page}"

SEARCH_QUERIES = [
    "solutions engineer",
    "sales engineer",
    "pre-sales engineer",
    "solution consultant",
]

LOCATIONS = ["chicago", ""]   # "" = nationwide/remote


def fetch_adzuna() -> list[Job]:
    """Fetch SE/pre-sales jobs from Adzuna (aggregates Indeed + others)."""
    app_id  = os.environ.get("ADZUNA_APP_ID", "")
    api_key = os.environ.get("ADZUNA_API_KEY", "")

    if not app_id or not api_key:
        logger.info("Adzuna: ADZUNA_APP_ID / ADZUNA_API_KEY not set — skipping. "
                    "(Register free at developer.adzuna.com for broader job coverage)")
        return []

    all_jobs: list[Job] = []
    seen_urls: set[str] = set()

    for query in SEARCH_QUERIES:
        for loc in LOCATIONS:
            try:
                params = {
                    "app_id":   app_id,
                    "app_key":  api_key,
                    "what":     query,
                    "results_per_page": 20,
                    "sort_by":  "date",
                    "full_time": 1,
                    "content-type": "application/json",
                }
                if loc:
                    params["where"] = loc

                resp = requests.get(
                    BASE_URL.format(page=1),
                    params=params,
                    timeout=TIMEOUT,
                )
                if resp.status_code == 429:
                    logger.warning("Adzuna: rate limited, waiting 5s...")
                    time.sleep(5)
                    time.sleep(DELAY)
                    continue
                if resp.status_code != 200:
                    logger.debug(f"Adzuna: '{query}' returned {resp.status_code}")
                    time.sleep(DELAY)
                    continue

                jobs = resp.json().get("results", [])
            except Exception as e:
                logger.warning(f"Adzuna fetch failed for '{query}': {e}")
                time.sleep(DELAY)
                continue

            for job in jobs:
                title   = job.get("title", "")
                company = job.get("company", {}).get("display_name", "")
                job_url = job.get("redirect_url", "")
                loc_data = job.get("location", {})
                location = loc_data.get("display_name", "") or "Remote"
                description = clean_html(job.get("description", "") or "")[:3000]
                date_posted = (job.get("created") or "")[:10]

                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                if not title_matches_targets(title, TARGET_TITLES):
                    continue
                if title_excluded(title, EXCLUDE_TITLE_KEYWORDS):
                    continue
                if not location_allowed(location, ALLOWED_LOCATIONS):
                    continue

                all_jobs.append(Job(
                    company=company,
                    title=title,
                    location=location,
                    url=job_url,
                    description=description,
                    date_posted=date_posted,
                    source="adzuna",
                ))

            time.sleep(DELAY)

    logger.info(f"Adzuna: found {len(all_jobs)} matching jobs.")
    return all_jobs
