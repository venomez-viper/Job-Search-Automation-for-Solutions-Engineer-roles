"""
fetchers/remotive.py — Fetch remote tech jobs from Remotive public API.

Free public API, no auth required.
Endpoint: https://remotive.com/api/remote-jobs
"""
import requests
import logging

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS

logger = logging.getLogger(__name__)

BASE_URL = "https://remotive.com/api/remote-jobs"
TIMEOUT = 20


def fetch_remotive() -> list[Job]:
    """Fetch SE/pre-sales remote jobs from Remotive."""
    all_jobs: list[Job] = []

    # Fetch using relevant categories
    categories = ["software-dev", "product", "sales", "customer-success"]

    for category in categories:
        try:
            resp = requests.get(BASE_URL, params={"category": category, "limit": 100}, timeout=TIMEOUT)
            if resp.status_code != 200:
                logger.debug(f"Remotive: category {category} returned {resp.status_code}")
                continue
            jobs = resp.json().get("jobs", [])
        except Exception as e:
            logger.warning(f"Remotive fetch failed for category {category}: {e}")
            continue

        for job in jobs:
            title = job.get("title", "")
            company = job.get("company_name", "")
            location = job.get("candidate_required_location", "") or "Remote"
            job_url = job.get("url", "")
            description_raw = job.get("description", "") or ""
            date_posted = (job.get("publication_date") or "")[:10]

            # Normalize location for US-only check
            # Remotive is remote-first; allow "Worldwide" and "USA" entries
            loc_lower = location.lower()
            if any(x in loc_lower for x in ["worldwide", "anywhere", "global"]):
                location = "Remote"
            elif "usa" in loc_lower or "united states" in loc_lower or "us only" in loc_lower:
                location = "Remote, United States"
            elif loc_lower and not any(x in loc_lower for x in ["remote", "us", "america"]):
                # Skip clearly non-US
                if any(country in loc_lower for country in [
                    "europe", "uk", "india", "canada", "australia",
                    "germany", "france", "brazil", "asia"
                ]):
                    continue

            if not title_matches_targets(title, TARGET_TITLES):
                continue
            if title_excluded(title, EXCLUDE_TITLE_KEYWORDS):
                continue

            all_jobs.append(Job(
                company=company,
                title=title,
                location=location,
                url=job_url,
                description=clean_html(description_raw)[:3000],
                date_posted=date_posted,
                source="remotive",
            ))

    logger.info(f"Remotive: found {len(all_jobs)} matching jobs.")
    return all_jobs
