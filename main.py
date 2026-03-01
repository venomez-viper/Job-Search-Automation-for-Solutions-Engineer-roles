"""
main.py — Job Hunt Automation Orchestrator.

Usage:
  python main.py            # Full run (fetch, score, email, log to Sheets)
  python main.py --dry-run  # Print results only, no email / Sheets writes
  python main.py --email-test  # Send a test email with dummy data
"""
import argparse
import logging
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from fetchers.greenhouse import fetch_greenhouse
from fetchers.lever import fetch_lever
from fetchers.ashby import fetch_ashby
from fetchers.workable import fetch_workable
from fetchers.remotive import fetch_remotive
from fetchers.themuse import fetch_themuse
from fetchers.jsearch import fetch_jsearch
from fetchers.ycombinator import fetch_ycombinator
from fetchers.himalayas import fetch_himalayas
from fetchers.adzuna import fetch_adzuna
from fetchers.hackernews import fetch_hackernews
from scorer import score_all
from deduper import filter_new_jobs, mark_seen, get_seen_count
from notifier import send_email
from sheets import log_to_sheets
from config import (
    MIN_JOBS_PER_RUN,
    MAX_JOBS_PER_RUN,
    MIN_SCORE_THRESHOLD,
    MAX_HIGH_MATCH,
    MAX_STRETCH,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("job_hunt.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("main")


def _select_jobs(high_match: list, stretch: list) -> list:
    """
    Pick up to MAX_JOBS_PER_RUN jobs prioritizing High Match,
    then filling remaining slots with Stretch but Apply.
    """
    selected_high = high_match[:MAX_HIGH_MATCH]
    remaining_slots = MAX_JOBS_PER_RUN - len(selected_high)
    selected_stretch = stretch[:min(MAX_STRETCH, remaining_slots)]
    return selected_high + selected_stretch


def run(dry_run: bool = False) -> None:
    start = datetime.now()
    logger.info("=" * 60)
    logger.info(f"Job Hunt Automation — {start.strftime('%Y-%m-%d %H:%M')}")
    logger.info(f"Total seen jobs in DB: {get_seen_count()}")
    logger.info("=" * 60)

    # ── 1. Fetch ──────────────────────────────────────────────────────────
    all_jobs = []
    for fetcher_name, fetcher_fn in [
        ("Greenhouse",   fetch_greenhouse),
        ("Lever",        fetch_lever),
        ("Ashby",        fetch_ashby),
        ("Workable",     fetch_workable),
        ("Remotive",     fetch_remotive),
        ("The Muse",     fetch_themuse),
        ("JSearch",      fetch_jsearch),
        ("YCombinator",  fetch_ycombinator),
        ("Himalayas",    fetch_himalayas),
        ("Adzuna",       fetch_adzuna),
        ("HackerNews",   fetch_hackernews),
    ]:
        try:
            jobs = fetcher_fn()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"{fetcher_name} fetch failed: {e}")

    logger.info(f"Total raw jobs fetched: {len(all_jobs)}")

    # ── 2. Score + classify → High Match / Stretch ────────────────────────
    logger.info("Scoring and classifying jobs...")
    high_match, stretch = score_all(all_jobs)

    # ── 3. Apply minimum score filter ────────────────────────────────────
    high_match = [j for j in high_match if j.score >= MIN_SCORE_THRESHOLD]
    stretch    = [j for j in stretch    if j.score >= MIN_SCORE_THRESHOLD]

    # ── 4. Deduplicate against seen DB ────────────────────────────────────
    logger.info("Filtering previously seen jobs...")
    high_match = filter_new_jobs(high_match)
    stretch    = filter_new_jobs(stretch)

    # ── 5. Select final 10-15 jobs ────────────────────────────────────────
    top_jobs = _select_jobs(high_match, stretch)

    logger.info(
        f"Selected {len(top_jobs)} jobs: "
        f"{sum(1 for j in top_jobs if getattr(j, 'label', '') == 'High Match')} High Match, "
        f"{sum(1 for j in top_jobs if getattr(j, 'label', '') == 'Stretch but Apply')} Stretch."
    )

    if len(top_jobs) < MIN_JOBS_PER_RUN:
        logger.warning(
            f"Only {len(top_jobs)} jobs found (target: {MIN_JOBS_PER_RUN}). "
            "Consider adding more companies to config.py."
        )

    if not top_jobs:
        logger.warning("No new jobs today. Exiting.")
        return

    # ── 6. Log to Google Sheets ───────────────────────────────────────────
    log_to_sheets(top_jobs, dry_run=dry_run)

    # ── 7. Send email digest ──────────────────────────────────────────────
    send_email(top_jobs, dry_run=dry_run)

    # ── 8. Mark as seen ───────────────────────────────────────────────────
    if not dry_run:
        mark_seen(top_jobs)

    elapsed = (datetime.now() - start).total_seconds()
    logger.info(f"Done in {elapsed:.1f}s. DB size: {get_seen_count()} seen jobs.")
    logger.info("=" * 60)


def email_test() -> None:
    from fetchers.base import Job
    from scorer import ScoreBreakdown
    bd = ScoreBreakdown(
        title_score=60, core_skill_score=28, tool_skill_score=8,
        transferability_score=4, seniority_score=5, location_score=8,
        freshness_score=5, ramp_boost=4, total=122, label="High Match",
        title_matches=["solutions engineer(+60)"],
        core_matches=["api(+4)", "demo(+4)", "sql(+4)", "dashboard(+3)"],
        tool_matches=["snowflake(+2)", "aws(+2)"],
        transferable_matches=["tableau→bi dashboards(+2)"],
        location_reason="Chicago ✓", freshness_reason="Posted 2d ago 🔥",
        ramp_keywords_found=["mentorship"],
    )
    test_jobs = [
        Job("Acme Analytics", "Solutions Engineer", "Chicago, IL",
            "https://example.com/job/test",
            "API integrations, SQL dashboards, demos, PoC, customer-facing.",
            datetime.now().strftime("%Y-%m-%d"), "test", score=122)
    ]
    test_jobs[0].breakdown = bd   # type: ignore
    test_jobs[0].label = "High Match"  # type: ignore
    logger.info("Sending test email...")
    success = send_email(test_jobs, dry_run=False)
    if success:
        logger.info("✅ Test email sent! Check your inbox.")
    else:
        logger.error("❌ Email failed — check EMAIL_SENDER/EMAIL_PASSWORD in .env")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job Hunt Automation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Fetch, score, print — no email or Sheets writes.")
    parser.add_argument("--email-test", action="store_true",
                        help="Send a test email to verify SMTP config.")
    args = parser.parse_args()

    if args.email_test:
        email_test()
    else:
        run(dry_run=args.dry_run)
