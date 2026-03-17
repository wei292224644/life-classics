from __future__ import annotations

import hashlib
from typing import List

from typing_extensions import TypedDict


class RawChunk(TypedDict):
    content: str
    section_path: List[str]
    char_count: int


class TypedSegment(TypedDict):
    content: str
    structure_type: str        # 结构维度：paragraph / list / table / formula / header
    semantic_type: str         # 语义维度：metadata / scope / limit / procedure / material / calculation / definition / amendment
    transform_params: dict
    confidence: float
    escalated: bool
    cross_refs: List[str]         # 识别到的所有引用标识符，如 ["表1", "附录A", "图A.1"]
    ref_context: str              # 已解析的被引用表格内容（拼接文本），未解析时为 ""
    failed_table_refs: List[str]  # 尝试内联但未能解析的表格引用标识符


class ClassifiedChunk(TypedDict):
    raw_chunk: RawChunk
    segments: List[TypedSegment]
    has_unknown: bool


class DocumentChunk(TypedDict):
    chunk_id: str
    doc_metadata: dict
    section_path: List[str]
    structure_type: str
    semantic_type: str
    content: str
    raw_content: str
    meta: dict


class ParserResult(TypedDict):
    chunks: List[DocumentChunk]
    doc_metadata: dict
    errors: List[str]
    stats: dict


class WorkflowState(TypedDict):
    md_content: str
    doc_metadata: dict
    config: dict
    rules_dir: str
    raw_chunks: List[RawChunk]
    classified_chunks: List[ClassifiedChunk]
    final_chunks: List[DocumentChunk]
    errors: List[str]


def make_chunk_id(standard_no: str, section_path: List[str], content: str) -> str:
    key = f"{standard_no}|{'|'.join(section_path)}|{content[:100]}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

