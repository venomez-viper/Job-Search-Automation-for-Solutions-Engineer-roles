"""
fetchers/lever.py — Fetch jobs from Lever public postings API.

Public endpoint (no auth required):
  GET https://api.lever.co/v0/postings/{company}?mode=json

Fixes:
  - 20s timeout (was 10s — caused timeouts on slow companies)
  - 0.3s delay between requests to avoid rate limiting
  - Smarter 404/410 detection skips bad slugs silently
"""
import time
import requests
import logging
from datetime import datetime

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS, LEVER_COMPANIES

logger = logging.getLogger(__name__)

BASE_URL = "https://api.lever.co/v0/postings/{slug}?mode=json"
TIMEOUT = 20       # seconds per request
DELAY   = 0.3      # seconds between requests (avoid rate limits)


def fetch_lever() -> list[Job]:
    """Fetch and filter jobs from all configured Lever companies."""
    all_jobs: list[Job] = []

    for slug in LEVER_COMPANIES:
        try:
            url = BASE_URL.format(slug=slug)
            resp = requests.get(url, timeout=TIMEOUT)
            if resp.status_code in (404, 403, 410, 422):
                logger.debug(f"Lever: {slug} not found ({resp.status_code}), skipping.")
                time.sleep(DELAY)
                continue
            if resp.status_code == 429:
                logger.warning(f"Lever: rate limited on {slug}, waiting 5s...")
                time.sleep(5)
                resp = requests.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            postings = resp.json()
        except requests.exceptions.Timeout:
            logger.warning(f"Lever: {slug} timed out after {TIMEOUT}s, skipping.")
            time.sleep(DELAY)
            continue
        except Exception as e:
            logger.warning(f"Lever fetch failed for {slug}: {e}")
            time.sleep(DELAY)
            continue

        if not isinstance(postings, list):
            time.sleep(DELAY)
            continue

        for post in postings:
            title = post.get("text", "")
            categories = post.get("categories", {}) or {}
            location = categories.get("location", "") or post.get("workplaceType", "")
            job_url = post.get("hostedUrl", "")

            # Build description from structured sections
            lists_data = post.get("lists", []) or []
            description_parts = []
            for lst in lists_data:
                description_parts.append(lst.get("text", ""))
                description_parts.append(lst.get("content", ""))
            additional = post.get("additional", "") or ""
            description_raw = " ".join(description_parts) + " " + additional

            created_at = post.get("createdAt", 0)
            date_posted = _ts_to_date(created_at)

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
                source="lever",
            ))

        time.sleep(DELAY)

    logger.info(f"Lever: found {len(all_jobs)} matching jobs.")
    return all_jobs


def _ts_to_date(ts) -> str:
    """Convert millisecond Unix timestamp to YYYY-MM-DD string."""
    try:
        if not ts:
            return ""
        ts_sec = int(ts) / 1000
        return datetime.utcfromtimestamp(ts_sec).strftime("%Y-%m-%d")
    except Exception:
        return ""
