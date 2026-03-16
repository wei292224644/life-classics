from __future__ import annotations

from typing import Dict, List

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    RawChunk,
    TypedSegment,
    WorkflowState,
)
from app.core.parser_workflow.rules import RulesStore
from app.core.config import settings
from app.core.parser_workflow.llm import create_chat_model, resolve_provider
from app.core.parser_workflow.nodes.output import ClassifyOutput, SegmentItem


def _call_classify_llm(
    chunk_content: str,
    content_types: List[Dict],
) -> List[SegmentItem]:
    """
    调用小模型对 chunk 做分段 + 分类。
    使用 structured output 强制返回 JSON，避免 LLM 输出格式不稳定的问题。
    """
    provider = resolve_provider(settings.CLASSIFY_LLM_PROVIDER)
    chat = create_chat_model(settings.CLASSIFY_MODEL, provider, output_schema=ClassifyOutput)
    type_descriptions = "\n".join(
        f"- {ct['id']}: {ct['description']}" for ct in content_types
    )
    format_example = """{
    "segments": [
        {
            "content": "片段文本内容",
            "content_type": "content_type_id",
            "confidence": 0.0-1.0的浮点数
        }
    ]
}"""
    prompt = f"""请将以下文本拆分为语义独立的片段，并分析每个片段的 content_type 和置信度（0-1）。

可用的 content_type：
{type_descriptions}

文本内容：
{chunk_content}

返回格式（json）：
{format_example}
"""
    result: ClassifyOutput = chat.invoke(prompt)
    return result.segments


def classify_raw_chunk(
    raw_chunk: RawChunk,
    store: RulesStore,
) -> ClassifiedChunk:
    threshold = store.get_confidence_threshold(
        settings.CONFIDENCE_THRESHOLD,
    )
    ct_rules = store.get_content_type_rules()
    content_types = ct_rules.get("content_types", [])

    llm_output = _call_classify_llm(raw_chunk["content"], content_types)

    segments: List[TypedSegment] = []
    has_unknown = False
    for item in llm_output:
        confidence = item.confidence
        if confidence < threshold:
            seg = TypedSegment(
                content=item.content,
                content_type="unknown",
                transform_params={
                    "strategy": "plain_embed",
                    "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n",
                },
                confidence=confidence,
                escalated=False,
            )
            has_unknown = True
        else:
            ct_id = item.content_type
            transform_params = store.get_transform_params(ct_id)
            seg = TypedSegment(
                content=item.content,
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
    classified: List[ClassifiedChunk] = [
        classify_raw_chunk(chunk, store) for chunk in state["raw_chunks"]
    ]
    return {"classified_chunks": classified}
