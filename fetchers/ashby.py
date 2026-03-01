"""
fetchers/ashby.py — Fetch jobs from Ashby public job board API.

Public endpoint (no auth required):
  POST https://api.ashbyhq.com/posting-public/graphql
  or
  GET  https://{company}.ashbyhq.com/api/jobs  (fallback)
"""
import requests
import logging
from datetime import datetime

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS, ASHBY_COMPANIES

logger = logging.getLogger(__name__)

GRAPHQL_URL = "https://api.ashbyhq.com/posting-public/graphql"

QUERY = """
query jobPostings($companySlug: String!) {
  jobPostings(organizationHostedJobsPageName: $companySlug) {
    title
    locationName
    jobPostingState
    externalLink
    descriptionHtml
    publishedDate
    isRemote
    employmentType
  }
}
"""


def fetch_ashby() -> list[Job]:
    """Fetch and filter jobs from all configured Ashby companies."""
    all_jobs: list[Job] = []

    headers = {"Content-Type": "application/json"}

    for slug in ASHBY_COMPANIES:
        try:
            payload = {
                "query": QUERY,
                "variables": {"companySlug": slug},
            }
            resp = requests.post(GRAPHQL_URL, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.warning(f"Ashby fetch failed for {slug}: {e}")
            continue

        errors = data.get("errors")
        if errors:
            logger.debug(f"Ashby GraphQL errors for {slug}: {errors}")
            continue

        postings = (data.get("data") or {}).get("jobPostings") or []

        for post in postings:
            title = post.get("title", "")
            location = post.get("locationName", "")
            is_remote = post.get("isRemote", False)
            if is_remote and not location:
                location = "Remote"
            job_url = post.get("externalLink", "") or f"https://{slug}.ashbyhq.com/jobs"
            description_raw = post.get("descriptionHtml", "") or ""
            published = post.get("publishedDate", "")
            state = post.get("jobPostingState", "")

            # Only live postings
            if state and state.lower() != "published":
                continue

            # Filter
            if not title_matches_targets(title, TARGET_TITLES):
                continue
            if title_excluded(title, EXCLUDE_TITLE_KEYWORDS):
                continue
            if not location_allowed(location, ALLOWED_LOCATIONS):
                continue

            company_name = slug.replace("-", " ").replace("_", " ").title()
            date_posted = published[:10] if published else ""

            all_jobs.append(Job(
                company=company_name,
                title=title,
                location=location or "Remote",
                url=job_url,
                description=clean_html(description_raw)[:3000],
                date_posted=date_posted,
                source="ashby",
            ))

    logger.info(f"Ashby: found {len(all_jobs)} matching jobs.")
    return all_jobs
