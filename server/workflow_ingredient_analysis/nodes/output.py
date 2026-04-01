"""Pydantic response models for LLM structured outputs in ingredient_analysis workflow."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── retrieve_evidence_node ────────────────────────────────────────────────────


class EvidenceRef(BaseModel):
    """Single evidence reference from GB standard chunks."""

    source_id: str
    source_type: Literal["gb_standard_chunk"] = "gb_standard_chunk"
    standard_no: str
    semantic_type: str
    section_path: str
    content: str
    raw_content: str
    score: float = Field(ge=0, le=1)


# ── analyze_node ──────────────────────────────────────────────────────────────


class AnalysisDecisionStep(BaseModel):
    """Single step in the decision trace."""

    step: str
    findings: list[str]
    reasoning: str
    conclusion: str


class AnalysisDecisionTrace(BaseModel):
    """Complete decision trace from analyze_node."""

    steps: list[AnalysisDecisionStep]
    final_conclusion: str


class AnalyzeOutput(BaseModel):
    """analyze_node LLM output."""

    level: Literal["t0", "t1", "t2", "t3", "t4", "unknown"]
    confidence_score: float = Field(ge=0, le=1)
    decision_trace: AnalysisDecisionTrace


# ── compose_output_node ───────────────────────────────────────────────────────


class AlternativeItem(BaseModel):
    """Single alternative ingredient suggestion."""

    ingredient_id: int
    name: str
    reason: str


class ComposeOutput(BaseModel):
    """compose_output_node LLM output."""

    safety_info: str
    alternatives: list[AlternativeItem]