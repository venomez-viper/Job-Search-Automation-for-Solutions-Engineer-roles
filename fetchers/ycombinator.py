"""
fetchers/ycombinator.py — Fetch jobs from Y Combinator's Work at a Startup board.

Public endpoint (no auth required):
  https://www.workatastartup.com/jobs (HTML, parsed from JSON in page)

Alternative: Use Algolia search which powers the site.
"""
import requests
import logging
import time

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS

logger = logging.getLogger(__name__)
TIMEOUT = 20
DELAY = 0.5

# YC uses Algolia to power their job search
ALGOLIA_URL = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/WaaS_Job_Production/query"
ALGOLIA_APP_ID = "45BWZJ1SGC"
ALGOLIA_API_KEY = "Zjk5ZmUyNTk4YTNhZTY3NGExMmZlMDVlMTk4NWQ5OGFlZWUxNjVmYjE4NWI4MjM4NmQ3NThjMGU4MDUzYTI3NXZhbGlkVW50aWw9MTc3MzUyNzYwMCZmaWx0ZXJzPXN0YXR1cyUzQUFjdGl2ZQ=="

SEARCH_TERMS = [
    "solutions engineer",
    "sales engineer",
    "pre-sales",
    "solution consultant",
]


def fetch_ycombinator() -> list[Job]:
    """Fetch SE/pre-sales jobs from Y Combinator's Work at a Startup board."""
    all_jobs: list[Job] = []
    seen_ids: set[str] = set()

    headers = {
        "X-Algolia-Application-Id": ALGOLIA_APP_ID,
        "X-Algolia-API-Key": ALGOLIA_API_KEY,
        "Content-Type": "application/json",
    }

    for term in SEARCH_TERMS:
        try:
            resp = requests.post(
                ALGOLIA_URL,
                headers=headers,
                json={"query": term, "hitsPerPage": 50, "page": 0},
                timeout=TIMEOUT,
            )
            if resp.status_code != 200:
                logger.debug(f"YC: '{term}' returned {resp.status_code}")
                time.sleep(DELAY)
                continue

            hits = resp.json().get("hits", [])
        except Exception as e:
            logger.warning(f"YC fetch failed for '{term}': {e}")
            time.sleep(DELAY)
            continue

        for hit in hits:
            job_id = str(hit.get("objectID", ""))
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            title = hit.get("job_name", "") or hit.get("title", "")
            company = hit.get("company_name", "") or hit.get("name", "")
            location = hit.get("job_locations", [""])[0] if hit.get("job_locations") else "Remote"
            job_url = f"https://www.workatastartup.com/jobs/{job_id}"
            description = clean_html(hit.get("job_description", "") or "")[:3000]
            date_posted = (hit.get("created_at") or "")[:10]

            if not location:
                location = "Remote"
            if "remote" in (hit.get("job_type", "") or "").lower():
                location = "Remote"

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
                source="ycombinator",
            ))

        time.sleep(DELAY)

    logger.info(f"YCombinator: found {len(all_jobs)} matching jobs.")
    return all_jobs
