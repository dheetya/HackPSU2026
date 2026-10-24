"""Deterministic demographic equity scoring (0–100)."""

from __future__ import annotations

import re
from typing import Any


def _female_pct(data: dict[str, Any]) -> float | None:
    total = data.get("total_sample_size") or 0
    female = data.get("female_participant_count")
    if total <= 0 or female is None:
        return None
    return min(100.0, max(0.0, (female / total) * 100.0))


def _subgroup_keywords_in_limitations(limitations: str) -> int:
    """Count equity-related subgroup mentions in free text (backup signal)."""
    if not limitations:
        return 0
    text = limitations.lower()
    patterns = [
        r"\bage\b",
        r"subgroup",
        r"stratif",
        r"menstrual",
        r"cycle",
        r"hormon",
        r"formulation",
        r"race",
        r"ethnic",
    ]
    return sum(1 for p in patterns if re.search(p, text))


def calculate_equity_score(extraction_data: dict) -> float:
    """
    Grade papers on demographic transparency and women's-health equity reporting.

    Starts at 100 and applies deterministic deductions/rewards.
    """
    score = 100.0

    total_n = int(extraction_data.get("total_sample_size") or 0)
    female_n = extraction_data.get("female_participant_count")
    sex_disagg = bool(extraction_data.get("sex_disaggregated_reported"))
    aes = extraction_data.get("reported_adverse_events") or []
    limitations = str(extraction_data.get("demographic_limitations_noted") or "")

    age_sub = bool(extraction_data.get("age_subgroups_reported"))
    cycle_sub = bool(extraction_data.get("baseline_cycle_irregularities_reported"))
    hormone_sub = bool(extraction_data.get("hormonal_formulation_breakdown"))

    if total_n <= 0:
        score -= 35
    elif total_n < 50:
        score -= 25
    elif total_n < 100:
        score -= 15
    elif total_n < 300:
        score -= 5

    female_pct = _female_pct(extraction_data)

    if female_n is None and total_n > 0:
        score -= 20

    if female_pct is not None:
        if female_pct >= 99 and not sex_disagg and aes:
            score -= 30
        elif female_pct >= 80 and not sex_disagg and aes:
            score -= 22
        elif female_pct >= 50 and not sex_disagg and len(aes) >= 2:
            score -= 15

    if not sex_disagg:
        score -= 12
    else:
        score += 8

    subgroup_points = 0
    if age_sub:
        subgroup_points += 5
    if cycle_sub:
        subgroup_points += 6
    if hormone_sub:
        subgroup_points += 6
    score += subgroup_points

    if not (age_sub or cycle_sub or hormone_sub):
        score += min(4, _subgroup_keywords_in_limitations(limitations))

    if limitations.strip():
        if re.search(r"generaliz|limited|homogeneous|lack of diversity", limitations, re.I):
            score += 3

    if not aes and total_n > 0:
        score -= 5

    return round(max(0.0, min(100.0, score)), 1)
