from __future__ import annotations

import re
import time
from typing import List

import structlog

from parser.models import (
    DocumentChunk,
    TypedSegment,
    WorkflowState,
    make_chunk_id,
)
from parser.structured_llm import invoke_structured
from parser.nodes.output import TransformOutput
from config import settings
from observability.metrics import (
    llm_calls_total,
    parser_chunks_processed_total,
    parser_node_duration_seconds,
)

_logger = structlog.get_logger(__name__)


def _transform_model() -> str:
    """返回 transform 节点实际使用的模型名，空则 fallback 到 ESCALATE_MODEL。"""
    return settings.TRANSFORM_MODEL or settings.ESCALATE_MODEL


def _call_llm_transform(
    content: str,
    transform_params: dict,
    ref_context: str = "",
) -> str:
    """
    使用 LLM 根据 prompt_template 将原始内容转化为自然语言文本。
    在测试中会通过 patch 进行 mock。
    """

    prompt = f"""
    按照以下提示词，处理原文本。
    {transform_params["prompt_template"]}
    \n\n原文本：
    {content}
    """

    if ref_context:
        prompt += (
            f"\n\n以下是文中引用的表格内容，请结合该表格理解上下文：\n{ref_context}"
        )

    resp = invoke_structured(
        node_name="transform_node",
        prompt=prompt,
        response_model=TransformOutput,
        extra_body={"enable_thinking": False, "reasoning_split": True},
    )
    return resp.content


def _strip_md_headings(text: str) -> str:
    """去除行首 Markdown 标题前缀，如 '### 二、...' → '二、...'"""
    return re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)


def apply_strategy(
    segments: List[TypedSegment],
    raw_chunk,
    doc_metadata: dict,
) -> List[DocumentChunk]:
    """
    当前版本：无论 strategy 为何，都统一通过 LLM 转写为向量化文本。
    未来如果需要区分不同策略，可以在此处分支。
    """
    results: List[DocumentChunk] = []

    for seg in segments:
        # 纯标题行信息已通过 section_path 携带，不生成独立 chunk
        if seg["structure_type"] == "header":
            continue

        raw_content = raw_chunk["content"]
        ref_context = seg.get("ref_context", "")
        cross_refs = seg.get("cross_refs", [])
        failed_table_refs = seg.get("failed_table_refs", [])

        # 去除内容中残留的 Markdown 标题前缀（如修改单条目 "### 二、2.3 ..."）
        content = _strip_md_headings(seg["content"])

        # 极短 segment 直接使用原文，跳过 LLM 避免幻觉
        if len(content) < 50:
            llm_text = content
        else:
            llm_text = _call_llm_transform(
                content, seg["transform_params"], ref_context
            )
            llm_calls_total.labels(node="transform_node", model=_transform_model()).inc()

        results.append(
            DocumentChunk(
                chunk_id=make_chunk_id(
                    doc_metadata.get("doc_id", ""),
                    raw_chunk["section_path"],
                    llm_text,
                ),
                doc_metadata=doc_metadata,
                section_path=raw_chunk["section_path"],
                structure_type=seg["structure_type"],
                semantic_type=seg["semantic_type"],
                content=llm_text,
                raw_content=raw_content,
                meta={
                    "transform_strategy": seg["transform_params"]["strategy"],
                    "segment_raw_content": seg["content"],
                    "cross_refs": cross_refs,
                    "non_table_refs": [r for r in cross_refs if not r.startswith("表")],
                    "failed_table_refs": failed_table_refs,
                },
            )
        )

    return results


def transform_node(state: WorkflowState) -> dict:
    chunk_count = len(state["classified_chunks"])
    _start = time.perf_counter()
    _logger.info("transform_node_start", chunk_count=chunk_count)

    final_chunks: List[DocumentChunk] = []
    for classified in state["classified_chunks"]:
        chunks = apply_strategy(
            classified["segments"],
            classified["raw_chunk"],
            state["doc_metadata"],
        )
        final_chunks.extend(chunks)

    duration = time.perf_counter() - _start
    parser_node_duration_seconds.labels(node="transform_node").observe(duration)
    parser_chunks_processed_total.labels(node="transform_node").inc(chunk_count)
    _logger.info(
        "transform_node_done",
        chunk_count=chunk_count,
        output_chunk_count=len(final_chunks),
        duration_ms=round(duration * 1000, 2),
        model=_transform_model(),
    )
    return {"final_chunks": final_chunks}
