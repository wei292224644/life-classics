from __future__ import annotations

import time
from typing import Any, Dict, List
import json

import structlog

from parser.models import ClassifiedChunk, TypedSegment, WorkflowState
from parser.rules import RulesStore
from parser.nodes.output import EscalateOutput
from parser.structured_llm import invoke_structured
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


def escalate_node(state: WorkflowState) -> dict:
    chunk_count = len(state["classified_chunks"])
    _start = time.perf_counter()
    _logger.info("escalate_node_start", chunk_count=chunk_count)

    store = RulesStore(state["rules_dir"])
    config = state.get("config", {})
    classified_chunks: List[ClassifiedChunk] = [
        dict(c) for c in state["classified_chunks"]
    ]

    for i, cc in enumerate(classified_chunks):
        if not cc["has_unknown"]:
            continue

        existing_types = store.get_content_type_rules().get("content_types", [])
        new_segments = list(cc["segments"])

        for j, seg in enumerate(new_segments):
            if seg["content_type"] != "unknown":
                continue

            llm_result = _call_escalate_llm(seg["content"], existing_types)
            llm_calls_total.labels(node="escalate_node", model=settings.ESCALATE_MODEL).inc()
            new_ct_id = llm_result.id

            if llm_result.action == "create_new":
                store.append_content_type(llm_result.model_dump())

            transform_params = llm_result.transform.model_dump()
            new_segments[j] = TypedSegment(
                content=seg["content"],
                content_type=new_ct_id,
                transform_params=transform_params,
                confidence=1.0,
                escalated=True,
                cross_refs=[],
                ref_context="",
                failed_table_refs=[],
            )

        classified_chunks[i] = ClassifiedChunk(
            raw_chunk=cc["raw_chunk"],
            segments=new_segments,
            has_unknown=False,
        )

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="escalate_node").observe(duration)
    parser_chunks_processed_total.labels(node="escalate_node").inc(chunk_count)
    _logger.info(
        "escalate_node_done",
        chunk_count=chunk_count,
        duration_ms=round(duration * 1000, 2),
        model=settings.ESCALATE_MODEL,
    )
    return {"classified_chunks": classified_chunks}