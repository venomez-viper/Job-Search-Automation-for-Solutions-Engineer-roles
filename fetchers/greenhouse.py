"""
fetchers/greenhouse.py — Fetch jobs from Greenhouse public board API.

Public endpoint (no auth required):
  GET https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs?content=true
"""
import requests
import logging
from typing import Optional
from datetime import datetime

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS, GREENHOUSE_COMPANIES

logger = logging.getLogger(__name__)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def fetch_greenhouse() -> list[Job]:
    """Fetch and filter jobs from all configured Greenhouse companies."""
    all_jobs: list[Job] = []

    for slug in GREENHOUSE_COMPANIES:
        try:
            url = BASE_URL.format(slug=slug)
            resp = requests.get(url, params={"content": "true"}, timeout=10)
            if resp.status_code == 404:
                logger.debug(f"Greenhouse: {slug} not found (404), skipping.")
                continue
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"Greenhouse fetch failed for {slug}: {e}")
            continue

        for job in data.get("jobs", []):
            title = job.get("title", "")
            location_info = job.get("location", {}) or {}
            location = location_info.get("name", "")
            job_url = job.get("absolute_url", "")
            description_raw = job.get("content", "")
            updated_at = job.get("updated_at", "")

            # Parse date
            date_posted = _parse_date(updated_at)

            # Filter
            if not title_matches_targets(title, TARGET_TITLES):
                continue
            if title_excluded(title, EXCLUDE_TITLE_KEYWORDS):
                continue
            if not location_allowed(location, ALLOWED_LOCATIONS):
                continue

            # Company name from metadata
            dept = job.get("departments", [])
            company_name = _guess_company_name(slug, data)

            all_jobs.append(Job(
                company=company_name,
                title=title,
                location=location or "Remote",
                url=job_url,
                description=clean_html(description_raw)[:3000],
                date_posted=date_posted,
                source="greenhouse",
            ))

    logger.info(f"Greenhouse: found {len(all_jobs)} matching jobs.")
    return all_jobs


def _parse_date(raw: str) -> str:
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:19], fmt[:len(fmt)]).\
                strftime("%Y-%m-%d")
        except Exception:
            pass
    return raw[:10] if raw else ""


def _guess_company_name(slug: str, data: dict) -> str:
    """Try to extract a clean company name from the API response."""
    # Some boards include metadata
    meta = data.get("meta", {}) or {}
    if meta.get("questions"):
        pass
    # Fall back to prettifying the slug
    return slug.replace("-", " ").replace("_", " ").title()
