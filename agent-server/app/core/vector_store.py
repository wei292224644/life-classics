"""
向量存储管理 - 基于ChromaDB (LangChain版本)
"""

import os
from typing import List, Optional, Dict
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.core.embeddings import get_embedding_model


class VectorStoreManager:
    """向量存储管理器"""

    def __init__(self):
        """初始化向量存储"""
        # 确保持久化目录存在
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

    def add_documents(self, documents: List[Document]):
        """
        添加文档到向量存储
        
        如果启用父子chunk模式，需要特殊处理
        """
        if settings.ENABLE_PARENT_CHILD:
            # 父子chunk模式：使用分层文本分割
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            
            # 创建父chunk分割器
            parent_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.PARENT_CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            
            # 创建子chunk分割器
            child_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.CHILD_CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP,
            )
            
            # 先创建父chunk
            parent_docs = parent_splitter.split_documents(documents)
            
            # 为每个父chunk创建子chunk
            all_docs = []
            for parent_doc in parent_docs:
                # 添加父chunk
                parent_doc.metadata["chunk_type"] = "parent"
                all_docs.append(parent_doc)
                
                # 创建子chunk
                child_docs = child_splitter.split_documents([parent_doc])
                for child_doc in child_docs:
                    child_doc.metadata["chunk_type"] = "child"
                    child_doc.metadata["parent_id"] = id(parent_doc)
                    all_docs.append(child_doc)
            
            # 添加到向量存储
            self.vector_store.add_documents(all_docs)
        else:
            # 普通模式：直接添加文档
            self.vector_store.add_documents(documents)

    def query(self, query_str: str, top_k: int = 5) -> List[Document]:
        """
        查询相似文档
        
        如果启用父子chunk模式，优先返回父chunk
        """
        # 使用相似度搜索
        results = self.vector_store.similarity_search_with_score(
            query_str, k=top_k * 3 if settings.ENABLE_PARENT_CHILD else top_k
        )
        
        if settings.ENABLE_PARENT_CHILD:
            # 父子chunk模式：优先返回父chunk，合并子chunk到父chunk
            parent_docs = {}
            child_docs = []
            
            for doc, score in results:
                chunk_type = doc.metadata.get("chunk_type", "normal")
                if chunk_type == "parent":
                    parent_id = id(doc)
                    if parent_id not in parent_docs:
                        parent_docs[parent_id] = (doc, score)
                elif chunk_type == "child":
                    child_docs.append((doc, score))
            
            # 合并子chunk到父chunk
            final_results = []
            for parent_id, (parent_doc, parent_score) in parent_docs.items():
                # 找到属于这个父chunk的子chunk
                related_children = [
                    (doc, score) for doc, score in child_docs
                    if doc.metadata.get("parent_id") == parent_id
                ]
                
                # 合并子chunk文本到父chunk
                if related_children:
                    child_texts = [doc.page_content for doc, _ in related_children]
                    parent_doc.page_content += "\n\n" + "\n\n".join(child_texts)
                
                final_results.append((parent_doc, parent_score))
            
            # 按分数排序并返回top_k
            final_results.sort(key=lambda x: x[1], reverse=True)
            return [doc for doc, _ in final_results[:top_k]]
        else:
            # 普通模式：直接返回结果
            return [doc for doc, _ in results[:top_k]]

    def delete_all(self):
        """清空所有文档"""
        # 删除集合并重新创建
        self.vector_store.delete_collection()
        self.vector_store = Chroma(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            collection_name=settings.CHROMA_COLLECTION_NAME,
            embedding_function=self.embedding_model,
        )
        return True

    def get_collection_info(self) -> dict:
        """获取集合信息"""
        count = self.vector_store._collection.count()
        return {
            "collection_name": settings.CHROMA_COLLECTION_NAME,
            "document_count": count,
            "persist_dir": settings.CHROMA_PERSIST_DIR,
        }

    def get_all_documents(self) -> List[dict]:
        """
        获取所有文档块
        
        Returns:
            文档块列表，每个块包含文本和元数据
        """
        # 从ChromaDB获取所有数据
        results = self.vector_store._collection.get()
        
        documents = []
        if results and "ids" in results:
            ids = results.get("ids", [])
            documents_data = results.get("documents", [])
            metadatas = results.get("metadatas", [])
            
            for i, doc_id in enumerate(ids):
                doc_text = documents_data[i] if i < len(documents_data) else ""
                doc_metadata = metadatas[i] if i < len(metadatas) else {}
                
                documents.append(
                    {"id": doc_id, "text": doc_text, "metadata": doc_metadata}
                )
        
        return documents

    def get_retriever(self, top_k: int = 5):
        """获取检索器"""
        return self.vector_store.as_retriever(
            search_kwargs={"k": top_k}
        )


# 全局向量存储管理器实例
vector_store_manager = VectorStoreManager()
