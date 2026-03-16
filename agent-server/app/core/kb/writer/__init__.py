from __future__ import annotations

import asyncio
from typing import List

from app.core.kb.writer import chroma_writer, neo4j_writer
from app.core.kb.writer.models import WriteResult
from app.core.parser_workflow.models import ParserResult


async def write_to_kb(result: ParserResult) -> WriteResult:
    """
    将 ParserResult 写入 ChromaDB 和 Neo4j。
    先串行删除旧数据，再并行写入两侧。各侧独立捕获错误。
    不抛异常，调用方通过 WriteResult.errors 判断是否成功。

    chunks_written 表示写入尝试数量（len(chunks)），不代表实际成功数。
    删除成功但写入失败时数据丢失，调用方需决定是否重试。
    """
    standard_no = result["doc_metadata"].get("standard_no")
    errors: List[str] = list(result["errors"])

    if not standard_no:
        errors.append("ERROR: standard_no missing, cannot write to KB")
        return WriteResult(
            standard_no="",
            chunks_written=0,
            chroma_ok=False,
            neo4j_ok=False,
            errors=errors,
        )

    chroma_delete_ok = await chroma_writer.delete_by_standard_no(standard_no, errors)
    neo4j_delete_ok = await neo4j_writer.delete_by_standard_no(standard_no, errors)

    async def do_chroma() -> bool:
        try:
            await chroma_writer.write(result["chunks"], result["doc_metadata"])
            return True
        except Exception as e:
            errors.append(f"chroma write error: {e}")
            return False

    async def do_neo4j() -> bool:
        try:
            await neo4j_writer.write(result["chunks"], result["doc_metadata"])
            return True
        except Exception as e:
            errors.append(f"neo4j write error: {e}")
            return False

    async def _false() -> bool:
        return False

    chroma_ok, neo4j_ok = await asyncio.gather(
        do_chroma() if chroma_delete_ok else _false(),
        do_neo4j() if neo4j_delete_ok else _false(),
    )

    return WriteResult(
        standard_no=standard_no,
        chunks_written=len(result["chunks"]),
        chroma_ok=chroma_ok,
        neo4j_ok=neo4j_ok,
        errors=errors,
    )
