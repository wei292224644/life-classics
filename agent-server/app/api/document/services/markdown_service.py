"""
Markdown 管理服务
处理 Markdown 的增删改查操作
"""

from typing import Optional, List, Dict, Any
from pathlib import Path

from app.core.markdown_db import markdown_db
from app.core.kb import split_step
from app.core.kb.vector_store import vector_store_manager
from app.core.document_chunk import DocumentChunk, ContentType


class MarkdownService:
    """Markdown 管理服务类"""

    @staticmethod
    def get_markdowns_by_doc_id(doc_id: str) -> List[Dict[str, Any]]:
        """
        获取文档的所有 markdown 列表

        Args:
            doc_id: 文档 ID

        Returns:
            markdown 记录列表
        """
        markdowns = markdown_db.get_markdowns_by_doc_id(doc_id)

        # 格式化返回数据
        markdown_list = [
            {
                "markdown_id": m["markdown_id"],
                "doc_id": m["doc_id"],
                "doc_title": m["doc_title"],
                "created_at": m["created_at"],
                "updated_at": m["updated_at"],
            }
            for m in markdowns
        ]

        return markdown_list

    @staticmethod
    def check_markdown(
        doc_id: str, markdown_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        检查文档是否有 markdown

        Args:
            doc_id: 文档 ID
            markdown_id: markdown ID（可选）

        Returns:
            检查结果字典
        """
        if markdown_id:
            # 检查指定的 markdown_id
            markdown_record = markdown_db.get_markdown(markdown_id)
            exists = markdown_record is not None
            return {
                "status": "success",
                "doc_id": doc_id,
                "markdown_id": markdown_id,
                "exists": exists,
            }
        else:
            # 检查是否有任何 markdown
            markdowns = markdown_db.get_markdowns_by_doc_id(doc_id)
            exists = len(markdowns) > 0
            return {
                "status": "success",
                "doc_id": doc_id,
                "exists": exists,
                "count": len(markdowns),
            }

    @staticmethod
    def get_markdown(
        doc_id: str, markdown_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取 markdown 内容

        Args:
            doc_id: 文档 ID
            markdown_id: markdown ID（可选，如果不提供则返回第一个）

        Returns:
            markdown 内容字典

        Raises:
            ValueError: 如果 markdown 不存在
        """
        if markdown_id:
            # 使用指定的 markdown_id
            markdown_record = markdown_db.get_markdown(markdown_id)
            if not markdown_record:
                raise ValueError(
                    f"markdown_cache (markdown_id: {markdown_id}) 不存在"
                )
            # 验证 markdown 是否属于该 doc_id
            if markdown_record.get("doc_id") != doc_id:
                raise ValueError(
                    f"markdown_id {markdown_id} 不属于文档 {doc_id}"
                )
            file_id = markdown_id
        else:
            # 如果没有提供 markdown_id，获取第一个 markdown
            markdowns = markdown_db.get_markdowns_by_doc_id(doc_id)
            if not markdowns:
                raise ValueError(f"文档 {doc_id} 没有 markdown 记录")
            markdown_record = markdowns[0]
            file_id = markdown_record["markdown_id"]

        return {
            "status": "success",
            "doc_id": doc_id,
            "markdown_id": file_id,
            "content": markdown_record["content"],
            "doc_title": markdown_record.get("doc_title"),
            "created_at": markdown_record.get("created_at"),
            "updated_at": markdown_record.get("updated_at"),
        }

    @staticmethod
    def update_markdown(
        doc_id: str, content: str, markdown_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        更新 markdown 内容

        Args:
            doc_id: 文档 ID
            content: markdown 内容
            markdown_id: markdown ID（可选）

        Returns:
            更新结果字典
        """
        # 如果提供了 markdown_id，使用 markdown_id；否则使用 doc_id
        file_id = markdown_id if markdown_id else doc_id

        # 更新数据库（文件保存由 markdown_db 内部处理）
        existing = markdown_db.get_markdown(file_id)
        if existing:
            # 更新现有记录
            markdown_db.update_markdown_content(file_id, content)
        else:
            # 插入新记录（如果不存在）
            # 使用文件名作为 doc_title，如果没有则使用 doc_id 的前8位
            doc_title = Path(file_id).stem if file_id != doc_id else doc_id[:8]
            markdown_db.insert_markdown(
                markdown_id=file_id,
                doc_id=doc_id,
                doc_title=doc_title,
                content=content,
            )

        return {
            "status": "success",
            "message": f"markdown_cache 已更新",
            "doc_id": doc_id,
            "markdown_id": file_id,
        }

    @staticmethod
    def reprocess_markdown(
        doc_id: str, strategy: str, markdown_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        重新处理 markdown：删除现有 chunks，从数据库重新导入

        Args:
            doc_id: 文档 ID
            strategy: 切分策略
            markdown_id: markdown ID（可选）

        Returns:
            重新处理结果字典

        Raises:
            ValueError: 如果 markdown 不存在或删除失败
        """
        # 如果提供了 markdown_id，使用 markdown_id；否则使用 doc_id
        file_id = markdown_id if markdown_id else doc_id

        # 从数据库读取 markdown 内容
        markdown_record = markdown_db.get_markdown(file_id)

        if not markdown_record:
            raise ValueError(
                f"markdown_cache (markdown_id: {file_id}) 不存在，无法重新处理"
            )

        # 1. 删除该 markdown 的所有 chunks
        # 如果提供了 markdown_id，只删除该 markdown_id 的 chunks；否则删除 doc_id 的所有 chunks
        if markdown_id:
            # 根据 markdown_id 删除 chunks
            success = vector_store_manager.delete_by_markdown_id(markdown_id)
        else:
            # 向后兼容：根据 doc_id 删除所有 chunks
            success = vector_store_manager.delete_by_doc_id(doc_id)

        if not success:
            raise RuntimeError("删除现有 chunks 失败")

        # 2. 从数据库读取 markdown 内容
        markdown_content = markdown_record["content"]
        doc_title = markdown_record.get("doc_title", doc_id[:8])

        # 使用原有的 markdown_id 创建 DocumentChunk
        documents = [
            DocumentChunk(
                doc_id=doc_id,
                doc_title=doc_title,
                section_path=[],
                content_type=ContentType.NOTE,
                content=markdown_content,
                meta={
                    "file_name": f"{file_id}.md",
                    "file_path": f"markdown_db:{file_id}",
                    "source_format": "markdown",
                },
                markdown_id=file_id,  # 使用原有的 markdown_id
            )
        ]

        if not documents:
            raise RuntimeError("从数据库导入失败")

        # 3. 执行后续流程（split + vector store）
        documents = split_step(documents, strategy)
        vector_store_manager.add_chunks(documents)

        return {
            "status": "success",
            "message": f"文档 {doc_id} (markdown_id: {file_id}) 已重新处理",
            "doc_id": doc_id,
            "markdown_id": file_id,
            "chunks_count": len(documents),
        }
