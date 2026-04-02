"""KB 业务编排服务 — L2 层，操作 ChromaDB / FTS."""
from __future__ import annotations

from typing import Any

from kb.clients import get_chroma_client, KB_COLLECTION_NAME
from kb.writer import chroma_writer, fts_writer


class KBService:
    """L2: 知识库业务编排 — 操作 ChromaDB / FTS."""

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
