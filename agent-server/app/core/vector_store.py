"""
向量存储管理 - 基于ChromaDB
"""
import os
from typing import List, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import VectorStoreIndex, StorageContext, Settings as LlamaIndexSettings
from llama_index.core.schema import Document, NodeWithScore
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
        """
        添加文档到向量存储
        
        如果启用父子chunk模式，需要将文档转换为节点并建立父子关系
        AutoMergingRetriever需要节点之间的父子关系信息
        """
        if not self.index:
            self._load_index()
        
        if settings.ENABLE_PARENT_CHILD:
            # 使用HierarchicalNodeParser重新解析文档以建立父子关系
            from llama_index.core.node_parser import HierarchicalNodeParser
            
            # 创建HierarchicalNodeParser
            hierarchical_parser = HierarchicalNodeParser.from_defaults(
                chunk_sizes=[
                    settings.PARENT_CHUNK_SIZE,
                    settings.CHILD_CHUNK_SIZE,
                ]
            )
            
            # 重新解析文档以生成带父子关系的节点
            nodes = hierarchical_parser.get_nodes_from_documents(documents)
            
            # 存储所有节点（包括父节点和子节点）
            # AutoMergingRetriever需要完整的节点图来建立父子关系
            # 但只有子节点会被用于向量检索
            for node in nodes:
                # 清理节点的metadata，避免过大
                if hasattr(node, 'metadata') and node.metadata:
                    cleaned_metadata = {}
                    for key, value in node.metadata.items():
                        # 只保留基本类型和短字符串
                        if isinstance(value, (int, float, type(None))):
                            cleaned_metadata[key] = value
                        elif isinstance(value, str):
                            # 限制字符串长度，避免metadata过大
                            if len(value) <= 200:
                                cleaned_metadata[key] = value
                            else:
                                # 对于长字符串，只保留前100个字符
                                cleaned_metadata[key] = value[:100] + "..."
                    node.metadata = cleaned_metadata
                
                # 存储节点（包括父节点和子节点，AutoMergingRetriever会处理）
                self.index.insert(node)
        else:
            # 原有逻辑：存储所有文档
            for doc in documents:
                self.index.insert(doc)
    
    def query(self, query_str: str, top_k: int = 5) -> List:
        """
        查询相似文档
        
        如果启用父子chunk模式，使用AutoMergingRetriever自动合并父节点
        """
        if not self.index:
            self._load_index()
        
        if settings.ENABLE_PARENT_CHILD:
            return self._query_with_auto_merging(query_str, top_k)
        else:
            # 原有查询逻辑
            query_engine = self.index.as_query_engine(similarity_top_k=top_k)
            response = query_engine.query(query_str)
            return response
    
    def _query_with_auto_merging(self, query_str: str, top_k: int):
        """
        使用AutoMergingRetriever进行查询
        
        AutoMergingRetriever会自动：
        1. 检索子节点
        2. 根据父子关系合并父节点
        3. 返回合并后的父节点给LLM
        """
        try:
            from llama_index.core.retrievers import AutoMergingRetriever
            from llama_index.core.retrievers import VectorIndexRetriever
            from llama_index.core.query_engine import RetrieverQueryEngine
        except ImportError:
            # 如果AutoMergingRetriever不可用，回退到普通查询
            print("警告: AutoMergingRetriever 不可用，回退到普通查询")
            query_engine = self.index.as_query_engine(similarity_top_k=top_k)
            return query_engine.query(query_str)
        
        # 创建向量检索器（用于检索子节点）
        vector_retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=top_k * 3  # 检索更多子节点以确保有足够的父节点
        )
        
        # 创建AutoMergingRetriever
        # 注意：AutoMergingRetriever 的正确参数是 vector_retriever 而不是 base_retriever
        retriever = AutoMergingRetriever(
            vector_retriever=vector_retriever,
            storage_context=self.storage_context,
            verbose=True
        )
        
        # 创建查询引擎
        query_engine = RetrieverQueryEngine.from_args(
            retriever=retriever
        )
        
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
    
    def get_all_documents(self) -> List[dict]:
        """
        获取所有文档块
        
        Returns:
            文档块列表，每个块包含文本和元数据
        """
        try:
            # 从ChromaDB集合中获取所有数据
            results = self.collection.get()
            
            documents = []
            if results and 'ids' in results:
                ids = results.get('ids', [])
                documents_data = results.get('documents', [])
                metadatas = results.get('metadatas', [])
                
                for i, doc_id in enumerate(ids):
                    doc_text = documents_data[i] if i < len(documents_data) else ""
                    doc_metadata = metadatas[i] if i < len(metadatas) else {}
                    
                    documents.append({
                        "id": doc_id,
                        "text": doc_text,
                        "metadata": doc_metadata
                    })
            
            return documents
        except Exception as e:
            print(f"获取所有文档失败: {e}")
            return []


# 全局向量存储管理器实例
vector_store_manager = VectorStoreManager()

