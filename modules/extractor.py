"""Structured LLM extraction of study demographics and reporting quality."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from modules.llm_client import chat_json


class StudyExtractionModel(BaseModel):
    study_title: str = Field(description="Title of the study or paper")
    target_compound_or_intervention: str = Field(
        description="Drug, device, or intervention studied (e.g., levonorgestrel IUD)"
    )
    total_sample_size: int = Field(ge=0, description="Total enrolled or analyzed N")
    female_participant_count: Optional[int] = Field(
        default=None, ge=0, description="Count of female participants if reported"
    )
    sex_disaggregated_reported: bool = Field(
        description="True if outcomes or AEs are broken down by sex/gender/hormonal status"
    )
    reported_adverse_events: List[str] = Field(
        default_factory=list,
        description="Adverse events explicitly mentioned in results or safety sections",
    )
    demographic_limitations_noted: str = Field(
        default="",
        description="Authors' stated limitations regarding demographics or generalizability",
    )
    age_subgroups_reported: bool = Field(
        default=False,
        description="True if age bands or subgroup analyses by age are reported",
    )
    baseline_cycle_irregularities_reported: bool = Field(
        default=False,
        description="True if menstrual/cycle irregularities at baseline are described",
    )
    hormonal_formulation_breakdown: bool = Field(
        default=False,
        description="True if results distinguish hormonal formulations or doses",
    )

    @field_validator("total_sample_size", "female_participant_count", mode="before")
    @classmethod
    def _coerce_int(cls, value: object) -> object:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            digits = "".join(ch for ch in value if ch.isdigit())
            return int(digits) if digits else 0
        return value


EXTRACTOR_SYSTEM = """You are a biomedical literature analyst specializing in women's health,
contraception, reproductive medicine, and clinical trial demographics.

Extract ONLY facts explicitly supported by the provided paper text. Do not infer or guess.
If a field is not stated, use 0 for total_sample_size only when truly unknown use best explicit N;
use null for female_participant_count when not reported; use empty strings/lists where appropriate.
For booleans, set true ONLY when the text clearly supports it.

Return JSON matching the schema exactly."""


def _build_user_prompt(paper_chunk: str) -> str:
    return (
        "Extract study metadata and demographic reporting from this paper excerpt.\n\n"
        "Prioritize: title, intervention, sample sizes, female enrollment, "
        "sex-disaggregated safety/outcomes, adverse events, and author-stated demographic limits.\n\n"
        "--- PAPER TEXT ---\n"
        f"{paper_chunk}\n"
        "--- END ---"
    )


def extract_study_fields(paper_text: str) -> StudyExtractionModel:
    """
    Run structured LLM extraction on paper text (single call on prioritized excerpt).
    """
    excerpt = paper_text
    if len(excerpt) > 14_000:
        excerpt = paper_text[:10_000] + "\n\n[...]\n\n" + paper_text[-4000:]

    return chat_json(
        EXTRACTOR_SYSTEM,
        _build_user_prompt(excerpt),
        StudyExtractionModel,
    )


def merge_extractions(primary: StudyExtractionModel, secondary: StudyExtractionModel) -> StudyExtractionModel:
    """Prefer non-empty / more specific values when re-extracting after audit."""
    data = primary.model_dump()
    other = secondary.model_dump()
    for key, val in other.items():
        if key in ("reported_adverse_events",):
            merged = list(dict.fromkeys(data[key] + val))
            data[key] = merged
        elif isinstance(val, bool) and val and not data.get(key):
            data[key] = val
        elif isinstance(val, str) and val.strip() and not str(data.get(key, "")).strip():
            data[key] = val
        elif val is not None and data.get(key) in (None, 0, ""):
            data[key] = val
    return StudyExtractionModel.model_validate(data)
