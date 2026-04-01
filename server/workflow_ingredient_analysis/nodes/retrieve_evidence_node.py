"""retrieve_evidence_node — 从 GB 标准知识库检索证据。"""
from __future__ import annotations

import time

import structlog
from opentelemetry import trace

from kb.retriever import search
from observability.metrics import ingredient_analysis_node_duration_seconds
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import EvidenceRef

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)

_KB_UNAVAILABLE_ERROR = "knowledge_base_unavailable"


async def retrieve_evidence_node(state: WorkflowState) -> dict:
    """检索 GB 标准 chunks 作为证据，无证据时降级为 unknown."""
    start = time.perf_counter()
    ingredient = state.get("ingredient")
    if not ingredient:
        return {
            "status": "failed",
            "error_code": "ingredient_not_found",
            "errors": ["ingredient data missing from state"],
        }

    ingredient_name = ingredient.get("name", "")
    ingredient_id = ingredient.get("ingredient_id", "?")
    task_id = state.get("task_id", "unknown")
    _logger.info(
        "retrieve_evidence_node_start",
        ingredient_id=ingredient_id,
        name=ingredient_name,
        task_id=task_id,
    )

    with _tracer.start_as_current_span("retrieve_evidence_node") as span:
        span.set_attribute("ingredient_analysis.node", "retrieve_evidence_node")
        span.set_attribute("ingredient_analysis.ingredient_id", ingredient_id)

        try:
            kb_results = await search(query=ingredient_name, top_k=5, filters=None)
        except Exception as exc:
            duration = time.perf_counter() - start
            ingredient_analysis_node_duration_seconds.labels(
                node="retrieve_evidence_node"
            ).observe(duration)
            _logger.error(
                "retrieve_evidence_node_kb_error",
                ingredient_id=ingredient_id,
                error=str(exc),
            )
            return {
                "status": "failed",
                "error_code": _KB_UNAVAILABLE_ERROR,
                "errors": [f"knowledge base unavailable: {exc}"],
            }

        if not kb_results:
            duration = time.perf_counter() - start
            ingredient_analysis_node_duration_seconds.labels(
                node="retrieve_evidence_node"
            ).observe(duration)
            _logger.warning(
                "retrieve_evidence_node_no_results",
                ingredient_id=ingredient_id,
            )
            return {
                "evidence_refs": [],
                "status": "running",
            }

        evidence_refs = [
            EvidenceRef(
                source_id=r["chunk_id"],
                source_type="gb_standard_chunk",
                standard_no=r.get("standard_no", ""),
                semantic_type=r.get("semantic_type", ""),
                section_path=r.get("section_path", ""),
                content=r.get("content", ""),
                raw_content=r.get("raw_content", ""),
                score=r.get("score", 0.0),
            ).model_dump()
            for r in kb_results
        ]

    duration = time.perf_counter() - start
    ingredient_analysis_node_duration_seconds.labels(
        node="retrieve_evidence_node"
    ).observe(duration)
    _logger.info(
        "retrieve_evidence_node_done",
        ingredient_id=ingredient_id,
        evidence_count=len(evidence_refs),
        duration_ms=round(duration * 1000, 2),
    )

    return {
        "evidence_refs": evidence_refs,
        "status": "running",
    }