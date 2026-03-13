from __future__ import annotations

from typing import List

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    DocumentChunk,
    TypedSegment,
    WorkflowState,
    make_chunk_id,
)


def _call_llm_transform(
    content: str,
    transform_params: dict,
    config: dict,
) -> str:
    """
    使用 LLM 根据 prompt_template 将原始内容转化为自然语言文本。
    在测试中会通过 patch 进行 mock。
    """
    from langchain_openai import ChatOpenAI  # type: ignore[import]

    prompt_template = transform_params.get("prompt_template", "{content}")
    prompt = prompt_template.replace("{content}", content)

    model_name = config.get("transform_model") or config.get("escalate_model")
    if not model_name:
        raise ValueError(
            "transform_model or escalate_model must be provided for llm_transform"
        )

    chat = ChatOpenAI(
        model=model_name,
        api_key=config.get("llm_api_key", ""),
        base_url=config.get("llm_base_url") or None,
    )
    resp = chat.invoke(prompt)
    # langchain_openai.ChatOpenAI 返回的是 BaseMessage
    return getattr(resp, "content", str(resp))


def apply_strategy(
    segments: List[TypedSegment],
    raw_chunk,
    doc_metadata: dict,
    config: dict,
) -> List[DocumentChunk]:
    """
    当前版本：无论 strategy 为何，都统一通过 LLM 转写为向量化文本。
    未来如果需要区分不同策略，可以在此处分支。
    """
    results: List[DocumentChunk] = []

    for seg in segments:
        raw_content = raw_chunk["content"]
        strategy = seg["transform_params"].get("strategy", "llm_transform")

        llm_text = _call_llm_transform(seg["content"], seg["transform_params"], config)

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
                    "transform_strategy": strategy,
                    "segment_raw_content": seg["content"],
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
            state.get("config", {}),
        )
        final_chunks.extend(chunks)
    return {"final_chunks": final_chunks}
