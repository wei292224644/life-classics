"""analyze_node — 基于配料信息和证据推理风险等级。"""
from __future__ import annotations

import time

import structlog
from opentelemetry import trace

from observability.metrics import (
    ingredient_analysis_node_duration_seconds,
    ingredient_analysis_llm_calls_total,
)
from workflow_ingredient_analysis.models import WorkflowState
from workflow_ingredient_analysis.nodes.output import AnalyzeOutput
from workflow_ingredient_analysis.structured_gateway import invoke_structured

_tracer = trace.get_tracer(__name__)
_logger = structlog.get_logger(__name__)

_EVIDENCE_CONTEXT_MAX_LEN = 3000


def _build_evidence_context(evidence_refs: list[dict]) -> str:
    """将 evidence_refs 格式化为 prompt 上下文字符串."""
    if not evidence_refs:
        return "（无相关证据）"

    chunks = []
    for ref in evidence_refs:
        chunk_text = f"""【标准】{ref.get('standard_no', 'N/A')}
【章节】{ref.get('section_path', 'N/A')}
【语义类型】{ref.get('semantic_type', 'N/A')}
【内容】
{ref.get('content', '')}""".strip()
        chunks.append(chunk_text)

    full_text = "\n\n---\n\n".join(chunks)
    if len(full_text) > _EVIDENCE_CONTEXT_MAX_LEN:
        full_text = full_text[:_EVIDENCE_CONTEXT_MAX_LEN] + "\n...（内容截断）"
    return full_text


def _build_analyze_prompt(ingredient: dict, evidence_context: str) -> str:
    """构建 analyze_node 的 prompt."""
    name = ingredient.get("name", "")
    function_types = ", ".join(ingredient.get("function_type", []) or [])
    limit_usage = ingredient.get("limit_usage", "")
    origin = ingredient.get("origin_type", "")

    return f"""你是一位食品安全评估专家。请根据以下证据信息，对配料「{name}」进行风险评估。

【配料信息】
- 名称：{name}
- 功能类型：{function_types or '未知'}
- 来源类型：{origin or '未知'}
- 法规限值要求：{limit_usage or '未找到相关限值'}

【相关 GB 标准证据】
{evidence_context}

请进行结构化分析并返回结果。

分析要求：
1. 仔细阅读每条证据，提取与该配料安全风险相关的信息
2. 结合配料的功能类型、来源、限值要求综合判断
3. 证据不足时，应返回 "unknown" 等级，而非强行判断
4. confidence_score 反映你对判断的确信程度（0-1），证据越充分分数越高

返回格式（严格 JSON）：
{{
    "level": "t0" | "t1" | "t2" | "t3" | "t4" | "unknown",
    "confidence_score": 0.0-1.0,
    "decision_trace": {{
        "steps": [
            {{
                "step": "步骤名称，如 evidence_review / risk_reasoning",
                "findings": ["发现1", "发现2"],
                "reasoning": "该步骤的推理逻辑",
                "conclusion": "该步骤的结论"
            }}
        ],
        "final_conclusion": "最终综合结论"
    }}
}}
"""


async def analyze_node(state: WorkflowState) -> dict:
    """基于 evidence_refs 推理风险等级，证据不足时降级为 unknown."""
    start = time.perf_counter()
    ingredient = state.get("ingredient", {})
    evidence_refs = state.get("evidence_refs") or []
    task_id = state.get("task_id", "unknown")
    ingredient_id = ingredient.get("ingredient_id", "?")

    _logger.info("analyze_node_start", ingredient_id=ingredient_id, task_id=task_id)

    with _tracer.start_as_current_span("analyze_node") as span:
        span.set_attribute("ingredient_analysis.node", "analyze_node")
        span.set_attribute("ingredient_analysis.ingredient_id", ingredient_id)

        evidence_context = _build_evidence_context(evidence_refs)
        prompt = _build_analyze_prompt(ingredient, evidence_context)

        try:
            result = invoke_structured(
                node_name="analyze_node",
                prompt=prompt,
                response_model=AnalyzeOutput,
            )
            ingredient_analysis_llm_calls_total.labels(
                node="analyze_node", model="unknown"
            ).inc()
        except Exception as exc:
            duration = time.perf_counter() - start
            ingredient_analysis_node_duration_seconds.labels(
                node="analyze_node"
            ).observe(duration)
            _logger.error(
                "analyze_node_llm_error",
                ingredient_id=ingredient_id,
                error=str(exc),
            )
            return {
                "status": "failed",
                "error_code": "schema_invalid",
                "errors": [f"analyze_node LLM 调用失败: {exc}"],
            }

    output = result.model_dump()
    duration = time.perf_counter() - start
    ingredient_analysis_node_duration_seconds.labels(node="analyze_node").observe(
        duration
    )
    _logger.info(
        "analyze_node_done",
        ingredient_id=ingredient_id,
        level=output["level"],
        confidence=output["confidence_score"],
        duration_ms=round(duration * 1000, 2),
    )

    return {
        "analysis_output": output,
        "status": "running",
    }