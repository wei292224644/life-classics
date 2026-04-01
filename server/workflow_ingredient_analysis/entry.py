"""Public entry point for ingredient_analysis workflow — pure compute, no DB/API calls."""
from __future__ import annotations

import time as time_module
import uuid

import structlog
from opentelemetry import trace

from observability.metrics import (
    ingredient_analysis_duration_seconds,
    ingredient_analysis_run_total,
    ingredient_analysis_unknown_rate,
)
from workflow_ingredient_analysis.graph import ingredient_analysis_graph
from workflow_ingredient_analysis.models import WorkflowState

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)


async def run_ingredient_analysis(
    ingredient: dict,
    task_id: str,
    ai_model: str = "unknown",
) -> dict:
    """
    执行 ingredient_analyses workflow（纯计算层）。

    Workflow 本身不调用任何 API、不操作数据库。
    编排逻辑（查配料 → 调用 workflow → 写结果）由调用方负责。

    Returns:
        dict，含 keys: status, ingredient_id, task_id, errors, analysis_output, composed_output
    """
    run_id = str(uuid.uuid4())
    ingredient_id = ingredient.get("ingredient_id", "?")
    _logger.info(
        "run_ingredient_analysis_start",
        ingredient_id=ingredient_id,
        task_id=task_id,
        run_id=run_id,
    )
    start_time = time_module.perf_counter()

    initial_state: WorkflowState = {
        "ingredient": ingredient,
        "task_id": task_id,
        "run_id": run_id,
        "ai_model": ai_model,
        "evidence_refs": None,
        "analysis_output": None,
        "composed_output": None,
        "status": "running",
        "error_code": None,
        "errors": [],
    }

    try:
        with _tracer.start_as_current_span("ingredient_analysis_workflow") as span:
            span.set_attribute("ingredient_analysis.ingredient_id", ingredient_id)
            span.set_attribute("ingredient_analysis.run_id", run_id)
            span.set_attribute("ingredient_analysis.task_id", task_id)

            result_state = await ingredient_analysis_graph.ainvoke(initial_state)

            final_status = result_state.get("status", "failed")
            span.set_attribute("ingredient_analysis.status", final_status)

            # 记录 metrics
            ingredient_analysis_run_total.labels(status=final_status).inc()
            elapsed = time_module.perf_counter() - start_time
            ingredient_analysis_duration_seconds.observe(elapsed)

            if final_status == "succeeded":
                analysis_output = result_state.get("analysis_output") or {}
                if analysis_output.get("level") == "unknown":
                    ingredient_analysis_unknown_rate.inc()

            _logger.info(
                "run_ingredient_analysis_done",
                ingredient_id=ingredient_id,
                status=final_status,
                duration_ms=round(elapsed * 1000, 2),
            )

            return {
                "status": final_status,
                "ingredient_id": ingredient_id,
                "task_id": task_id,
                "run_id": run_id,
                "error_code": result_state.get("error_code"),
                "errors": result_state.get("errors", []),
                "analysis_output": result_state.get("analysis_output"),
                "composed_output": result_state.get("composed_output"),
                "evidence_refs": result_state.get("evidence_refs"),
            }
    except Exception as exc:
        elapsed = time_module.perf_counter() - start_time
        ingredient_analysis_run_total.labels(status="failed").inc()
        ingredient_analysis_duration_seconds.observe(elapsed)
        _logger.error(
            "run_ingredient_analysis_error",
            ingredient_id=ingredient_id,
            error=str(exc),
        )
        return {
            "status": "failed",
            "ingredient_id": ingredient_id,
            "task_id": task_id,
            "run_id": run_id,
            "error_code": "workflow_error",
            "errors": [str(exc)],
            "analysis_output": None,
            "composed_output": None,
            "evidence_refs": None,
        }