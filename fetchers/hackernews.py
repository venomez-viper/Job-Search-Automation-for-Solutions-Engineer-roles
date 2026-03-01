"""
fetchers/hackernews.py — Fetch jobs from HackerNews "Who's Hiring" monthly thread.

Uses the public Algolia HN API — completely free, no auth required.
The "Who's Hiring" thread is posted the first business day of each month
and is a goldmine for startup SE/pre-sales roles.
"""
import requests
import logging
import time
import re
from datetime import datetime

from .base import Job, clean_html, title_matches_targets, title_excluded, location_allowed
from config import TARGET_TITLES, EXCLUDE_TITLE_KEYWORDS, ALLOWED_LOCATIONS

logger = logging.getLogger(__name__)
TIMEOUT = 20

# Algolia HN search API
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
# Stories tagged "Who is hiring" from Ask HN
HN_ITEMS_URL  = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

SE_TERMS = [
    "solutions engineer", "sales engineer", "pre-sales",
    "solution consultant", "presales", "se |", "| se "
]


def _get_latest_whos_hiring_id() -> int | None:
    """Find the most recent 'Ask HN: Who is Hiring?' thread ID."""
    try:
        resp = requests.get(
            HN_SEARCH_URL,
            params={
                "query": "Ask HN: Who is hiring",
                "tags": "ask_hn",
                "hitsPerPage": 5,
            },
            timeout=TIMEOUT,
        )
        hits = resp.json().get("hits", [])
        # Filter to actual "Who is hiring?" posts
        for hit in hits:
            title = hit.get("title", "").lower()
            if "who is hiring" in title and hit.get("author") == "whoishiring":
                return int(hit["objectID"])
        # Fallback: just use first hit
        if hits:
            return int(hits[0]["objectID"])
    except Exception as e:
        logger.warning(f"HN: failed to get Who's Hiring thread: {e}")
    return None


def fetch_hackernews() -> list[Job]:
    """Parse HN Who's Hiring thread for SE/pre-sales job comments."""
    all_jobs: list[Job] = []

    thread_id = _get_latest_whos_hiring_id()
    if not thread_id:
        logger.warning("HN: could not find Who's Hiring thread.")
        return []

    try:
        resp = requests.get(HN_ITEMS_URL.format(id=thread_id), timeout=TIMEOUT)
        thread = resp.json()
        kids = thread.get("kids", [])  # top-level comment IDs
        month_str = datetime.now().strftime("%Y-%m")
    except Exception as e:
        logger.warning(f"HN: failed to fetch thread {thread_id}: {e}")
        return []

    logger.info(f"HN: scanning {len(kids)} comments in Who's Hiring thread #{thread_id}...")

    for comment_id in kids[:300]:   # limit to first 300 comments
        try:
            resp = requests.get(HN_ITEMS_URL.format(id=comment_id), timeout=10)
            comment = resp.json()
            text = comment.get("text", "") or ""
            if not text or comment.get("deleted") or comment.get("dead"):
                continue
        except Exception:
            continue

        # Check if comment mentions relevant job types
        text_lower = text.lower()
        if not any(term in text_lower for term in SE_TERMS):
            continue

        # Extract company name (usually first line before | or :)
        first_line = re.split(r"<br|<p|\|", text)[0]
        company = clean_html(first_line).strip()[:60]
        if not company:
            company = "HN Company"

        # Extract location
        location = "Remote"
        loc_match = re.search(
            r"(chicago|remote|san francisco|new york|nyc|boston|austin|seattle|onsite)",
            text_lower
        )
        if loc_match:
            loc_raw = loc_match.group(1)
            if "chicago" in loc_raw:
                location = "Chicago, IL"
            elif "remote" in loc_raw:
                location = "Remote"

        # Check location filter
        if not location_allowed(location, ALLOWED_LOCATIONS):
            continue

        job_url = f"https://news.ycombinator.com/item?id={comment_id}"
        description = clean_html(text)[:3000]

        # Guess title from context
        title = "Solutions / Sales Engineer"
        for t in ["solutions engineer", "sales engineer", "pre-sales engineer", "solution consultant"]:
            if t in text_lower:
                title = t.title()
                break

        all_jobs.append(Job(
            company=company,
            title=title,
            location=location,
            url=job_url,
            description=description,
            date_posted=month_str + "-01",
            source="hackernews",
        ))

        time.sleep(0.05)  # be polite to HN API

    logger.info(f"HackerNews: found {len(all_jobs)} matching job posts.")
    return all_jobs
