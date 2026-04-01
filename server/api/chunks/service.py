"""
ChromaDB Chunk CRUD。

同步/异步设计规则：
- 所有 ChromaDB I/O 操作（get/delete/upsert）在 asyncio.to_thread 中执行，
  保持 async 接口以避免阻塞事件循环。
- 涉及 embed_batch 的操作必须是 async，且 embed 计算完成后在同一 to_thread 块中执行 upsert。
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from config import settings
from kb.clients import get_chroma_client, KB_COLLECTION_NAME
from kb.embeddings import embed_batch
from kb.writer import fts_writer
from workflow_parser_kb.models import ClassifiedChunk, RawChunk, TypedSegment, WorkflowState
from workflow_parser_kb.nodes.merge_node import merge_node
from workflow_parser_kb.nodes.transform_node import transform_node
from workflow_parser_kb.rules import RulesStore


def _default_collection_getter():
    return get_chroma_client().get_or_create_collection(KB_COLLECTION_NAME)


class ChunksService:
    """
    ChromaDB chunk 管理。
    所有方法为 async，内部通过 asyncio.to_thread 将 ChromaDB I/O 操作卸载到线程池，
    避免阻塞事件循环。
    """

    def __init__(
        self,
        collection_getter: Callable = _default_collection_getter,
    ):
        self._get_collection = collection_getter

    async def get_chunks(
        self,
        doc_id: str | None = None,
        semantic_type: str | None = None,
        section_path: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        def _do():
            where: dict = {}
            if doc_id:
                where["doc_id"] = {"$eq": doc_id}
            if semantic_type:
                where["semantic_type"] = {"$eq": semantic_type}
            if section_path:
                where["section_path"] = {"$eq": section_path.replace("/", "|")}

            where_clause = _build_where(where)
            col = self._get_collection()
            result = col.get(include=["documents", "metadatas"], limit=limit, offset=offset, where=where_clause)
            count_result = col.get(include=[], where=where_clause)

            ids = result.get("ids") or []
            documents = result.get("documents") or []
            metadatas = result.get("metadatas") or []
            chunks = [
                {"id": ids[i], "content": documents[i], "metadata": metadatas[i]}
                for i in range(len(ids))
            ]
            total = len(count_result.get("ids") or [])
            return chunks, total

        return await asyncio.to_thread(_do)

    async def get_chunk_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        def _do():
            col = self._get_collection()
            result = col.get(ids=[chunk_id], include=["documents", "metadatas"])
            ids = result.get("ids") or []
            if not ids:
                return None
            return {
                "id": ids[0],
                "content": (result.get("documents") or [""])[0],
                "metadata": (result.get("metadatas") or [{}])[0],
            }

        return await asyncio.to_thread(_do)

    async def update_chunk(
        self,
        chunk_id: str,
        content: str,
        semantic_type: str,
        section_path: str,
    ) -> dict[str, Any]:
        async def _do():
            embeddings = await embed_batch([content])

            def _sync():
                col = self._get_collection()
                existing = col.get(ids=[chunk_id], include=["metadatas"])
                if not (existing.get("ids") or []):
                    raise ValueError(f"chunk {chunk_id} not found")

                old_meta = (existing.get("metadatas") or [{}])[0]
                new_section_path_pipe = section_path.replace("/", "|")
                new_meta = {**old_meta, "semantic_type": semantic_type, "section_path": new_section_path_pipe}
                col.upsert(ids=[chunk_id], documents=[content], embeddings=embeddings, metadatas=[new_meta])

                fts_writer.init_db()
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
                fts_writer.write([fts_chunk], doc_metadata)
                return {"id": chunk_id, "content": content, "metadata": new_meta}

            return await asyncio.to_thread(_sync)

        return await _do()

    async def delete_chunk(self, chunk_id: str) -> None:
        def _do():
            self._get_collection().delete(ids=[chunk_id])

        await asyncio.to_thread(_do)

    async def reparse_chunk(self, chunk_id: str) -> dict[str, Any]:
        # Step 1: 在线程池中读取 chunk 元数据
        def _read():
            col = self._get_collection()
            existing = col.get(ids=[chunk_id], include=["documents", "metadatas"])
            if not (existing.get("ids") or []):
                raise ValueError(f"chunk {chunk_id} not found")
            old_meta = (existing.get("metadatas") or [{}])[0]
            raw_content = old_meta.get("raw_content", "")
            section_path_str = old_meta.get("section_path", "")
            semantic_type = old_meta.get("semantic_type", "")
            store = RulesStore(settings.RULES_DIR)
            transform_params = store.get_transform_params(semantic_type)
            typed_segment: TypedSegment = {
                "content": old_meta.get("raw_content", ""),
                "structure_type": old_meta.get("structure_type", "paragraph"),
                "semantic_type": semantic_type,
                "transform_params": transform_params,
                "confidence": 1.0,
                "escalated": False,
                "cross_refs": old_meta.get("cross_refs", []),
                "ref_context": "",
                "failed_table_refs": old_meta.get("failed_table_refs", []),
            }
            raw_chunk: RawChunk = {
                "content": raw_content,
                "section_path": section_path_str.split("|") if section_path_str else [],
                "char_count": len(raw_content),
            }
            classified_chunk: ClassifiedChunk = {
                "raw_chunk": raw_chunk,
                "segments": [typed_segment],
                "has_unknown": False,
            }
            doc_metadata = {
                "doc_id": old_meta.get("doc_id", ""),
                "standard_no": old_meta.get("standard_no", ""),
                "doc_type": old_meta.get("doc_type", ""),
            }
            state: WorkflowState = {
                "md_content": "",
                "doc_metadata": doc_metadata,
                "config": {},
                "rules_dir": settings.RULES_DIR,
                "raw_chunks": [],
                "classified_chunks": [classified_chunk],
                "final_chunks": [],
                "errors": [],
            }
            return state, old_meta, doc_metadata

        state, old_meta, doc_metadata = await asyncio.to_thread(_read)

        # Step 2: transform + merge（async workflow）
        transform_result = await transform_node(state)
        final_chunks = transform_result.get("final_chunks", [])
        merge_result = merge_node({"final_chunks": final_chunks, "doc_metadata": doc_metadata})
        merged_chunks = merge_result.get("final_chunks", [])

        if not merged_chunks:
            raise ValueError(f"reparse {chunk_id} produced no chunks")

        merged = merged_chunks[0]

        # Step 3: embed（async 上下文）+ upsert（to_thread 中执行）
        embeddings = await embed_batch([merged["content"]])

        def _upsert(emb):
            col = self._get_collection()
            new_meta = {
                **old_meta,
                "raw_content": old_meta.get("raw_content", ""),
                "semantic_type": merged["semantic_type"],
                "section_path": "|".join(merged["section_path"]),
            }
            col.upsert(
                ids=[chunk_id],
                documents=[merged["content"]],
                embeddings=emb,
                metadatas=[new_meta],
            )
            fts_writer.init_db()
            fts_chunk = {
                "chunk_id": chunk_id,
                "content": merged["content"],
                "semantic_type": merged["semantic_type"],
                "section_path": merged["section_path"],
                "raw_content": old_meta.get("raw_content", ""),
                "doc_metadata": {},
                "meta": {},
            }
            fts_writer.write([fts_chunk], doc_metadata)
            return {"id": chunk_id, "content": merged["content"], "metadata": new_meta}

        return await asyncio.to_thread(_upsert, embeddings)


def _build_where(where: dict) -> dict | None:
    if not where:
        return None
    items = [{k: v} for k, v in where.items()]
    if len(items) == 1:
        return items[0]
    return {"$and": items}
