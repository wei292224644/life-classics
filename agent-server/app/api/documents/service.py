from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

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
        from app.core.kb import import_file_step

        file_ext = Path(filename).suffix.lower()
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as f:
                f.write(file_content)
                temp_path = f.name

            documents = import_file_step(
                file_path=temp_path,
                strategy=strategy,
                original_filename=filename,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            doc_id = documents[0].doc_id if documents else None
            return {
                "success": bool(documents),
                "message": f"成功导入 {len(documents)} 个 chunks" if documents else "未能提取内容",
                "doc_id": doc_id,
                "chunks_count": len(documents),
                "file_name": filename,
                "strategy": strategy,
            }
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)
