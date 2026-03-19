from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.core.kb.clients import get_chroma_client
from app.core.kb.writer import fts_writer


def get_collection():
    return get_chroma_client().get_or_create_collection("knowledge_base")


class DocumentsService:

    @staticmethod
    def get_all_documents() -> list[dict[str, Any]]:
        result = get_collection().get(include=["metadatas"])
        metadatas = result.get("metadatas") or []

        doc_map: dict[str, dict] = {}
        for meta in metadatas:
            doc_id = meta.get("doc_id", "unknown")
            if doc_id not in doc_map:
                doc_map[doc_id] = {
                    "doc_id": doc_id,
                    "standard_no": meta.get("standard_no", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "chunks_count": 0,
                }
            doc_map[doc_id]["chunks_count"] += 1

        return sorted(doc_map.values(), key=lambda d: d["doc_id"])

    @staticmethod
    def delete_document(doc_id: str) -> dict[str, Any]:
        get_collection().delete(where={"doc_id": {"$eq": doc_id}})
        errors: list[str] = []
        fts_writer.delete_by_doc_id(doc_id, errors)
        return {"doc_id": doc_id, "errors": errors}

    @staticmethod
    async def upload_document(
        file_content: bytes,
        filename: str,
        strategy: str,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> dict[str, Any]:
        raise HTTPException(status_code=501, detail="文档上传功能尚未实现，请通过 parser_workflow 直接写入知识库")
