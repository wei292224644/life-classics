from __future__ import annotations

from kb.clients import get_chroma_client
from kb.writer import fts_writer


def get_collection():
    return get_chroma_client().get_or_create_collection("knowledge_base")


class KBService:

    @staticmethod
    def get_stats() -> dict:
        result = get_collection().get(include=["metadatas"])
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
    def clear_all() -> dict:
        col = get_collection()
        result = col.get(include=["metadatas"])
        ids = result.get("ids") or []
        metadatas = result.get("metadatas") or []

        if ids:
            col.delete(ids=ids)

        doc_ids = {m.get("doc_id") for m in metadatas if m.get("doc_id")}
        errors: list[str] = []
        for doc_id in doc_ids:
            fts_writer.delete_by_doc_id(doc_id, errors)

        return {"deleted_chunks": len(ids), "deleted_documents": len(doc_ids), "errors": errors}
