"""Workflow state and types for ingredient_analysis."""
from __future__ import annotations

from typing import Literal, TypedDict


class WorkflowState(TypedDict):
    """ingredient_analyses workflow state — flows through all 3 nodes."""

    # 输入（由调用方注入）
    ingredient: dict  # 配料数据字典
    task_id: str
    run_id: str
    ai_model: str

    # Node outputs
    evidence_refs: list[dict] | None  # list[EvidenceRef]
    analysis_output: dict | None  # AnalyzeOutput
    composed_output: dict | None  # ComposeOutput

    # 状态与错误
    status: Literal["running", "succeeded", "failed"]
    error_code: str | None
    errors: list[str]