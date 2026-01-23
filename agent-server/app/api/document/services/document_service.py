"""
文档管理服务
处理文档的增删改查操作
"""

import os
import tempfile
import json
from typing import Optional, List, Dict, Any
from pathlib import Path

from app.core.kb import import_file_step
from app.core.kb.vector_store import vector_store_manager
from app.core.markdown_db import markdown_db
from app.api.document.models import DocumentInfo


class DocumentService:
    """文档管理服务类"""

    @staticmethod
    async def upload_document(
        file_content: bytes,
        filename: str,
        strategy: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        上传并导入文档

        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            strategy: 切分策略
            chunk_size: 切分大小
            chunk_overlap: 切分重叠大小

        Returns:
            导入结果字典
        """
        temp_file_path = None
        file_ext = Path(filename).suffix.lower()

        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name

            # 导入文档
            documents = import_file_step(
                file_path=temp_file_path,
                strategy=strategy,
                original_filename=filename,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            if not documents:
                return {
                    "success": False,
                    "message": "未能从文件中提取到内容",
                    "file_name": filename or "unknown",
                    "file_format": file_ext or "unknown",
                    "strategy": strategy,
                }

            # 提取信息
            doc_id = documents[0].doc_id if documents else None
            chunks_count = len(documents)

            return {
                "success": True,
                "message": f"成功导入 {chunks_count} 个 chunks",
                "doc_id": doc_id,
                "chunks_count": chunks_count,
                "file_name": filename or "unknown",
                "file_format": file_ext or "unknown",
                "strategy": strategy,
            }

        finally:
            # 清理临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

    @staticmethod
    def get_all_documents() -> List[DocumentInfo]:
        """
        获取所有文档列表及其统计信息

        Returns:
            文档信息列表
        """
        # 获取所有文档的 metadata
        all_results = vector_store_manager.vector_store._collection.get(
            include=["metadatas"],
        )
        metadatas = all_results.get("metadatas", []) or []
        ids = all_results.get("ids", []) or []

        # 按文档 ID 分组统计
        doc_stats = {}
        for i, metadata in enumerate(metadatas):
            doc_id = metadata.get("doc_id", "unknown")
            doc_title = metadata.get("doc_title", doc_id)
            content_type = metadata.get("content_type", "unknown")
            source = metadata.get("meta", {})
            if isinstance(source, str):
                try:
                    source = json.loads(source)
                except:
                    source = {}
            source_str = source.get("source") if isinstance(source, dict) else None

            if doc_id not in doc_stats:
                doc_stats[doc_id] = {
                    "doc_id": doc_id,
                    "doc_title": doc_title,
                    "chunks_count": 0,
                    "content_types": {},
                    "source": source_str,
                }

            doc_stats[doc_id]["chunks_count"] += 1
            doc_stats[doc_id]["content_types"][content_type] = (
                doc_stats[doc_id]["content_types"].get(content_type, 0) + 1
            )

        # 转换为列表
        documents = [
            DocumentInfo(
                doc_id=info["doc_id"],
                doc_title=info["doc_title"],
                chunks_count=info["chunks_count"],
                content_types=info["content_types"],
                source=info.get("source"),
            )
            for info in doc_stats.values()
        ]

        # 按文档 ID 排序
        documents.sort(key=lambda x: x.doc_id)

        return documents

    @staticmethod
    def delete_document(doc_id: str) -> Dict[str, Any]:
        """
        删除指定文档及其所有 chunks

        Args:
            doc_id: 文档 ID

        Returns:
            删除结果字典
        """
        # 1. 获取该文档的所有 markdown_id
        markdown_ids = markdown_db.get_markdown_ids_by_doc_id(doc_id)

        # 2. 删除向量数据库中的 chunks
        success = vector_store_manager.delete_by_doc_id(doc_id)

        # 3. 删除数据库中的记录
        deleted_count = markdown_db.delete_markdowns_by_doc_id(doc_id)

        if not success:
            raise RuntimeError("删除向量数据失败")

        return {
            "status": "success",
            "message": f"文档 {doc_id} 及其所有 chunks 已删除",
            "deleted_markdowns": deleted_count,
            "markdown_ids": markdown_ids,
        }

    @staticmethod
    def clear_all() -> Dict[str, Any]:
        """
        清空所有文档和 chunks

        Returns:
            清空结果字典
        """
        # 获取删除前的统计信息
        all_results = vector_store_manager.vector_store._collection.get(
            include=["metadatas"]
        )
        metadatas = all_results.get("metadatas", []) or []
        doc_ids = set()
        for metadata in metadatas:
            doc_id = metadata.get("doc_id")
            if doc_id:
                doc_ids.add(doc_id)
        total_chunks = len(all_results.get("ids", []))
        total_docs = len(doc_ids)

        # 清空向量数据库
        success = vector_store_manager.clear_all()

        # 清空 markdown 数据库（删除所有记录）
        deleted_markdowns_count = markdown_db.clear_all()

        if not success:
            raise RuntimeError("清空向量数据失败")

        return {
            "status": "success",
            "message": f"已清空所有数据，共删除 {total_docs} 个文档，{total_chunks} 个 chunks，{deleted_markdowns_count} 个 markdown 记录",
            "deleted_documents": total_docs,
            "deleted_chunks": total_chunks,
            "deleted_markdowns": deleted_markdowns_count,
        }
