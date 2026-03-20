from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from kb.clients import get_chroma_client
from kb.writer import chroma_writer, fts_writer
from parser.graph import run_parser_workflow, run_parser_workflow_stream


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
        try:
            md_content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="文件编码错误，请确保文件为 UTF-8 编码")

        # doc_id 取文件名去掉扩展名
        doc_id = os.path.splitext(filename)[0]
        doc_metadata = {
            "doc_id": doc_id,
            "standard_no": doc_id,
            "doc_type": "standard",
        }

        rules_dir = str(Path(__file__).parent.parent.parent / "parser" / "rules")

        result = await run_parser_workflow(
            md_content=md_content,
            doc_metadata=doc_metadata,
            rules_dir=rules_dir,
        )

        if result.chunks:
            await chroma_writer.write(result.chunks, doc_metadata)
            fts_writer.write(result.chunks, doc_metadata)

        return {
            "success": True,
            "message": f"上传成功，共生成 {len(result.chunks)} 个 chunk",
            "doc_id": doc_id,
            "chunks_count": len(result.chunks),
            "file_name": filename,
            "strategy": strategy,
        }

    @staticmethod
    async def upload_document_stream(
        file_content: bytes,
        filename: str,
    ) -> AsyncGenerator[str, None]:
        """流式上传文档，yield SSE 格式字符串（每条：data: <json>\n\n）。"""
        try:
            md_content = file_content.decode("utf-8")
        except UnicodeDecodeError:
            yield f"data: {json.dumps({'type': 'error', 'message': '文件编码错误，请确保文件为 UTF-8 编码'})}\n\n"
            return

        doc_id = os.path.splitext(filename)[0]
        doc_metadata = {
            "doc_id": doc_id,
            "standard_no": doc_id,
            "doc_type": "standard",
        }
        rules_dir = str(Path(__file__).parent.parent.parent / "parser" / "rules")

        try:
            async for event in run_parser_workflow_stream(
                md_content=md_content,
                doc_metadata=doc_metadata,
                rules_dir=rules_dir,
            ):
                if event["type"] == "workflow_done":
                    chunks = event["chunks"]
                    if chunks:
                        await chroma_writer.write(chunks, doc_metadata)
                        fts_writer.write(chunks, doc_metadata)
                    yield f"data: {json.dumps({'type': 'done', 'chunks_count': len(chunks)})}\n\n"
                else:
                    yield f"data: {json.dumps(event)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    @staticmethod
    def clear_all() -> dict[str, Any]:
        """
        清空所有文档和 chunks（ChromaDB + FTS）。
        Returns:
            {
                "status": "success",
                "deleted_documents": int,
                "deleted_chunks": int,
            }
        """
        # 获取删除前的统计
        collection = get_collection()
        all_results = collection.get(include=["metadatas"])
        metadatas = all_results.get("metadatas") or []
        doc_ids = {m.get("doc_id") for m in metadatas if m.get("doc_id")}
        total_chunks = len(all_results.get("ids") or [])

        # 清空 ChromaDB（用 ids 批量删除，避免 where={} 不被支持）
        all_ids = all_results.get("ids") or []
        if all_ids:
            collection.delete(ids=all_ids)

        # 清空 FTS
        fts_writer.clear_all()

        return {
            "status": "success",
            "deleted_documents": len(doc_ids),
            "deleted_chunks": total_chunks,
        }
