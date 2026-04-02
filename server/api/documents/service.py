from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncGenerator
from typing import Any

from config import settings
from services.kb_service import KBService
from services.parser_workflow_service import ParserWorkflowService


class DocumentsService:
    """Knowledge Base 文档管理，可通过构造参数注入 mock 实现单测。"""

    def __init__(
        self,
        kb_service: KBService,
        parser_workflow_service: ParserWorkflowService,
    ):
        self._kb_service = kb_service
        self._parser_workflow_service = parser_workflow_service

    def get_all_documents(self) -> list[dict[str, Any]]:
        return self._kb_service.get_all_documents()

    def document_exists(self, doc_id: str) -> bool:
        return self._kb_service.document_exists(doc_id)

    def delete_document(self, doc_id: str) -> dict[str, Any]:
        return self._kb_service.delete_document(doc_id)

    async def create_document(self, chunks: list, doc_metadata: dict) -> None:
        """将解析后的 chunks 写入知识库。"""
        await self._kb_service.upload_chunks(chunks, doc_metadata)

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
            async for event in self._parser_workflow_service.run_parse_workflow(
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
        return self._kb_service.update_document(doc_id, fields)

    def clear_all(self) -> dict[str, Any]:
        """清空所有文档和 chunks（ChromaDB + FTS）。"""
        return self._kb_service.clear_all()
