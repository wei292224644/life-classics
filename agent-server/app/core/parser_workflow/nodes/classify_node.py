from __future__ import annotations

from typing import Any, Dict, List

from app.core.parser_workflow.config import get_config_value
from app.core.parser_workflow.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from app.core.parser_workflow.rules import RulesStore


def _call_classify_llm(
    chunk_content: str,
    content_types: List[Dict],
    config: dict,
) -> Dict[str, Any]:
    """
    调用小模型对 chunk 做分段 + 分类。
    使用 structured output 强制返回 JSON，避免 LLM 输出格式不稳定的问题。
    """
    from langchain_openai import ChatOpenAI  # type: ignore[import]
    from pydantic import BaseModel

    class SegmentItem(BaseModel):
        content: str
        content_type: str
        confidence: float

    class ClassifyOutput(BaseModel):
        segments: List[SegmentItem]

    type_descriptions = "\n".join(
        f"- {ct['id']}: {ct['description']}" for ct in content_types
    )
    prompt = (
        "请将以下文本拆分为语义独立的片段，并以 JSON 格式返回每段的 content_type 和置信度（0-1）。\n\n"
        f"可用的 content_type：\n{type_descriptions}\n\n"
        f"文本内容：\n{chunk_content}"
    )

    chat = ChatOpenAI(
        model=config.get("classify_model", "gpt-4o-mini"),
        api_key=config.get("llm_api_key", ""),
        base_url=config.get("llm_base_url") or None,
    ).with_structured_output(ClassifyOutput)

    result: ClassifyOutput = chat.invoke(prompt)
    return {"segments": [s.model_dump() for s in result.segments]}


def classify_raw_chunk(
    raw_chunk: RawChunk,
    store: RulesStore,
    config: dict,
) -> ClassifiedChunk:
    threshold = store.get_confidence_threshold(
        config.get("confidence_threshold"),
    )
    ct_rules = store.get_content_type_rules()
    content_types = ct_rules.get("content_types", [])

    llm_output = _call_classify_llm(raw_chunk["content"], content_types, config)

    segments: List[TypedSegment] = []
    has_unknown = False
    for item in llm_output.get("segments", []):
        confidence = item.get("confidence", 0.0)
        if confidence < threshold:
            seg = TypedSegment(
                content=item["content"],
                content_type="unknown",
                transform_params={"strategy": "plain_embed"},
                confidence=confidence,
                escalated=False,
            )
            has_unknown = True
        else:
            ct_id = item["content_type"]
            transform_params = store.get_transform_params(ct_id)
            seg = TypedSegment(
                content=item["content"],
                content_type=ct_id,
                transform_params=transform_params,
                confidence=confidence,
                escalated=False,
            )
        segments.append(seg)

    return ClassifiedChunk(
        raw_chunk=raw_chunk,
        segments=segments,
        has_unknown=has_unknown,
    )


def classify_node(state: WorkflowState) -> dict:
    store = RulesStore(state["rules_dir"])
    config = state.get("config", {})
    classified: List[ClassifiedChunk] = [
        classify_raw_chunk(chunk, store, config) for chunk in state["raw_chunks"]
    ]
    return {"classified_chunks": classified}

