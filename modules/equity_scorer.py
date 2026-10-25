"""Deterministic demographic equity reporting score (0–100)."""

from __future__ import annotations

from typing import Any


# Proposed MVP weights. These are design choices, not validated
# scientific weights.
WEIGHTS = {
    "sample_size": 5,
    "female_participant_count": 15,
    "sex_disaggregated_reporting": 25,
    "age_subgroups": 10,
    "cycle_characteristics": 10,
    "hormonal_formulation": 10,
    "adverse_events": 15,
    "demographic_limitations": 10,
}


def calculate_equity_score_details(
    extraction_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate a reporting-completeness score from StudyExtractionModel data.

    Accepts either a dictionary or a Pydantic model instance.
    A higher score means more of the selected reporting criteria were
    documented. This is not a validated measure of study quality or bias.
    """

    # Support both model_dump() output and direct Pydantic model input.
    if not isinstance(extraction_data, dict):
        if hasattr(extraction_data, "model_dump"):
            extraction_data = extraction_data.model_dump()
        else:
            raise TypeError(
                "extraction_data must be a dictionary or Pydantic model"
        )

    data = extraction_data

    def present(value: Any) -> bool:
        """Whether a field contains a usable value."""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip()) and value.strip().lower() not in {
                "unknown", "not reported", "not available", "n/a"
            }
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) > 0
        return True

    total_n = data.get("total_sample_size")
    female_n = data.get("female_participant_count")
    
    # Validate counts rather than silently scoring contradictory data.
    warnings = []

    if isinstance(total_n, int) and not isinstance(total_n, bool):
        if total_n < 0:
            warnings.append("Total sample size is negative.")

    if isinstance(female_n, int) and not isinstance(female_n, bool):
        if female_n < 0:
            warnings.append("Female participant count is negative.")

    if (
        isinstance(total_n, int)
        and not isinstance(total_n, bool)
        and isinstance(female_n, int)
        and not isinstance(female_n, bool)
        and female_n > total_n
    ):
        warnings.append(
            "Female participant count exceeds total sample size."
        )

    valid_counts = (
        isinstance(total_n, int)
        and not isinstance(total_n, bool)
        and total_n >= 0
        and (
            female_n is None
            or (
                isinstance(female_n, int)
                and not isinstance(female_n, bool)
                and 0 <= female_n <= total_n
            )
        )
    )


    criteria = {
        "sample_size": (
            "Total sample size is reported",
            valid_counts and isinstance(total_n, int) and not isinstance(total_n, bool) and total_n > 0,
        ),
        "female_participant_count": (
            "Female participant count is reported",
            valid_counts and female_n is not None,
        ),
        "sex_disaggregated_reporting": (
            "Sex/gender/hormonal-status disaggregation is reported",
            data.get("sex_disaggregated_reported") is True,
        ),
        "age_subgroups": (
            "Age subgroup reporting is documented",
            data.get("age_subgroups_reported") is True,
        ),
        "cycle_characteristics": (
            "Baseline menstrual-cycle characteristics are described",
            data.get("baseline_cycle_irregularities_reported") is True,
        ),
        "hormonal_formulation": (
            "Hormonal formulation or dose breakdown is reported",
            data.get("hormonal_formulation_breakdown") is True,
        ),
        "adverse_events": (
            "At least one adverse event is explicitly listed",
            present(data.get("reported_adverse_events")),
        ),
        "demographic_limitations": (
            "Demographic limitations are discussed",
            present(data.get("demographic_limitations_noted")),
        ),
    }

    details = {}
    score = 0

    for key, (description, reported) in criteria.items():
        weight = WEIGHTS[key]
        points = weight if reported else 0
        score += points

        details[key] = {
            "description": description,
            "weight": weight,
            "reported": reported,
            "points_awarded": points,
        }

    return {
        "equity_score": float(score),
        "components": details,
        "reporting_gaps": [
            item["description"]
            for item in details.values()
            if not item["reported"]
        ],
        "warnings": warnings,
        "interpretation": (
            "Measures documented reporting criteria under a proposed MVP "
            "rubric. It does not establish actual population representation, "
            "scientific quality, or absence of bias."
        ),
    }


def calculate_equity_score(extraction_data: dict) -> float:
    """Return a numeric score for compatibility with the existing app."""
    return calculate_equity_score_details(extraction_data)["equity_score"]
