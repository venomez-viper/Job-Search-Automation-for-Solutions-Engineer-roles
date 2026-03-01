"""
fetchers/workable.py — Fetch jobs from Workable public jobs API.

Public endpoint (no auth required):
  POST https://apply.workable.com/api/v3/accounts/{slug}/jobs

Fixes:
  - 400 errors: many slugs aren't on Workable — skip silently instead of warning
  - 429 rate limiting: back off 5s and retry once
  - 20s timeout (was 10s)
  - 0.5s delay between companies to avoid rate limits
"""
import time
import requests
import logging

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS, WORKABLE_COMPANIES

logger = logging.getLogger(__name__)

BASE_URL = "https://apply.workable.com/api/v3/accounts/{slug}/jobs"
TIMEOUT = 20
DELAY   = 0.5

_POST_BODY = {"query": "", "location": [], "department": [], "worktype": [], "remote": False}


def fetch_workable() -> list[Job]:
    """Fetch and filter jobs from all configured Workable companies."""
    all_jobs: list[Job] = []

    for slug in WORKABLE_COMPANIES:
        try:
            url = BASE_URL.format(slug=slug)
            resp = requests.post(url, json=_POST_BODY, timeout=TIMEOUT)

            # 400/404/403 = company not on Workable or slug is wrong — skip quietly
            if resp.status_code in (400, 404, 403, 410, 422):
                logger.debug(f"Workable: {slug} not found ({resp.status_code}), skipping.")
                time.sleep(DELAY)
                continue

            # Rate limited — back off and retry once
            if resp.status_code == 429:
                logger.warning(f"Workable: rate limited, waiting 5s...")
                time.sleep(5)
                resp = requests.post(url, json=_POST_BODY, timeout=TIMEOUT)
                if resp.status_code != 200:
                    time.sleep(DELAY)
                    continue

            resp.raise_for_status()
            data = resp.json()

        except requests.exceptions.Timeout:
            logger.warning(f"Workable: {slug} timed out, skipping.")
            time.sleep(DELAY)
            continue
        except Exception as e:
            logger.warning(f"Workable fetch failed for {slug}: {e}")
            time.sleep(DELAY)
            continue

        results = data.get("results") or data.get("jobs") or []

        for job in results:
            title = job.get("title", "")
            location_info = job.get("location", {}) or {}
            city    = location_info.get("city", "")
            country = location_info.get("country_code", "") or location_info.get("country", "")
            remote  = job.get("remote", False)

            if remote:
                location = "Remote"
            elif city:
                location = f"{city}, {country}".strip(", ")
            else:
                location = country or ""

            shortcode = job.get("shortcode", "")
            job_url = f"https://apply.workable.com/{slug}/j/{shortcode}/" if shortcode else ""
            description_raw = job.get("description", "") or job.get("full_description", "") or ""
            published = job.get("published_on", "") or job.get("created_at", "")
            date_posted = published[:10] if published else ""

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

        time.sleep(DELAY)

    logger.info(f"Workable: found {len(all_jobs)} matching jobs.")
    return all_jobs
