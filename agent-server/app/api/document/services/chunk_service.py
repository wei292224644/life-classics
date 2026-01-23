"""
Chunk 管理服务
处理 Chunk 的查询和统计操作
"""

import json
from typing import Optional, List, Dict, Any

from app.core.kb.vector_store import vector_store_manager
from app.api.document.models import ChunkResponse


class ChunkService:
    """Chunk 管理服务类"""

    @staticmethod
    def _restore_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        还原复杂的 metadata（将 JSON 字符串转换为对象）

        Args:
            metadata: 原始 metadata

        Returns:
            还原后的 metadata
        """
        restored_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, (list, dict)):
                        restored_metadata[key] = parsed
                    else:
                        restored_metadata[key] = value
                except (json.JSONDecodeError, TypeError):
                    restored_metadata[key] = value
            else:
                restored_metadata[key] = value
        return restored_metadata

    @staticmethod
    def get_chunks(
        limit: Optional[int] = None,
        offset: int = 0,
        doc_id: Optional[str] = None,
        markdown_id: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> tuple[List[ChunkResponse], Optional[int]]:
        """
        获取 chunks（支持分页和过滤）

        Args:
            limit: 返回的最大文档数量
            offset: 跳过的文档数量
            doc_id: 按文档 ID 过滤
            markdown_id: 按 markdown ID 过滤
            content_type: 按内容类型过滤

        Returns:
            (chunks 列表, 总数)
        """
        # 构建过滤条件
        where = {}
        if doc_id:
            where["doc_id"] = doc_id
        if markdown_id:
            where["markdown_id"] = markdown_id
        if content_type:
            where["content_type"] = content_type

        # 获取文档
        include = ["documents", "metadatas"]
        where_clause = where if where else None
        results = vector_store_manager.vector_store._collection.get(
            include=include,
            limit=limit,
            offset=offset,
            where=where_clause,
        )

        ids = results.get("ids", []) or []
        documents_data = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []

        # 还原复杂的 metadata 并过滤
        chunks = []
        for i, chunk_id in enumerate(ids):
            metadata = metadatas[i] if i < len(metadatas) else {}
            restored_metadata = ChunkService._restore_metadata(metadata)

            # 额外的客户端过滤：如果指定了 doc_id 或 markdown_id，确保 metadata 中的值匹配
            if doc_id and restored_metadata.get("doc_id") != doc_id:
                continue
            if markdown_id and restored_metadata.get("markdown_id") != markdown_id:
                continue

            chunks.append(
                ChunkResponse(
                    id=chunk_id,
                    content=documents_data[i] if i < len(documents_data) else "",
                    metadata=restored_metadata,
                )
            )

        # 获取总数
        total = None
        if limit is not None:
            try:
                count_results = vector_store_manager.vector_store._collection.get(
                    include=[],
                    where=where_clause,
                )
                # 如果指定了 doc_id 或 markdown_id，还需要在客户端再次过滤以确保准确性
                if doc_id or markdown_id:
                    filtered_ids = []
                    filtered_metadatas = count_results.get("metadatas", []) or []
                    filtered_ids_list = count_results.get("ids", []) or []
                    for j, meta in enumerate(filtered_metadatas):
                        if j < len(filtered_ids_list):
                            # 检查 doc_id 和 markdown_id 是否匹配
                            if doc_id and meta.get("doc_id") != doc_id:
                                continue
                            if markdown_id and meta.get("markdown_id") != markdown_id:
                                continue
                            filtered_ids.append(filtered_ids_list[j])
                    total = len(filtered_ids)
                else:
                    total = len(count_results.get("ids", []))
            except:
                pass

        return chunks, total

    @staticmethod
    def get_chunks_info() -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            统计信息字典
        """
        results = vector_store_manager.vector_store._collection.get(include=[])
        count = len(results.get("ids", []))

        # 获取所有文档的 metadata 来统计
        all_results = vector_store_manager.vector_store._collection.get(
            include=["metadatas"],
            limit=count if count < 10000 else 10000,
        )
        metadatas = all_results.get("metadatas", []) or []

        # 统计文档类型和文档 ID
        doc_types = {}
        doc_ids = set()
        for metadata in metadatas:
            doc_id = metadata.get("doc_id", "unknown")
            doc_ids.add(doc_id)
            content_type = metadata.get("content_type", "unknown")
            doc_types[content_type] = doc_types.get(content_type, 0) + 1

        return {
            "status": "success",
            "total_chunks": count,
            "total_doc_ids": len(doc_ids),
            "content_types": doc_types,
            "doc_ids": sorted(list(doc_ids)),
        }
