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
    content_type: str
    transform_params: dict
    confidence: float
    escalated: bool


class ClassifiedChunk(TypedDict):
    raw_chunk: RawChunk
    segments: List[TypedSegment]
    has_unknown: bool


class DocumentChunk(TypedDict):
    chunk_id: str
    doc_metadata: dict
    section_path: List[str]
    content_type: str
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

