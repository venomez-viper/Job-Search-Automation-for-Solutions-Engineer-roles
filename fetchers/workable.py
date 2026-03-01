"""
fetchers/workable.py — Fetch jobs from Workable public jobs API.

Public endpoint (no auth required):
  GET https://apply.workable.com/api/v3/accounts/{slug}/jobs
"""
import requests
import logging
from datetime import datetime

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS, WORKABLE_COMPANIES

logger = logging.getLogger(__name__)

BASE_URL = "https://apply.workable.com/api/v3/accounts/{slug}/jobs"
JOB_DETAIL_URL = "https://apply.workable.com/api/v3/accounts/{slug}/jobs/{shortcode}"


def fetch_workable() -> list[Job]:
    """Fetch and filter jobs from all configured Workable companies."""
    all_jobs: list[Job] = []

    for slug in WORKABLE_COMPANIES:
        try:
            url = BASE_URL.format(slug=slug)
            resp = requests.post(
                url,
                json={"query": "", "location": [], "department": [], "worktype": [], "remote": False},
                timeout=10,
            )
            if resp.status_code in (404, 403, 422):
                # Try GET as fallback
                resp = requests.get(url, timeout=10)
            if resp.status_code in (404, 403):
                logger.debug(f"Workable: {slug} not found, skipping.")
                continue
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"Workable fetch failed for {slug}: {e}")
            continue

        results = data.get("results") or data.get("jobs") or []

        for job in results:
            title = job.get("title", "")
            location_info = job.get("location", {}) or {}
            location = location_info.get("city", "") or location_info.get("country", "") or ""
            remote = job.get("remote", False)
            if remote:
                location = f"Remote / {location}".strip(" /")

            shortcode = job.get("shortcode", "")
            job_url = f"https://apply.workable.com/{slug}/j/{shortcode}/" if shortcode else ""
            description_raw = job.get("description", "") or job.get("full_description", "") or ""
            published = job.get("published_on", "") or job.get("created_at", "")
            date_posted = published[:10] if published else ""

            # Filter
            if not title_matches_targets(title, TARGET_TITLES):
                continue
            if title_excluded(title, EXCLUDE_TITLE_KEYWORDS):
                continue
            if not location_allowed(location, ALLOWED_LOCATIONS):
                continue

            company_name = slug.replace("-", " ").replace("_", " ").title()

            all_jobs.append(Job(
                company=company_name,
                title=title,
                location=location or "Remote",
                url=job_url,
                description=clean_html(description_raw)[:3000],
                date_posted=date_posted,
                source="workable",
            ))

    logger.info(f"Workable: found {len(all_jobs)} matching jobs.")
    return all_jobs
