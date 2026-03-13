from __future__ import annotations

from typing import List

from app.core.parser_workflow.models import (
    ClassifiedChunk,
    DocumentChunk,
    TypedSegment,
    WorkflowState,
    make_chunk_id,
)


def dominant_content_type(segments: List[TypedSegment]) -> str:
    """按字符数占比最高的 segment 的 content_type。"""
    if not segments:
        return "plain_text"
    return max(segments, key=lambda s: len(s["content"]))["content_type"]


def _parse_table(table_md: str):
    """解析 Markdown 表格，返回 (header_row, [data_rows])。"""
    lines = [l for l in table_md.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return None, []
    header = lines[0]
    data_rows = lines[2:]
    return header, data_rows


def _make_single_chunk(seg, raw_chunk, doc_metadata, content_type) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=make_chunk_id(
            doc_metadata.get("standard_no", ""),
            raw_chunk["section_path"],
            seg["content"],
        ),
        doc_metadata=doc_metadata,
        section_path=raw_chunk["section_path"],
        content_type=content_type,
        content=seg["content"],
        raw_content=raw_chunk["content"],
        meta={},
    )


def apply_strategy(
    segments: List[TypedSegment],
    raw_chunk,
    doc_metadata: dict,
) -> List[DocumentChunk]:
    """将一组 TypedSegment 按各自策略转化为 DocumentChunk 列表。"""
    results: List[DocumentChunk] = []

    for seg in segments:
        strategy = seg["transform_params"].get("strategy", "plain_embed")
        raw_content = raw_chunk["content"]

        if strategy == "split_rows":
            header, data_rows = _parse_table(seg["content"])
            if not data_rows:
                results.append(
                    _make_single_chunk(seg, raw_chunk, doc_metadata, seg["content_type"])
                )
                continue
            for i, row in enumerate(data_rows):
                content = f"{header}\n{row}" if header else row
                results.append(
                    DocumentChunk(
                        chunk_id=make_chunk_id(
                            doc_metadata.get("standard_no", ""),
                            raw_chunk["section_path"],
                            content,
                        ),
                        doc_metadata=doc_metadata,
                        section_path=raw_chunk["section_path"],
                        content_type=seg["content_type"],
                        content=content,
                        raw_content=raw_content,
                        meta={"table_row_index": i},
                    )
                )

        elif strategy == "plain_embed":
            content = " ".join(seg["content"].split())
            results.append(
                DocumentChunk(
                    chunk_id=make_chunk_id(
                        doc_metadata.get("standard_no", ""),
                        raw_chunk["section_path"],
                        content,
                    ),
                    doc_metadata=doc_metadata,
                    section_path=raw_chunk["section_path"],
                    content_type=seg["content_type"],
                    content=content,
                    raw_content=raw_content,
                    meta={},
                )
            )

        else:  # preserve_as_is / preserve_as_list 等
            results.append(
                _make_single_chunk(seg, raw_chunk, doc_metadata, seg["content_type"])
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

