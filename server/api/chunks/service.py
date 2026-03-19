from __future__ import annotations

from typing import Any

from kb.clients import get_chroma_client
from kb.embeddings import embed_batch
from kb.writer import fts_writer


def get_collection():
    return get_chroma_client().get_or_create_collection("knowledge_base")


class ChunksService:

    @staticmethod
    def get_chunks(
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

        where_clause = _build_where(where)
        col = get_collection()

        result = col.get(
            include=["documents", "metadatas"],
            limit=limit,
            offset=offset,
            where=where_clause,
        )
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

    @staticmethod
    def get_chunk_by_id(chunk_id: str) -> dict[str, Any] | None:
        result = get_collection().get(
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

    @staticmethod
    async def update_chunk(
        chunk_id: str,
        content: str,
        semantic_type: str,
        section_path: str,  # "/" 分隔
    ) -> dict[str, Any]:
        col = get_collection()
        existing = col.get(ids=[chunk_id], include=["metadatas"])
        if not (existing.get("ids") or []):
            raise ValueError(f"chunk {chunk_id} not found")

        old_meta = (existing.get("metadatas") or [{}])[0]
        new_section_path_pipe = section_path.replace("/", "|")

        embeddings = await embed_batch([content])

        new_meta = {
            **old_meta,
            "semantic_type": semantic_type,
            "section_path": new_section_path_pipe,
        }
        col.upsert(
            ids=[chunk_id],
            documents=[content],
            embeddings=embeddings,
            metadatas=[new_meta],
        )

        # 同步更新 FTS（先确保表已初始化）
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

    @staticmethod
    def delete_chunk(chunk_id: str) -> None:
        col = get_collection()
        col.delete(ids=[chunk_id])


def _build_where(where: dict) -> dict | None:
    if not where:
        return None
    items = [{k: v} for k, v in where.items()]
    if len(items) == 1:
        return items[0]
    return {"$and": items}
