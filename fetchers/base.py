"""
fetchers/base.py — Shared Job dataclass and utility helpers.
"""
from dataclasses import dataclass, field
from typing import Optional
import re


@dataclass
class Job:
    """Normalized job record across all ATS sources."""
    company: str
    title: str
    location: str
    url: str
    description: str
    date_posted: str
    source: str          # 'greenhouse' | 'lever' | 'ashby' | 'workable'
    score: int = 0       # filled in by scorer.py

    def __hash__(self):
        return hash(self.url)

    def __eq__(self, other):
        return isinstance(other, Job) and self.url == other.url


def clean_html(raw: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_location(loc: str) -> str:
    """Lowercase and strip location string."""
    return (loc or "").strip().lower()


def title_matches_targets(title: str, target_titles: list[str]) -> bool:
    """Check if a job title matches any of our target role keywords."""
    title_lower = title.lower()
    return any(t in title_lower for t in target_titles)


def title_excluded(title: str, exclude_keywords: list[str]) -> bool:
    """Return True if title contains any seniority exclusion keyword."""
    title_lower = title.lower()
    return any(kw in title_lower for kw in exclude_keywords)


def location_allowed(loc: str, allowed_locations: list[str]) -> bool:
    """Return True if the location matches our allowed list."""
    loc_lower = normalize_location(loc)
    if not loc_lower:
        return True  # blank = likely remote
    return any(a in loc_lower for a in allowed_locations if a)
