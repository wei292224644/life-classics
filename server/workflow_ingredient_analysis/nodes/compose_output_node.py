"""compose_output_node — 生成 safety_info 和 alternatives。"""
from __future__ import annotations

import time

import structlog
from opentelemetry import trace

from observability.metrics import (
    ingredient_analysis_node_duration_seconds,
    ingredient_analysis_llm_calls_total,
)
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import ComposeOutput
from workflow_ingredient_analysis.structured_gateway import invoke_structured

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)


def _build_compose_prompt(
    ingredient: dict, analysis_output: dict, evidence_refs: list[dict]
) -> str:
    """构建 compose_output_node 的 prompt."""
    name = ingredient.get("name", "")
    function_types = ", ".join(ingredient.get("function_type", []) or [])
    level = analysis_output.get("level", "unknown")
    confidence = analysis_output.get("confidence_score", 0.0)
    trace_steps = analysis_output.get("decision_trace", {}).get("steps", [])
    final_conclusion = analysis_output.get("decision_trace", {}).get(
        "final_conclusion", ""
    )

    trace_text = (
        "\n".join(f"- [{s['step']}] {s['conclusion']}" for s in trace_steps)
        if trace_steps
        else final_conclusion
    )

    evidence_brief = "\n".join(
        f"- {r.get('standard_no', 'N/A')}: {r.get('content', '')[:100]}..."
        for r in (evidence_refs or [])[:3]
    ) or "无相关证据"

    return f"""你是一位食品安全科普专家。请为配料「{name}」生成面向消费者的安全提示和替代建议。

【配料信息】
- 名称：{name}
- 功能类型：{function_types or '未知'}
- 风险等级：{level}（{final_conclusion}）
- 判断置信度：{confidence:.0%}

【风险评估依据】
{trace_text}

【相关标准参考（仅前3条）】
{evidence_brief}

返回格式（严格 JSON）：
{{
    "safety_info": "面向消费者的安全提示，2-4句话，通俗易懂，说明该配料的风险和适用人群。不超过200字。",
    "alternatives": [
        {{
            "ingredient_id": 0,
            "name": "替代配料名称",
            "reason": "推荐理由，1句话"
        }}
    ]
}}

注意：
- 如果 level 为 t0 或 t1，safety_info 应强调其安全性
- 如果 level 为 t3 或 t4，safety_info 应明确风险提示
- 如果 level 为 unknown 或 t2，alternatives 应提供更安全的替代选择
- alternatives 中的 ingredient_id 暂时填 0（由外部知识库匹配后填充）
"""


async def compose_output_node(state: WorkflowState) -> dict:
    """生成 safety_info 与 alternatives."""
    start = time.perf_counter()
    ingredient = state.get("ingredient", {})
    analysis_output = state.get("analysis_output") or {}
    evidence_refs = state.get("evidence_refs") or []
    task_id = state.get("task_id", "unknown")
    ingredient_id = ingredient.get("ingredient_id", "?")

    _logger.info(
        "compose_output_node_start",
        ingredient_id=ingredient_id,
        task_id=task_id,
    )

    with _tracer.start_as_current_span("compose_output_node") as span:
        span.set_attribute("ingredient_analysis.node", "compose_output_node")
        span.set_attribute("ingredient_analysis.ingredient_id", ingredient_id)

        prompt = _build_compose_prompt(ingredient, analysis_output, evidence_refs)

        try:
            result = invoke_structured(
                node_name="compose_output_node",
                prompt=prompt,
                response_model=ComposeOutput,
            )
            ingredient_analysis_llm_calls_total.labels(
                node="compose_output_node", model="unknown"
            ).inc()
        except Exception as exc:
            duration = time.perf_counter() - start
            ingredient_analysis_node_duration_seconds.labels(
                node="compose_output_node"
            ).observe(duration)
            _logger.error(
                "compose_output_node_llm_error",
                ingredient_id=ingredient_id,
                error=str(exc),
            )
            return {
                "status": "failed",
                "error_code": "schema_invalid",
                "errors": [f"compose_output_node LLM 调用失败: {exc}"],
            }

    output = result.model_dump()
    duration = time.perf_counter() - start
    ingredient_analysis_node_duration_seconds.labels(
        node="compose_output_node"
    ).observe(duration)
    _logger.info(
        "compose_output_node_done",
        ingredient_id=ingredient_id,
        has_alternatives=len(output.get("alternatives", [])) > 0,
        duration_ms=round(duration * 1000, 2),
    )

    return {
        "composed_output": output,
        "status": "succeeded",
    }