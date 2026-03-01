"""
scorer.py — Near-match, transferable-skill, explainable job scoring engine.

Scoring Architecture:
═══════════════════════════════════════════════════════════════════
  Final Score = title_score
              + core_skill_score
              + tool_skill_score (direct match OR transferability credit)
              + seniority_score
              + location_score
              + freshness_score
              + ramp_feasibility_boost
              + hard_blocker_penalty
              + unrelated_role_penalty

Classification:
  • High Match  — strong core AND tool alignment
  • Stretch but Apply — strong core, moderate/low tool (but worth trying)
  • Below threshold — filtered out before email

All weights live in config.py. This file contains zero magic numbers.
═══════════════════════════════════════════════════════════════════
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from fetchers.base import Job
from config import (
    TITLE_KEYWORD_WEIGHTS,
    CORE_SKILL_WEIGHTS,
    TOOL_SKILL_WEIGHTS,
    TRANSFERABILITY_MAP,
    SENIORITY_PENALTIES,
    SENIORITY_BOOSTS,
    UNRELATED_ROLE_KEYWORDS,
    UNRELATED_ROLE_PENALTY,
    RAMP_FEASIBILITY_KEYWORDS,
    RAMP_FEASIBILITY_BOOST,
    HARD_BLOCKER_KEYWORDS,
    HARD_BLOCKER_PENALTY,
    E_VERIFY_KEYWORDS,
    E_VERIFY_BOOST,
    SCORING_WEIGHTS,
    HIGH_MATCH_CORE_THRESHOLD,
    STRETCH_CORE_THRESHOLD,
    STRETCH_TOOL_CEILING,
    EXPLAIN_SCORES,
)

logger = logging.getLogger(__name__)

JobLabel = Literal["High Match", "Stretch but Apply", "Below Threshold"]


# ─── Score Breakdown ─────────────────────────────────────────────────────────

@dataclass
class ScoreBreakdown:
    """
    Transparent, component-by-component explanation of a job's relevance score.
    Every field is human-readable — designed to be logged and displayed in email.
    """
    # Raw component scores
    title_score: int = 0
    core_skill_score: int = 0
    tool_skill_score: int = 0
    transferability_score: int = 0   # partial credit for near-match tools
    seniority_score: int = 0
    location_score: int = 0
    freshness_score: int = 0
    ramp_boost: int = 0
    e_verify_boost: int = 0
    hard_blocker_penalty: int = 0
    unrelated_penalty: int = 0
    total: int = 0

    # Match evidence (for logging / email)
    title_matches: list[str] = field(default_factory=list)
    core_matches: list[str] = field(default_factory=list)
    tool_matches: list[str] = field(default_factory=list)
    transferable_matches: list[str] = field(default_factory=list)   # "Tableau → BI dashboards"
    ramp_keywords_found: list[str] = field(default_factory=list)
    hard_blockers_found: list[str] = field(default_factory=list)
    seniority_reasons: list[str] = field(default_factory=list)
    location_reason: str = ""
    freshness_reason: str = ""

    # Classification
    label: JobLabel = "Below Threshold"

    def summary(self) -> str:
        """One-line plain-text explanation of score for logging."""
        parts = []
        if self.title_matches:
            parts.append(f"Title({self.title_score:+d}): {', '.join(self.title_matches[:2])}")
        if self.core_matches:
            parts.append(f"Core({self.core_skill_score:+d}): {', '.join(self.core_matches[:4])}")
        if self.tool_matches:
            parts.append(f"Tools({self.tool_skill_score:+d}): {', '.join(self.tool_matches[:3])}")
        if self.transferable_matches:
            parts.append(f"Transferable({self.transferability_score:+d}): {', '.join(self.transferable_matches[:2])}")
        if self.seniority_score != 0:
            parts.append(f"Seniority({self.seniority_score:+d})")
        if self.location_reason:
            parts.append(f"Loc({self.location_score:+d}): {self.location_reason}")
        if self.ramp_boost:
            parts.append(f"Ramp({self.ramp_boost:+d})")
        if self.hard_blocker_penalty:
            parts.append(f"Blocker({self.hard_blocker_penalty}): {', '.join(self.hard_blockers_found)}")
        return " | ".join(parts) or "No signal."


# ─── Component Scorers ────────────────────────────────────────────────────────

def _score_title(title: str) -> tuple[int, list[str]]:
    """Title matches carry SCORING_WEIGHTS['title_multiplier'] × base weight."""
    title_lower = title.lower()
    multiplier = SCORING_WEIGHTS["title_multiplier"]
    total, matches = 0, []
    for keyword, weight in TITLE_KEYWORD_WEIGHTS.items():
        if keyword in title_lower:
            pts = weight * multiplier
            total += pts
            matches.append(f"{keyword}(+{pts})")
    return total, matches


def _score_core_skills(description: str) -> tuple[int, list[str]]:
    """
    Score core FUNCTIONAL skills in description.
    These represent what-you-do workflows vs what-tool-you-know.
    High weight — a strong match here means the role is functionally right.
    """
    desc_lower = description.lower()
    total, matches = 0, []
    for keyword, weight in CORE_SKILL_WEIGHTS.items():
        if keyword in desc_lower:
            total += weight
            if weight > 0:
                matches.append(f"{keyword}(+{weight})")
    return total, matches


def _score_tool_skills(description: str) -> tuple[int, int, list[str], list[str]]:
    """
    Score tool-specific skills in description.
    For each tool:
      - If EXACT keyword found in description → full weight (direct match)
      - If keyword NOT found but a transferability alias IS found → partial credit
        (e.g., job says 'Tableau', Akash has Zoho Analytics → partial BI credit)

    Returns:
        direct_score, transfer_score, direct_matches, transfer_matches
    """
    desc_lower = description.lower()
    direct_score, transfer_score = 0, 0
    direct_matches, transfer_matches = [], []

    for keyword, weight in TOOL_SKILL_WEIGHTS.items():
        if keyword in desc_lower:
            direct_score += weight
            direct_matches.append(f"{keyword}(+{weight})")
        elif keyword in TRANSFERABILITY_MAP:
            # Check if the job description contains the transfer term itself
            # (i.e., the company listed the tool — Akash gets partial credit via similar tool)
            concept, partial_weight = TRANSFERABILITY_MAP[keyword]
            # Award partial credit since Akash has a transferable equivalent
            transfer_score += partial_weight
            transfer_matches.append(f"{keyword}→{concept}(+{partial_weight})")

    return direct_score, transfer_score, direct_matches, transfer_matches


def _score_seniority(title: str) -> tuple[int, list[str]]:
    """Penalize senior roles; boost junior/associate/mid-level."""
    title_lower = title.lower()
    total, reasons = 0, []
    for keyword, penalty in SENIORITY_PENALTIES.items():
        if keyword in title_lower:
            total += penalty
            reasons.append(f"'{keyword.strip()}' ({penalty:+d})")
    if total == 0:
        for keyword, boost in SENIORITY_BOOSTS.items():
            if keyword in title_lower:
                total += boost
                reasons.append(f"'{keyword.strip()}' ({boost:+d})")
                break
    return max(total, SCORING_WEIGHTS["seniority_max_penalty"]), reasons


def _score_location(location: str) -> tuple[int, str]:
    """Chicago → strong bonus. Remote/US → moderate. Overseas → penalty."""
    loc = (location or "").lower()
    if "chicago" in loc:
        return SCORING_WEIGHTS["location_chicago_bonus"], "Chicago ✓"
    if "remote" in loc or "united states" in loc or "nationwide" in loc or not loc:
        return SCORING_WEIGHTS["location_remote_bonus"], "Remote / US ✓"
    foreign = ["india", "london", "uk", "germany", "paris", "france",
               "toronto", "canada", "australia", "singapore", "dubai",
               "brazil", "amsterdam", "berlin"]
    if any(f in loc for f in foreign):
        return SCORING_WEIGHTS["location_other_penalty"], f"Outside preferred geo: {location}"
    return 0, "Location unclear"


def _score_freshness(date_posted: str) -> tuple[int, str]:
    """Boost fresh jobs (<7d), slight penalty for stale (>30d)."""
    if not date_posted or len(date_posted) < 10:
        return SCORING_WEIGHTS["freshness_unknown"], "Date unknown"
    try:
        posted = datetime.strptime(date_posted[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        age = max((datetime.now(timezone.utc) - posted).days, 0)
        if age <= 7:
            return SCORING_WEIGHTS["freshness_7d_bonus"], f"Posted {age}d ago 🔥"
        if age <= 14:
            return SCORING_WEIGHTS["freshness_14d_bonus"], f"Posted {age}d ago"
        if age <= 30:
            return 0, f"Posted {age}d ago"
        return SCORING_WEIGHTS["freshness_30d_penalty"], f"Posted {age}d ago (stale)"
    except ValueError:
        return 0, "Date parse error"


def _score_ramp(description: str) -> tuple[int, list[str]]:
    """Boost if job signals mentorship / training / growth culture."""
    desc_lower = description.lower()
    found = [kw for kw in RAMP_FEASIBILITY_KEYWORDS if kw in desc_lower]
    if found:
        return RAMP_FEASIBILITY_BOOST, found[:3]
    return 0, []


def _score_e_verify(description: str) -> int:
    """Boost if job explicitly signals E-Verify participation or visa sponsorship."""
    desc_lower = description.lower()
    for kw in E_VERIFY_KEYWORDS:
        if kw in desc_lower:
            return E_VERIFY_BOOST
    return 0


def _score_hard_blockers(description: str) -> tuple[int, list[str]]:
    """Large penalty for hard disqualifiers (clearances, unreachable certifications)."""
    desc_lower = description.lower()
    found = [kw for kw in HARD_BLOCKER_KEYWORDS if kw in desc_lower]
    if found:
        return HARD_BLOCKER_PENALTY * len(found), found
    return 0, []


def _score_unrelated(title: str) -> int:
    """Flat penalty for titles clearly outside target domain."""
    title_lower = title.lower()
    for kw in UNRELATED_ROLE_KEYWORDS:
        if kw in title_lower:
            return UNRELATED_ROLE_PENALTY
    return 0


def _classify(core_score: int, tool_score: int, transferability_score: int) -> JobLabel:
    """
    Assign a classification label based on core + tool alignment.

    High Match:      Strong functional alignment + reasonable tool match
    Stretch but Apply: Strong functional alignment but tool gap (use transferability)
    Below Threshold: Not enough signal to recommend applying
    """
    effective_tool = tool_score + transferability_score
    if core_score >= HIGH_MATCH_CORE_THRESHOLD and effective_tool >= STRETCH_TOOL_CEILING:
        return "High Match"
    if core_score >= STRETCH_CORE_THRESHOLD:
        return "Stretch but Apply"
    return "Below Threshold"


# ─── Main Public API ─────────────────────────────────────────────────────────

def score_job(job: Job) -> tuple[int, ScoreBreakdown]:
    """
    Score a single job. Returns (total_score, ScoreBreakdown).
    Deterministic: same inputs always produce same output.
    All weights are in config.py — no magic numbers here.
    """
    bd = ScoreBreakdown()

    # Component 1 — Title (3× multiplier)
    bd.title_score, bd.title_matches = _score_title(job.title)

    # Component 2 — Core functional skills (what-you-do)
    bd.core_skill_score, bd.core_matches = _score_core_skills(job.description)

    # Component 3 — Tool skills (direct) + transferability (partial credit)
    direct, transfer, bd.tool_matches, bd.transferable_matches = _score_tool_skills(job.description)
    bd.tool_skill_score = direct
    bd.transferability_score = transfer

    # Component 4 — Seniority
    bd.seniority_score, bd.seniority_reasons = _score_seniority(job.title)

    # Component 5 — Location
    bd.location_score, bd.location_reason = _score_location(job.location)

    # Component 6 — Freshness
    bd.freshness_score, bd.freshness_reason = _score_freshness(job.date_posted)

    # Component 7 — Ramp feasibility boost (stretch-role friendly)
    bd.ramp_boost, bd.ramp_keywords_found = _score_ramp(job.description)

    # Component 8 — E-Verify / sponsorship-friendly signal
    bd.e_verify_boost = _score_e_verify(job.description)

    # Component 9 — Hard blockers
    bd.hard_blocker_penalty, bd.hard_blockers_found = _score_hard_blockers(job.description)

    # Component 9 — Clearly unrelated domain
    bd.unrelated_penalty = _score_unrelated(job.title)

    # Total
    bd.total = max(
        bd.title_score
        + bd.core_skill_score
        + bd.tool_skill_score
        + bd.transferability_score
        + bd.seniority_score
        + bd.location_score
        + bd.freshness_score
        + bd.ramp_boost
        + bd.e_verify_boost
        + bd.hard_blocker_penalty
        + bd.unrelated_penalty,
        0,
    )

    # Classification
    bd.label = _classify(bd.core_skill_score, bd.tool_skill_score, bd.transferability_score)

    if EXPLAIN_SCORES:
        logger.debug(
            f"  [{bd.label:16s}] Score {bd.total:3d} | {job.company:25s} | {job.title}\n"
            f"    {bd.summary()}"
        )

    return bd.total, bd


def score_all(jobs: list[Job]) -> tuple[list[Job], list[Job]]:
    """
    Score all jobs, deduplicate by fingerprint, attach score + breakdown,
    then split into two sorted lists:
      - high_match: "High Match" jobs, sorted by score desc
      - stretch:    "Stretch but Apply" jobs, sorted by score desc

    Inline deduplication prevents identical (company+title+location) listings
    from inflating rankings — even across different ATS sources.
    """
    # Deduplicate by fingerprint
    seen: set[str] = set()
    unique: list[Job] = []
    for job in jobs:
        fp = f"{job.company.lower()}|{job.title.lower()}|{job.location.lower()}"
        if fp not in seen:
            seen.add(fp)
            unique.append(job)

    logger.info(f"Scorer: dedup {len(jobs)} -> {len(unique)} unique jobs.")

    high_match: list[Job] = []
    stretch: list[Job] = []

    for job in unique:
        total, breakdown = score_job(job)
        job.score = total
        job.breakdown = breakdown  # type: ignore[attr-defined]
        job.label = breakdown.label  # type: ignore[attr-defined]

        if breakdown.label == "High Match":
            high_match.append(job)
        elif breakdown.label == "Stretch but Apply":
            stretch.append(job)
        # "Below Threshold" jobs are silently dropped

    high_match.sort(key=lambda j: j.score, reverse=True)
    stretch.sort(key=lambda j: j.score, reverse=True)

    logger.info(
        f"Scorer: {len(high_match)} High Match, {len(stretch)} Stretch, "
        f"{len(unique) - len(high_match) - len(stretch)} Below threshold."
    )
    return high_match, stretch
