"""Extractor–auditor verification loop for hallucination and mismatch detection."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from modules.extractor import (
    StudyExtractionModel,
    extract_study_fields,
    merge_extractions,
)
from modules.ingestion import chunk_text
from modules.llm_client import chat_json_raw

VerificationStatus = Literal[
    "Verified",
    "Flagged: Mismatch",
    "Flagged: Insufficient Evidence",
    "Error",
]


class AuditResult(BaseModel):
    extraction: StudyExtractionModel
    verification_status: VerificationStatus
    auditor_notes: str = Field(default="")
    equity_score: float = Field(default=0.0)


AUDITOR_SYSTEM = """You are an independent auditor for biomedical paper extractions.
Compare the extracted JSON claims against the source text. Be strict.

Check especially:
- total_sample_size and female_participant_count match explicit statements
- sex_disaggregated_reported is true ONLY if sex/gender/hormonal breakdown is explicit
- adverse events listed appear in the text
- subgroup flags (age, cycle irregularities, formulation) are supported

Respond with JSON:
{
  "passed": boolean,
  "issues": ["string", ...],
  "corrected_fields": { optional partial field overrides with same keys as extraction },
  "summary": "one short paragraph"
}

If mismatches exist, passed=false and list each issue. corrected_fields may fix obvious errors
ONLY when the source text clearly states the correct value; otherwise leave empty."""


def _auditor_review(source_chunk: str, extraction: StudyExtractionModel) -> dict[str, Any]:
    user = (
        "SOURCE TEXT:\n"
        f"{source_chunk}\n\n"
        "EXTRACTED JSON:\n"
        f"{extraction.model_dump_json(indent=2)}\n"
    )
    return chat_json_raw(AUDITOR_SYSTEM, user)


def _apply_corrections(
    extraction: StudyExtractionModel, corrected: dict[str, Any] | None
) -> StudyExtractionModel:
    if not corrected:
        return extraction
    data = extraction.model_dump()
    for key, val in corrected.items():
        if key in data and val is not None:
            data[key] = val
    try:
        return StudyExtractionModel.model_validate(data)
    except Exception:
        return extraction


def extract_and_verify(paper_text: str) -> AuditResult:
    """
    Step 1: Extract structured fields.
    Step 2: Auditor verifies against raw text; re-extract on mismatch if needed.
    """
    from modules.equity_scorer import calculate_equity_score

    chunks = chunk_text(paper_text)
    primary_chunk = chunks[0]
    audit_chunk = primary_chunk if len(primary_chunk) <= 14_000 else paper_text[:14_000]

    try:
        extraction = extract_study_fields(paper_text)
    except Exception as exc:
        empty = StudyExtractionModel(
            study_title="Extraction failed",
            target_compound_or_intervention="",
            total_sample_size=0,
            sex_disaggregated_reported=False,
            demographic_limitations_noted=str(exc),
        )
        return AuditResult(
            extraction=empty,
            verification_status="Error",
            auditor_notes=str(exc),
            equity_score=calculate_equity_score(empty.model_dump()),
        )

    try:
        audit = _auditor_review(audit_chunk, extraction)
    except Exception as exc:
        return AuditResult(
            extraction=extraction,
            verification_status="Error",
            auditor_notes=f"Auditor unavailable: {exc}",
            equity_score=calculate_equity_score(extraction.model_dump()),
        )

    passed = bool(audit.get("passed", False))
    issues = audit.get("issues") or []
    summary = str(audit.get("summary") or "").strip()
    corrected = audit.get("corrected_fields")

    extraction = _apply_corrections(extraction, corrected if isinstance(corrected, dict) else None)

    if not passed:
        try:
            re_extract = extract_study_fields(audit_chunk)
            extraction = merge_extractions(extraction, re_extract)
            second_audit = _auditor_review(audit_chunk, extraction)
            passed = bool(second_audit.get("passed", False))
            issues = second_audit.get("issues") or issues
            summary = str(second_audit.get("summary") or summary).strip()
            extraction = _apply_corrections(
                extraction,
                second_audit.get("corrected_fields")
                if isinstance(second_audit.get("corrected_fields"), dict)
                else None,
            )
        except Exception as exc:
            issues.append(f"Re-extraction failed: {exc}")

    if passed:
        status: VerificationStatus = "Verified"
    elif issues:
        status = "Flagged: Mismatch"
    else:
        status = "Flagged: Insufficient Evidence"

    notes_parts = []
    if summary:
        notes_parts.append(summary)
    if issues:
        notes_parts.append("Issues: " + "; ".join(str(i) for i in issues))
    auditor_notes = " | ".join(notes_parts) if notes_parts else "No auditor notes."

    score = calculate_equity_score(extraction.model_dump())

    return AuditResult(
        extraction=extraction,
        verification_status=status,
        auditor_notes=auditor_notes,
        equity_score=score,
    )
