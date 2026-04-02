"""
ChromaDB Chunk CRUD。

同步/异步设计规则：
- 所有 ChromaDB I/O 操作（get/delete/upsert）在 asyncio.to_thread 中执行，
  保持 async 接口以避免阻塞事件循环。
- 涉及 embed_batch 的操作必须是 async，且 embed 计算完成后在同一 to_thread 块中执行 upsert。
"""
from __future__ import annotations

from typing import Any

from config import settings
from services.kb_service import KBService
from services.parser_workflow_service import ParserWorkflowService


class ChunksService:
    """
    ChromaDB chunk 管理。
    所有方法为 async，内部通过 asyncio.to_thread 将 ChromaDB I/O 操作卸载到线程池，
    避免阻塞事件循环。

    所有 KB 操作（ChromaDB/Embed/FTS）通过 KBService L2 代理，
    所有 parser workflow 操作通过 ParserWorkflowService L2 代理。
    """

    def __init__(
        self,
        kb_service: KBService,
        parser_workflow_service: ParserWorkflowService,
    ):
        self._kb_service = kb_service
        self._parser_workflow_service = parser_workflow_service

    def _build_where(self, where: dict) -> dict | None:
        if not where:
            return None
        items = [{k: v} for k, v in where.items()]
        if len(items) == 1:
            return items[0]
        return {"$and": items}

    async def get_chunks(
        self,
        doc_id: str | None = None,
        semantic_type: str | None = None,
        section_path: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        where: dict = {}
        if doc_id:
            where["doc_id"] = {"$eq": doc_id}
        if semantic_type:
            where["semantic_type"] = {"$eq": semantic_type}
        if section_path:
            where["section_path"] = {"$eq": section_path.replace("/", "|")}

        where_clause = self._build_where(where)

        result = await self._kb_service.get_chunks(
            where=where_clause,
            limit=limit,
            offset=offset,
            include=["documents", "metadatas"],
        )
        count_result = await self._kb_service.get_chunks(
            where=where_clause,
            limit=10000,
            offset=0,
            include=[],
        )

        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        chunks = [
            {"id": ids[i], "content": documents[i], "metadata": metadatas[i]}
            for i in range(len(ids))
        ]
        total = len(count_result.get("ids") or [])
        return chunks, total

    async def get_chunk_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        result = await self._kb_service.get_chunks(
            ids=[chunk_id],
            include=["documents", "metadatas"],
        )
        ids = result.get("ids") or []
        if not ids:
            return None
        return {
            "id": ids[0],
            "content": (result.get("documents") or [""])[0],
            "metadata": (result.get("metadatas") or [{}])[0],
        }

    async def update_chunk(
        self,
        chunk_id: str,
        content: str,
        semantic_type: str,
        section_path: str,
    ) -> dict[str, Any]:
        embeddings = await self._kb_service.embed_batch([content])

        result = await self._kb_service.get_chunks(
            ids=[chunk_id],
            include=["metadatas"],
        )
        existing = result
        if not (existing.get("ids") or []):
            raise ValueError(f"chunk {chunk_id} not found")

        old_meta = (existing.get("metadatas") or [{}])[0]
        new_section_path_pipe = section_path.replace("/", "|")
        new_meta = {**old_meta, "semantic_type": semantic_type, "section_path": new_section_path_pipe}

        await self._kb_service.upsert_chunks(
            ids=[chunk_id],
            documents=[content],
            embeddings=embeddings,
            metadatas=[new_meta],
        )

        self._kb_service.init_fts()
        doc_metadata = {
            "doc_id": old_meta.get("doc_id", ""),
            "standard_no": old_meta.get("standard_no", ""),
            "doc_type": old_meta.get("doc_type", ""),
        }
        fts_chunk = {
            "chunk_id": chunk_id,
            "content": content,
            "semantic_type": semantic_type,
            "section_path": section_path.split("/"),
            "raw_content": old_meta.get("raw_content", ""),
            "doc_metadata": {},
            "meta": {},
        }
        self._kb_service.write_fts_chunks([fts_chunk], doc_metadata)
        return {"id": chunk_id, "content": content, "metadata": new_meta}

    async def delete_chunk(self, chunk_id: str) -> None:
        await self._kb_service.delete_chunks(ids=[chunk_id])

    async def reparse_chunk(self, chunk_id: str) -> dict[str, Any]:
        # Step 1: 读取 chunk 元数据
        result = await self._kb_service.get_chunks(
            ids=[chunk_id],
            include=["documents", "metadatas"],
        )
        if not (result.get("ids") or []):
            raise ValueError(f"chunk {chunk_id} not found")
        old_meta = (result.get("metadatas") or [{}])[0]
        raw_content = old_meta.get("raw_content", "")
        section_path_str = old_meta.get("section_path", "")
        semantic_type = old_meta.get("semantic_type", "")
        structure_type = old_meta.get("structure_type", "paragraph")
        cross_refs = old_meta.get("cross_refs", [])
        failed_table_refs = old_meta.get("failed_table_refs", [])
        doc_metadata = {
            "doc_id": old_meta.get("doc_id", ""),
            "standard_no": old_meta.get("standard_no", ""),
            "doc_type": old_meta.get("doc_type", ""),
        }

        # Step 2: transform + merge（通过 L2 service）
        merged_chunks = await self._parser_workflow_service.reparse_chunk(
            raw_content=raw_content,
            section_path_str=section_path_str,
            semantic_type=semantic_type,
            structure_type=structure_type,
            cross_refs=cross_refs,
            failed_table_refs=failed_table_refs,
            rules_dir=settings.RULES_DIR,
            doc_metadata=doc_metadata,
        )

        if not merged_chunks:
            raise ValueError(f"reparse {chunk_id} produced no chunks")

        merged = merged_chunks[0]

        # Step 3: embed + upsert
        embeddings = await self._kb_service.embed_batch([merged["content"]])

        new_meta = {
            **old_meta,
            "raw_content": old_meta.get("raw_content", ""),
            "semantic_type": merged["semantic_type"],
            "section_path": "|".join(merged["section_path"]),
        }
        await self._kb_service.upsert_chunks(
            ids=[chunk_id],
            documents=[merged["content"]],
            embeddings=embeddings,
            metadatas=[new_meta],
        )
        self._kb_service.init_fts()
        fts_chunk = {
            "chunk_id": chunk_id,
            "content": merged["content"],
            "semantic_type": merged["semantic_type"],
            "section_path": merged["section_path"],
            "raw_content": old_meta.get("raw_content", ""),
            "doc_metadata": {},
            "meta": {},
        }
        self._kb_service.write_fts_chunks([fts_chunk], doc_metadata)
        return {"id": chunk_id, "content": merged["content"], "metadata": new_meta}
