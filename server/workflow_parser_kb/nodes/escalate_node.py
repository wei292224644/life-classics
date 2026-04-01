from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List
import json

import structlog
from opentelemetry import trace

_tracer = trace.get_tracer(__name__)

from workflow_parser_kb.models import ClassifiedChunk, TypedSegment, WorkflowState
from workflow_parser_kb.rules import RulesStore
from workflow_parser_kb.nodes.output import EscalateOutput
from workflow_parser_kb.structured_gateway import invoke_structured
from config import settings
from observability.metrics import (
    llm_calls_total,
    parser_chunks_processed_total,
    parser_node_duration_seconds,
)

_logger = structlog.get_logger(__name__)


def _call_escalate_llm(
    segment_content: str,
    content_types: List[Dict],
) -> EscalateOutput:
    """
    大模型两步判断：
    1. 语义匹配：unknown 片段是否符合已有 content_type？
       → action="use_existing", content_type=<existing_id>
    2. 不符合则创建新类型（含 strategy + prompt_template）
       → action="create_new", content_type=<new_id>, description=..., transform={...}
    """
    type_list = json.dumps(content_types, ensure_ascii=False, indent=2)
    format_example = """{
    "action": "use_existing" | "create_new",
    "id": "content_type_id",
    "description": "类型说明",
    "transform": {
        "strategy": "转化策略",
        "prompt_template": "转化提示词"
    }
}"""
    prompt = f"""
        你是一个数据分析助手，我现在需要你分析以下文本片段，并返回一个 JSON 对象。
        你需要根据以下文本片段的语义，判断它是否符合某个已有内容类型。
        如果符合，直接返回相对应的 content 实例即可。
        如果不符合，请分析该文本的语义，并给出新的 content 实例。
        你需要分析出他适合的提示词是什么，并返回新的 content 实例。
        
        现有content_type列表：
        {type_list}
        
        文本内容：
        {segment_content}
        
        返回格式（json）：
        {format_example}
    """
    result = invoke_structured(
        node_name="escalate_node",
        prompt=prompt,
        response_model=EscalateOutput,
        extra_body={"enable_thinking": False, "reasoning_split": True},
    )
    return result


async def escalate_node(state: WorkflowState) -> dict:
    chunks_in = len(state["classified_chunks"])
    _start = time.perf_counter()
    _logger.info("escalate_node_start", chunk_count=chunks_in)

    with _tracer.start_as_current_span("escalate_node") as span:
        span.set_attribute("workflow_parser_kb.node", "escalate_node")
        span.set_attribute("workflow_parser_kb.doc_id", state.get("doc_metadata", {}).get("doc_id", ""))
        span.set_attribute("workflow_parser_kb.chunk_count.in", chunks_in)
        store = RulesStore(state["rules_dir"])
        config = state.get("config", {})
        classified_chunks: List[ClassifiedChunk] = [
            dict(c) for c in state["classified_chunks"]
        ]

        # 收集所有需要处理的 unknown segment
        unknown_tasks = []
        for i, cc in enumerate(classified_chunks):
            if not cc["has_unknown"]:
                continue
            existing_types = store.get_content_type_rules().get("content_types", [])
            for j, seg in enumerate(cc["segments"]):
                if seg["content_type"] == "unknown":
                    unknown_tasks.append((i, j, seg["content"], existing_types))

        semaphore = asyncio.Semaphore(settings.LLM_MAX_CONCURRENCY)

        async def limited_escalate(idx_i: int, idx_j: int, content: str, existing_types: List[Dict]) -> tuple[int, int, EscalateOutput]:
            async with semaphore:
                return idx_i, idx_j, await asyncio.to_thread(_call_escalate_llm, content, existing_types)

        results = await asyncio.gather(
            *[limited_escalate(i, j, content, et) for i, j, content, et in unknown_tasks],
            return_exceptions=True,
        )

        # 处理结果
        for result in results:
            if isinstance(result, Exception):
                continue
            i, j, llm_result = result
            llm_calls_total.labels(node="escalate_node", model=settings.DEFAULT_MODEL).inc()
            new_ct_id = llm_result.id

            if llm_result.action == "create_new":
                store.append_content_type(llm_result.model_dump())

            transform_params = llm_result.transform.model_dump()
            classified_chunks[i]["segments"][j] = TypedSegment(
                content=classified_chunks[i]["segments"][j]["content"],
                content_type=new_ct_id,
                transform_params=transform_params,
                confidence=1.0,
                escalated=True,
                cross_refs=[],
                ref_context="",
                failed_table_refs=[],
            )
            classified_chunks[i]["has_unknown"] = False

        duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="escalate_node").observe(duration)
    parser_chunks_processed_total.labels(node="escalate_node").inc(chunks_in)
    _logger.info(
        "escalate_node_done",
        chunk_count=chunks_in,
        duration_ms=round(duration * 1000, 2),
        model=settings.DEFAULT_MODEL,
    )
    return {"classified_chunks": classified_chunks}