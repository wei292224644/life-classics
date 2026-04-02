"""KB 业务编排服务 — L2 层，操作 ChromaDB / FTS."""
from __future__ import annotations

import asyncio
from typing import Any, Callable

from kb.clients import get_chroma_client, KB_COLLECTION_NAME
from kb.embeddings import embed_batch
from kb.writer import chroma_writer, fts_writer


def _default_collection_getter():
    return get_chroma_client().get_or_create_collection(KB_COLLECTION_NAME)


class KBService:
    """L2: 知识库业务编排 — 操作 ChromaDB / FTS."""

    def __init__(
        self,
        collection_getter: Callable = _default_collection_getter,
    ):
        self._get_collection = collection_getter

    def get_collection(self):
        return self._get_collection()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文本."""
        return await embed_batch(texts)

    def init_fts(self) -> None:
        """初始化 FTS 数据库."""
        fts_writer.init_db()

    def write_fts_chunks(self, chunks: list, doc_metadata: dict) -> None:
        """写入 FTS chunks."""
        fts_writer.write(chunks, doc_metadata)

    async def get_chunks(
        self,
        where: dict | None = None,
        limit: int = 20,
        offset: int = 0,
        include: list[str] | None = None,
        ids: list[str] | None = None,
    ) -> dict:
        """获取 chunks，支持过滤条件和 ID 列表."""
        if include is None:
            include = ["documents", "metadatas"]

        def _do():
            col = self._get_collection()
            return col.get(include=include, limit=limit, offset=offset, where=where, ids=ids)

        return await asyncio.to_thread(_do)

    async def upsert_chunks(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> None:
        """批量 upsert chunks 到 ChromaDB."""

        def _do():
            col = self._get_collection()
            col.upsert(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

        await asyncio.to_thread(_do)

    async def delete_chunks(self, ids: list[str]) -> None:
        """删除指定 chunks."""

        def _do():
            self._get_collection().delete(ids=ids)

        await asyncio.to_thread(_do)

    @staticmethod
    def get_stats() -> dict[str, Any]:
        """获取知识库统计信息."""
        collection = get_chroma_client().get_or_create_collection(KB_COLLECTION_NAME)
        result = collection.get(include=["metadatas"])
        metadatas = result.get("metadatas") or []
        ids = result.get("ids") or []

        doc_ids: set = set()
        semantic_types: dict[str, int] = {}
        for meta in metadatas:
            doc_ids.add(meta.get("doc_id", "unknown"))
            st = meta.get("semantic_type", "unknown")
            semantic_types[st] = semantic_types.get(st, 0) + 1

        return {
            "total_chunks": len(ids),
            "total_documents": len(doc_ids),
            "semantic_types": semantic_types,
        }

    @staticmethod
    def get_all_documents() -> list[dict[str, Any]]:
        """获取所有文档列表（按 doc_id 聚合）。"""
        collection = get_chroma_client().get_or_create_collection(KB_COLLECTION_NAME)
        result = collection.get(include=["metadatas"])
        metadatas = result.get("metadatas") or []

        doc_map: dict[str, dict] = {}
        for meta in metadatas:
            doc_id = meta.get("doc_id", "unknown")
            if doc_id not in doc_map:
                doc_map[doc_id] = {
                    "doc_id": doc_id,
                    "title": meta.get("title", ""),
                    "standard_no": meta.get("standard_no", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "chunks_count": 0,
                }
            doc_map[doc_id]["chunks_count"] += 1

        return sorted(doc_map.values(), key=lambda d: d["doc_id"])

    @staticmethod
    async def upload_chunks(chunks: list, doc_metadata: dict) -> None:
        """将解析后的 chunks 写入知识库（ChromaDB + FTS）."""
        await chroma_writer.write(chunks, doc_metadata)
        fts_writer.write(chunks, doc_metadata)

    @staticmethod
    def delete_document(doc_id: str) -> dict[str, Any]:
        """从 ChromaDB 和 FTS 删除指定文档的所有 chunks."""
        collection = get_chroma_client().get_or_create_collection(KB_COLLECTION_NAME)
        result = collection.get(where={"doc_id": {"$eq": doc_id}}, include=["metadatas"])
        ids = result.get("ids") or []
        if not ids:
            raise ValueError(f"Document '{doc_id}' not found")
        collection.delete(where={"doc_id": {"$eq": doc_id}})
        errors: list[str] = []
        fts_writer.delete_by_doc_id(doc_id, errors)
        return {"doc_id": doc_id, "errors": errors}

    @staticmethod
    def document_exists(doc_id: str) -> bool:
        """检查文档是否已存在."""
        collection = get_chroma_client().get_or_create_collection(KB_COLLECTION_NAME)
        result = collection.get(where={"doc_id": {"$eq": doc_id}}, include=["metadatas"])
        return bool(result.get("ids"))

    @staticmethod
    def search_similar(
        query_vector: list[float],
        top_k: int = 5,
    ) -> dict[str, Any]:
        """向量检索."""
        collection = get_chroma_client().get_or_create_collection(KB_COLLECTION_NAME)
        results = collection.query(query_embeddings=[query_vector], n_results=top_k)
        return results

    @staticmethod
    def clear_all() -> dict[str, Any]:
        """清空知识库（ChromaDB + FTS）."""
        collection = get_chroma_client().get_or_create_collection(KB_COLLECTION_NAME)
        all_results = collection.get(include=["metadatas"])
        metadatas = all_results.get("metadatas") or []
        doc_ids = {m.get("doc_id") for m in metadatas if m.get("doc_id")}
        total_chunks = len(all_results.get("ids") or [])

        all_ids = all_results.get("ids") or []
        if all_ids:
            collection.delete(ids=all_ids)

        fts_writer.clear_all()

        return {
            "status": "success",
            "deleted_documents": len(doc_ids),
            "deleted_chunks": total_chunks,
        }

    @staticmethod
    def update_document(doc_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """更新该文档所有 chunks 的指定 metadata 字段."""
        collection = get_chroma_client().get_or_create_collection(KB_COLLECTION_NAME)
        result = collection.get(
            where={"doc_id": {"$eq": doc_id}},
            include=["metadatas"],
        )
        ids = result.get("ids") or []
        metadatas = result.get("metadatas") or []

        if not ids:
            raise ValueError(f"Document '{doc_id}' not found")

        updated_metadatas = []
        for meta in metadatas:
            new_meta = dict(meta)
            for key, value in fields.items():
                if value is not None:
                    new_meta[key] = value
            updated_metadatas.append(new_meta)

        collection.update(ids=ids, metadatas=updated_metadatas)

        first = updated_metadatas[0]
        return {
            "doc_id": doc_id,
            "title": first.get("title", ""),
            "standard_no": first.get("standard_no", ""),
            "doc_type": first.get("doc_type", ""),
            "chunks_count": len(ids),
        }
