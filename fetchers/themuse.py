"""
fetchers/themuse.py — Fetch jobs from The Muse public API.

Free public API, no auth required.
Endpoint: https://www.themuse.com/api/public/jobs
"""
import requests
import logging
import time

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS

logger = logging.getLogger(__name__)

BASE_URL = "https://www.themuse.com/api/public/jobs"
TIMEOUT = 20
DELAY   = 0.5

# The Muse category IDs relevant to SE/pre-sales
CATEGORIES = ["Account Management", "Sales", "IT", "Software Engineer", "Data Science"]


def fetch_themuse() -> list[Job]:
    """Fetch SE/pre-sales jobs from The Muse."""
    all_jobs: list[Job] = []
    seen_urls: set[str] = set()

    for category in CATEGORIES:
        for page in range(0, 3):   # pages 0, 1, 2 = up to 60 jobs per category
            try:
                resp = requests.get(
                    BASE_URL,
                    params={"category": category, "page": page, "descending": "true"},
                    timeout=TIMEOUT,
                )
                if resp.status_code != 200:
                    break
                data = resp.json()
                jobs = data.get("results", [])
                if not jobs:
                    break
            except Exception as e:
                logger.warning(f"The Muse fetch failed (category={category}, page={page}): {e}")
                break

            for job in jobs:
                title = job.get("name", "")
                publication_date = (job.get("publication_date") or "")[:10]
                job_url = job.get("refs", {}).get("landing_page", "")

                # Location
                locations = job.get("locations", []) or []
                location = locations[0].get("name", "") if locations else "Remote"
                if "flexible" in location.lower() or not location:
                    location = "Remote"

                # Company
                company_info = job.get("company", {}) or {}
                company = company_info.get("name", "")

                # Description (short + body)
                contents = job.get("contents", "") or ""
                description = clean_html(contents)[:3000]

                if not title_matches_targets(title, TARGET_TITLES):
                    continue
                if title_excluded(title, EXCLUDE_TITLE_KEYWORDS):
                    continue
                if not location_allowed(location, ALLOWED_LOCATIONS):
                    continue
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                all_jobs.append(Job(
                    company=company,
                    title=title,
                    location=location,
                    url=job_url,
                    description=description,
                    date_posted=publication_date,
                    source="themuse",
                ))

            time.sleep(DELAY)

    logger.info(f"The Muse: found {len(all_jobs)} matching jobs.")
    return all_jobs
