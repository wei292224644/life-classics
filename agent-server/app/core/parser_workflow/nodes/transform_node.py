from __future__ import annotations

from typing import List

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    DocumentChunk,
    TypedSegment,
    WorkflowState,
    make_chunk_id,
)
from app.core.config import settings
from app.core.parser_workflow.llm import create_chat_model, resolve_provider

from app.core.parser_workflow.nodes.output import TransformOutput


def _call_llm_transform(
    content: str,
    transform_params: dict,
    ref_context: str = "",
) -> str:
    """
    使用 LLM 根据 prompt_template 将原始内容转化为自然语言文本。
    在测试中会通过 patch 进行 mock。
    """
    provider = resolve_provider(settings.TRANSFORM_LLM_PROVIDER)
    chat = create_chat_model(settings.TRANSFORM_MODEL, provider, output_schema=TransformOutput)
    format_example = """
    {
        "content": "转化后的内容"
    }
    """

    prompt = f"""
    请根据以下提示词，将待处理内容转化为 JSON 结构。
    {transform_params["prompt_template"]}
    \n\n待处理内容：
    {content}
    \n\n返回格式（json）：
    {format_example}
    """

    if ref_context:
        prompt += f"\n\n以下是文中引用的表格内容，请结合该表格理解上下文：\n{ref_context}"

    resp: TransformOutput = chat.invoke(prompt)
    return resp.content


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
        raw_content = raw_chunk["content"]
        ref_context = seg.get("ref_context", "")
        cross_refs = seg.get("cross_refs", [])
        failed_table_refs = seg.get("failed_table_refs", [])

        llm_text = _call_llm_transform(seg["content"], seg["transform_params"], ref_context)

        results.append(
            DocumentChunk(
                chunk_id=make_chunk_id(
                    doc_metadata.get("standard_no", ""),
                    raw_chunk["section_path"],
                    llm_text,
                ),
                doc_metadata=doc_metadata,
                section_path=raw_chunk["section_path"],
                content_type=seg["content_type"],
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
    final_chunks: List[DocumentChunk] = []
    for classified in state["classified_chunks"]:
        chunks = apply_strategy(
            classified["segments"],
            classified["raw_chunk"],
            state["doc_metadata"],
        )
        final_chunks.extend(chunks)
    return {"final_chunks": final_chunks}

