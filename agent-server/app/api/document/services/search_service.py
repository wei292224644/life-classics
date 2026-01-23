"""
搜索服务
处理文档搜索相关操作
"""

from typing import List, Optional

from app.core.kb.vector_store import vector_store_manager
from app.api.document.models import SearchResult


class SearchService:
    """搜索服务类"""

    @staticmethod
    def search(
        query: str,
        top_k: int = 10,
        use_rerank: bool = False,
        retrieve_k: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        搜索知识库中的文档

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果
            use_rerank: 是否使用重排序
            retrieve_k: 初始检索的文档数量（重排序时使用）

        Returns:
            搜索结果列表
        """
        if use_rerank:
            # 使用重排序搜索
            retrieve_k = retrieve_k or max(top_k * 2, 20)
            reranked_chunks = vector_store_manager.search_with_rerank(
                query=query,
                top_k=top_k,
                retrieve_k=retrieve_k,
            )

            results = [
                SearchResult(
                    id=chunk.document.metadata.get("chunk_id", ""),
                    content=chunk.document.page_content,
                    metadata=chunk.document.metadata,
                    relevance_score=chunk.relevance_score,
                    relevance_reason=chunk.relevance_reason,
                )
                for chunk in reranked_chunks
            ]
        else:
            # 普通向量搜索
            documents = vector_store_manager.search(
                query=query,
                top_k=top_k,
            )

            results = [
                SearchResult(
                    id=doc.metadata.get("chunk_id", ""),
                    content=doc.page_content,
                    metadata=doc.metadata,
                )
                for doc in documents
            ]

        return results
