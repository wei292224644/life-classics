from __future__ import annotations

import asyncio
from typing import List

from typing_extensions import TypedDict

from app.core.kb.writer import chroma_writer, fts_writer
from app.core.parser_workflow.models import WorkflowState

# 模块 import 时初始化 FTS DB（幂等，表已存在则跳过）
fts_writer.init_db()


class StoreResult(TypedDict):
    standard_no: str
    chunks_written: int
    ok: bool
    errors: List[str]


async def store_to_kb(state: WorkflowState) -> StoreResult:
    """
    将 WorkflowState 中的 final_chunks 写入 ChromaDB 和 SQLite FTS5。

    流程：
    1. 取 state["doc_metadata"]["standard_no"]，缺失则返回 ok=False
    2. 并行删除旧数据（ChromaDB + SQLite），任一失败则终止，不执行写入
    3. 并行写入（ChromaDB + SQLite），各自独立捕获错误
    4. 任一写入失败则 ok=False

    注意：不传播 state["errors"]（parse 阶段警告与存储无关）
    """
    errors: List[str] = []

    standard_no = state["doc_metadata"].get("standard_no")
    if not standard_no:
        errors.append("ERROR: standard_no missing, cannot write to KB")
        return StoreResult(
            standard_no="",
            chunks_written=0,
            ok=False,
            errors=errors,
        )

    chunks = state["final_chunks"]
    doc_metadata = state["doc_metadata"]

    # 并行删除
    chroma_del_ok, fts_del_ok = await asyncio.gather(
        chroma_writer.delete_by_standard_no(standard_no, errors),
        asyncio.to_thread(fts_writer.delete_by_standard_no, standard_no, errors),
    )

    if not (chroma_del_ok and fts_del_ok):
        return StoreResult(
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
        standard_no=standard_no,
        chunks_written=len(chunks),
        ok=chroma_ok and fts_ok,
        errors=errors,
    )
