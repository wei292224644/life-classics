from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncGenerator
from typing import Any, Callable

from config import settings
from kb.clients import get_chroma_client, KB_COLLECTION_NAME
from kb.writer import chroma_writer, fts_writer
from workflow_parser_kb.graph import run_parser_workflow_stream


def _default_collection_getter():
    return get_chroma_client().get_or_create_collection(KB_COLLECTION_NAME)


class DocumentsService:
    """Knowledge Base 文档管理，可通过构造参数注入 mock 实现单测。"""

    def __init__(
        self,
        collection_getter: Callable = _default_collection_getter,
    ):
        self._get_collection = collection_getter

    def get_all_documents(self) -> list[dict[str, Any]]:
        result = self._get_collection().get(include=["metadatas"])
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

    def document_exists(self, doc_id: str) -> bool:
        result = self._get_collection().get(where={"doc_id": {"$eq": doc_id}}, include=["metadatas"])
        return bool(result.get("ids"))

    def delete_document(self, doc_id: str) -> dict[str, Any]:
        result = self._get_collection().get(where={"doc_id": {"$eq": doc_id}}, include=["metadatas"])
        ids = result.get("ids") or []
        if not ids:
            raise ValueError(f"Document '{doc_id}' not found")
        self._get_collection().delete(where={"doc_id": {"$eq": doc_id}})
        errors: list[str] = []
        fts_writer.delete_by_doc_id(doc_id, errors)
        return {"doc_id": doc_id, "errors": errors}

    async def create_document(self, chunks: list, doc_metadata: dict) -> None:
        """将解析后的 chunks 写入知识库。"""
        await chroma_writer.write(chunks, doc_metadata)
        fts_writer.write(chunks, doc_metadata)

    async def upload_document_stream(
        self,
        file_content: bytes,
        filename: str,
    ) -> AsyncGenerator[str, None]:
        """流式上传文档，yield SSE 格式字符串（每条：data: <json>\n\n）。"""
        try:
            md_content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            yield f"data: {json.dumps({'type': 'error', 'message': '文件编码错误，请确保文件为 UTF-8 编码'})}\n\n"
            return

        doc_title = os.path.splitext(filename)[0]
        rules_dir = settings.RULES_DIR

        try:
            async for event in run_parser_workflow_stream(
                md_content=md_content,
                doc_name=doc_title,
                rules_dir=rules_dir,
            ):
                if event["type"] == "workflow_done":
                    chunks = event["chunks"]
                    doc_metadata = event["doc_metadata"]
                    if chunks:
                        doc_id = doc_metadata.get("doc_id")
                        if self.document_exists(doc_id):
                            await asyncio.to_thread(self.delete_document, doc_id)
                        await self.create_document(chunks, doc_metadata)
                    yield f"data: {json.dumps({'type': 'done', 'chunks_count': len(chunks)})}\n\n"
                else:
                    yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    def update_document(self, doc_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """更新该文档所有 chunks 的指定 metadata 字段。"""
        collection = self._get_collection()
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

    def clear_all(self) -> dict[str, Any]:
        """清空所有文档和 chunks（ChromaDB + FTS）。"""
        collection = self._get_collection()
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
