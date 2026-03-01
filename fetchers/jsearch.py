"""
fetchers/jsearch.py — Fetch jobs from JSearch API (RapidAPI).

JSearch is a legal aggregator that pulls from LinkedIn, Indeed, Glassdoor, ZipRecruiter.
Free tier: 500 requests/month — plenty for daily runs.

Setup:
  1. Go to https://rapidapi.com/openwebninja/api/jsearch (search 'jsearch' on rapidapi.com)
  2. Sign up free → Subscribe (Basic plan = 500 req/month free)
  3. Copy your API key → add as JSEARCH_API_KEY in GitHub Secrets

If JSEARCH_API_KEY is not set, this fetcher is silently skipped.
"""
import os
import time
import requests
import logging

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS

logger = logging.getLogger(__name__)

BASE_URL = "https://jsearch.p.rapidapi.com/search"   # endpoint unchanged
TIMEOUT  = 20
DELAY    = 1.0   # JSearch free tier rate limit is low — be polite

# Search queries to run (each uses 1 API call)
SEARCH_QUERIES = [
    "Solutions Engineer Chicago",
    "Solutions Engineer Remote USA",
    "Pre-Sales Engineer Chicago",
    "Pre-Sales Engineer Remote USA",
    "Sales Engineer Chicago",
    "Sales Engineer Remote USA",
    "Solution Consultant Remote USA",
]


def fetch_jsearch() -> list[Job]:
    """Fetch jobs from LinkedIn/Indeed/Glassdoor via JSearch API."""
    api_key = os.environ.get("JSEARCH_API_KEY", "")
    if not api_key:
        logger.info("JSearch: JSEARCH_API_KEY not set — skipping. (Add it to GitHub Secrets for LinkedIn/Indeed coverage)")
        return []

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",   # host unchanged — same as before
    }

    all_jobs: list[Job] = []
    seen_urls: set[str] = set()

    for query in SEARCH_QUERIES:
        try:
            resp = requests.get(
                BASE_URL,
                headers=headers,
                params={
                    "query": query,
                    "page": "1",
                    "num_pages": "2",
                    "date_posted": "month",
                    "employment_types": "FULLTIME",
                },
                timeout=TIMEOUT,
            )

            if resp.status_code == 429:
                logger.warning("JSearch: rate limited — waiting 10s...")
                time.sleep(10)
                time.sleep(DELAY)
                continue

            if resp.status_code != 200:
                logger.warning(f"JSearch: query '{query}' returned {resp.status_code}")
                time.sleep(DELAY)
                continue

            jobs = resp.json().get("data", [])

        except Exception as e:
            logger.warning(f"JSearch fetch failed for '{query}': {e}")
            time.sleep(DELAY)
            continue

        for job in jobs:
            title      = job.get("job_title", "")
            company    = job.get("employer_name", "")
            location   = _build_location(job)
            job_url    = job.get("job_apply_link", "") or job.get("job_google_link", "")
            description = clean_html(job.get("job_description", "") or "")[:3000]
            date_posted = (job.get("job_posted_at_datetime_utc") or "")[:10]

            if not title_matches_targets(title, TARGET_TITLES):
                continue
            if title_excluded(title, EXCLUDE_TITLE_KEYWORDS):
                continue
            if not location_allowed(location, ALLOWED_LOCATIONS):
                continue
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)

            source = job.get("job_publisher", "jsearch").lower().replace(" ", "-")

            all_jobs.append(Job(
                company=company,
                title=title,
                location=location,
                url=job_url,
                description=description,
                date_posted=date_posted,
                source=source,  # "linkedin", "indeed", "glassdoor", etc.
            ))

        time.sleep(DELAY)

    logger.info(f"JSearch: found {len(all_jobs)} matching jobs across LinkedIn/Indeed/Glassdoor.")
    return all_jobs


def _build_location(job: dict) -> str:
    """Build a clean location string from JSearch job data."""
    remote = job.get("job_is_remote", False)
    if remote:
        return "Remote"
    city    = job.get("job_city", "") or ""
    state   = job.get("job_state", "") or ""
    country = job.get("job_country", "") or ""
    if city and state:
        return f"{city}, {state}"
    if city:
        return city
    if state:
        return state
    return country or "Remote"
