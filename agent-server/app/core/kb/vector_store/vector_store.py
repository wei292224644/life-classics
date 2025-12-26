"""
知识库向量存储模块
用于存储和检索知识库中的向量数据
"""

import os
from typing import List, Dict, Any, Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.core.document_chunk import DocumentChunk
from app.core.embeddings import get_embedding_model
from app.core.kb.vector_store.rerank import rerank_documents, RerankedChunk


class VectorStore:
    """
    向量存储类
    """

    def __init__(self, **kwargs):
        """
        初始化向量存储

        Args:
            **kwargs: 向量存储配置参数
        """
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        # 获取嵌入模型
        self.embedding_model = get_embedding_model(
            provider_name=settings.EMBEDDING_PROVIDER,
        )

        # 初始化ChromaDB向量存储
        self.vector_store = Chroma(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=self.embedding_model,
        )

    def add_chunks(self, chunks: List[DocumentChunk]) -> bool:
        """
        添加知识库数据块到向量存储

        Args:
            chunks: 知识库通用数据结构列表

        Returns:
            bool: 是否添加成功
        """
        self.vector_store.add_documents([chunk.to_documents() for chunk in chunks])
        return True

    def search(self, query: str, top_k: int = 10, **kwargs) -> List[Document]:
        """
        搜索相似内容

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果
            **kwargs: 其他搜索参数

        Returns:
            相似的知识库数据块列表
        """
        return self.vector_store.similarity_search(query, k=top_k)

    def search_with_rerank(
        self,
        query: str,
        top_k: int = 5,
        retrieve_k: int = 10,
        use_llm: bool = True,
        **kwargs
    ) -> List[RerankedChunk]:
        """
        搜索相似内容并进行重排序

        Args:
            query: 查询文本
            top_k: 返回前 k 个最相关的结果
            retrieve_k: 初始检索的文档数量（应该 >= top_k）
            use_llm: 是否使用 LLM 进行重排序
            **kwargs: 其他搜索参数

        Returns:
            重排序后的 chunk 列表，按相关性从高到低排序

        Example:
            >>> vector_store = VectorStore()
            >>> reranked = vector_store.search_with_rerank(
            ...     "β-胡萝卜素含量",
            ...     top_k=5,
            ...     retrieve_k=10,
            ...     use_llm=True
            ... )
            >>> for chunk in reranked:
            ...     print(f"分数: {chunk.relevance_score:.2f}")
            ...     print(chunk.document.page_content[:100])
        """
        # 先检索更多文档
        retrieved_docs = self.search(query, top_k=max(retrieve_k, top_k * 2), **kwargs)

        # 进行重排序
        reranked_chunks = rerank_documents(
            query=query,
            documents=retrieved_docs,
            top_k=top_k,
            use_llm=use_llm,
        )

        return reranked_chunks

    def delete_by_doc_id(self, doc_id: str) -> bool:
        """
        根据文档 ID 删除向量数据

        Args:
            doc_id: 文档 ID

        Returns:
            是否删除成功
        """
        self.vector_store.delete(where={"doc_id": doc_id})
        return True
