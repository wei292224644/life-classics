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
from app.core.parser_workflow.structured_llm import invoke_structured
from app.core.parser_workflow.nodes.output import ClassifyOutput, SegmentItem


def _call_classify_llm(
    chunk_content: str,
    content_types: List[Dict],
) -> List[SegmentItem]:
    """
    调用小模型对 chunk 做分段 + 分类。
    使用 invoke_structured 强制返回结构化输出，失败时抛 StructuredOutputError。
    """
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

保守切分原则：
1. 只在相邻内容属于明显不同的 content_type 时才切分；同一逻辑章节的内容应保持整体。
2. 标准前言（以"前言"为标题的章节）整体归为 preface 类型，内部变更条目列表（如"——增加了..."）不单独拆分。

示例（前言章节的正确处理方式）：
输入：包含前言标题、版本代替声明和多条变更条目的文本块
正确输出：1 个 segment，content_type=preface，包含完整前言文本
错误输出：多个 segment，将各变更条目拆分为独立的 numbered_list

文本内容：
{chunk_content}

返回格式（json）：
{format_example}
"""
    result = invoke_structured(
        node_name="classify_node",
        prompt=prompt,
        response_model=ClassifyOutput,
    )
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
                cross_refs=[],
                ref_context="",
                failed_table_refs=[],
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
                cross_refs=[],
                ref_context="",
                failed_table_refs=[],
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
