"""
向量存储管理 - 基于ChromaDB
"""
import os
from typing import List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, StorageContext, Settings as LlamaIndexSettings
from llama_index.core.schema import Document
from app.core.config import settings
from app.core.embeddings import get_embedding_model
from app.core.llm import get_llm


class VectorStoreManager:
    """向量存储管理器"""
    
    def __init__(self):
        """初始化向量存储"""
        # 确保持久化目录存在
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        
        # 配置LlamaIndex设置（包括嵌入模型和LLM）
        try:
            embedding_model = get_embedding_model()
            LlamaIndexSettings.embed_model = embedding_model
        except Exception as e:
            print(f"警告: 无法初始化嵌入模型: {e}")
        
        try:
            llm = get_llm()
            LlamaIndexSettings.llm = llm
        except Exception as e:
            print(f"警告: 无法初始化LLM: {e}")
        
        # 初始化ChromaDB客户端
        self.chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # 获取或创建集合
        self.collection = self.chroma_client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION_NAME
        )
        
        # 创建向量存储
        self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
        
        # 创建存储上下文
        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vector_store
        )
        
        # 初始化索引
        self.index: Optional[VectorStoreIndex] = None
        self._load_index()
    
    def _load_index(self):
        """加载或创建索引"""
        try:
            # 尝试加载现有索引
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=self.vector_store,
                storage_context=self.storage_context
            )
        except Exception:
            # 如果不存在，创建新索引
            self.index = VectorStoreIndex(
                [],
                storage_context=self.storage_context
            )
    
    def add_documents(self, documents: List[Document]):
        """添加文档到向量存储"""
        if not self.index:
            self._load_index()
        
        # 添加文档到索引
        for doc in documents:
            self.index.insert(doc)
    
    def query(self, query_str: str, top_k: int = 5) -> List:
        """查询相似文档"""
        if not self.index:
            self._load_index()
        
        # 创建查询引擎
        query_engine = self.index.as_query_engine(similarity_top_k=top_k)
        
        # 执行查询
        response = query_engine.query(query_str)
        
        return response
    
    def delete_all(self):
        """清空所有文档"""
        try:
            self.chroma_client.delete_collection(name=settings.CHROMA_COLLECTION_NAME)
            self.collection = self.chroma_client.create_collection(
                name=settings.CHROMA_COLLECTION_NAME
            )
            self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
            self.storage_context = StorageContext.from_defaults(
                vector_store=self.vector_store
            )
            self.index = VectorStoreIndex(
                [],
                storage_context=self.storage_context
            )
            return True
        except Exception as e:
            print(f"删除失败: {e}")
            return False
    
    def get_collection_info(self) -> dict:
        """获取集合信息"""
        count = self.collection.count()
        return {
            "collection_name": settings.CHROMA_COLLECTION_NAME,
            "document_count": count,
            "persist_dir": settings.CHROMA_PERSIST_DIR
        }


# 全局向量存储管理器实例
vector_store_manager = VectorStoreManager()

