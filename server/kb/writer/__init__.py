from __future__ import annotations

import asyncio
from typing import List

from typing_extensions import TypedDict

from kb.writer import chroma_writer, fts_writer
from workflow_parser_kb.models import WorkflowState

_db_initialized = False


class StoreResult(TypedDict):
    doc_id: str
    standard_no: str
    chunks_written: int
    ok: bool
    errors: List[str]


async def store_to_kb(state: WorkflowState) -> StoreResult:
    """
    将 WorkflowState 中的 final_chunks 写入 ChromaDB 和 SQLite FTS5。

    流程：
    1. 取 state["doc_metadata"]["doc_id"]，缺失则返回 ok=False
    2. 并行删除旧数据（ChromaDB + SQLite），任一失败则终止，不执行写入
    3. 并行写入（ChromaDB + SQLite），各自独立捕获错误
    4. 任一写入失败则 ok=False

    注意：不传播 state["errors"]（parse 阶段警告与存储无关）
    """
    global _db_initialized
    if not _db_initialized:
        fts_writer.init_db()
        _db_initialized = True

    errors: List[str] = []

    doc_id = state["doc_metadata"].get("doc_id")
    if not doc_id:
        errors.append("ERROR: doc_id missing, cannot write to KB")
        return StoreResult(
            doc_id="",
            standard_no="",
            chunks_written=0,
            ok=False,
            errors=errors,
        )

    standard_no = state["doc_metadata"].get("standard_no", "")
    chunks = state["final_chunks"]
    doc_metadata = state["doc_metadata"]

    # 并行删除
    chroma_del_ok, fts_del_ok = await asyncio.gather(
        chroma_writer.delete_by_doc_id(doc_id, errors),
        asyncio.to_thread(fts_writer.delete_by_doc_id, doc_id, errors),
    )

    if not (chroma_del_ok and fts_del_ok):
        return StoreResult(
            doc_id=doc_id,
            standard_no=standard_no,
            chunks_written=0,
            ok=False,
            errors=errors,
        )

    # 并行写入，各自独立捕获错误
    async def do_chroma() -> bool:
        try:
            await chroma_writer.write(chunks, doc_metadata)
            return True
        except Exception as e:
            errors.append(f"chroma write error: {e}")
            return False

    async def do_fts() -> bool:
        try:
            await asyncio.to_thread(fts_writer.write, chunks, doc_metadata)
            return True
        except Exception as e:
            errors.append(f"fts write error: {e}")
            return False

    chroma_ok, fts_ok = await asyncio.gather(do_chroma(), do_fts())

    return StoreResult(
        doc_id=doc_id,
        standard_no=standard_no,
        chunks_written=len(chunks),
        ok=chroma_ok and fts_ok,
        errors=errors,
    )
