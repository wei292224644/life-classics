from __future__ import annotations

from typing import List

from typing_extensions import TypedDict


class WriteResult(TypedDict):
    standard_no: str
    chunks_written: int   # 写入尝试的 chunk 总数（len(chunks)），不代表成功数
    chroma_ok: bool
    neo4j_ok: bool
    errors: List[str]
