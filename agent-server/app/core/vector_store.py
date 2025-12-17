"""
向量存储管理 - 基于ChromaDB (LangChain版本)
"""

import os
import uuid
from typing import List, Optional, Dict, Any
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings
from app.core.embeddings import get_embedding_model
from app.core.parent_store import ParentChunkStore


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

        # 父 chunk 存储（SQLite）
        self.parent_store = ParentChunkStore(
            db_path=os.path.join(settings.CHROMA_PERSIST_DIR, "parent_chunks.sqlite3")
        )

    def add_documents(self, documents: List[Document]):
        """
        添加文档到向量存储
        
        如果启用父子chunk模式：
        - 父 chunk 写入 SQLite（parent_store）
        - 子 chunk 写入 Chroma（向量检索）
        """
        if settings.ENABLE_PARENT_CHILD:
            self._add_documents_parent_child(documents)
        else:
            # 普通模式：直接添加文档
            self.vector_store.add_documents(documents)

    def _add_documents_parent_child(self, raw_documents: List[Document]) -> None:
        """
        父子 chunk 入库策略：
        - parent: 仅保存到 SQLite（避免向量库重复存大段文本）
        - child: 保存到 Chroma（用于向量检索）
        """
        parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.PARENT_CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHILD_CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )

        parent_docs = parent_splitter.split_documents(raw_documents)

        child_docs_to_add: List[Document] = []
        child_ids: List[str] = []

        for parent_idx, parent_doc in enumerate(parent_docs):
            parent_id = str(uuid.uuid4())

            parent_metadata: Dict[str, Any] = dict(parent_doc.metadata or {})
            parent_metadata.update(
                {
                    "chunk_type": "parent",
                    "split_strategy": "parent_child",
                    "parent_id": parent_id,
                    "parent_index": parent_idx,
                }
            )

            # 写父 chunk 到 SQLite
            self.parent_store.upsert_parent(
                parent_id=parent_id,
                text=parent_doc.page_content or "",
                metadata=parent_metadata,
            )

            # 为父 chunk 创建子 chunk（只将子 chunk 写入向量库）
            child_docs = child_splitter.split_documents([parent_doc])
            for child_idx, child_doc in enumerate(child_docs):
                child_metadata: Dict[str, Any] = dict(child_doc.metadata or {})
                child_metadata.update(
                    {
                        "chunk_type": "child",
                        "split_strategy": "parent_child",
                        "parent_id": parent_id,
                        "child_index": child_idx,
                    }
                )
                child_doc.metadata = child_metadata

                child_id = f"{parent_id}:{child_idx}"
                child_ids.append(child_id)
                child_docs_to_add.append(child_doc)

        if child_docs_to_add:
            # 显式传入 ids，保证稳定可追溯
            self.vector_store.add_documents(child_docs_to_add, ids=child_ids)

    def query(self, query_str: str, top_k: int = 5) -> List[Document]:
        """
        查询相似文档
        
        如果启用父子chunk模式，优先返回父chunk
        """
        if settings.ENABLE_PARENT_CHILD:
            # 只检索子 chunk，然后回溯父 chunk（父 chunk 不入向量库）
            results = self.vector_store.similarity_search_with_score(
                query_str, k=top_k * 4
            )

            # parent_id -> best_score / matched_children
            parent_best: Dict[str, float] = {}
            parent_children: Dict[str, List[Document]] = {}

            for doc, score in results:
                parent_id = (doc.metadata or {}).get("parent_id")
                if not parent_id:
                    continue
                if parent_id not in parent_best or score > parent_best[parent_id]:
                    parent_best[parent_id] = score
                parent_children.setdefault(parent_id, []).append(doc)

            # 按 best_score 取 top_k 个 parent
            sorted_parent_ids = sorted(
                parent_best.keys(), key=lambda pid: parent_best[pid], reverse=True
            )[:top_k]

            parent_docs: List[Document] = []
            for pid in sorted_parent_ids:
                parent = self.parent_store.get_parent(pid)
                if not parent:
                    continue
                md = dict(parent.get("metadata") or {})
                # 附带一小段命中的子 chunk 片段，便于调试/展示
                matched = parent_children.get(pid, [])[:3]
                md["matched_children_preview"] = [
                    (c.page_content or "")[:200] for c in matched
                ]
                parent_docs.append(
                    Document(page_content=parent.get("text") or "", metadata=md)
                )
            return parent_docs
        else:
            # 使用相似度搜索
            results = self.vector_store.similarity_search_with_score(
                query_str, k=top_k
            )
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
        # 同时清空父 chunk 存储
        try:
            self.parent_store.clear()
        except Exception:
            pass
        return True

    def get_collection_info(self) -> dict:
        """获取集合信息"""
        count = self.vector_store._collection.count()
        info = {
            "collection_name": settings.CHROMA_COLLECTION_NAME,
            "document_count": count,
            "persist_dir": settings.CHROMA_PERSIST_DIR,
        }
        if settings.ENABLE_PARENT_CHILD:
            try:
                info["parent_count"] = self.parent_store.count()
            except Exception:
                info["parent_count"] = None
        return info

    def get_all_documents(self) -> List[dict]:
        """
        获取所有文档块
        
        Returns:
            文档块列表，每个块包含文本和元数据
        """
        # 从ChromaDB获取所有数据（父子模式下只存子 chunk）
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

    def list_chunks_page(
        self,
        limit: int = 20,
        offset: int = 0,
        where: Optional[Dict] = None,
        where_document: Optional[Dict] = None,
    ) -> Dict[str, any]:
        """
        分页获取 chunk 列表（尽量走 Chroma 原生过滤）。

        Args:
            limit: 每页条数
            offset: 偏移量
            where: metadata 过滤条件（Chroma where）
            where_document: 文本过滤条件（Chroma where_document，例如 {"$contains": "foo"}）
        """
        include = ["documents", "metadatas"]
        # Chroma collection.get 支持 limit/offset/where/where_document（不同版本兼容性略有差异）
        try:
            results = self.vector_store._collection.get(
                include=include,
                limit=limit,
                offset=offset,
                where=where,
                where_document=where_document,
            )
        except TypeError:
            # 兼容旧版本：没有 where_document 或 offset 参数
            results = self.vector_store._collection.get(
                include=include,
                where=where,
            )
            # 手动分页（退化方案）
            ids = results.get("ids", []) or []
            documents_data = results.get("documents", []) or []
            metadatas = results.get("metadatas", []) or []
            ids = ids[offset : offset + limit]
            documents_data = documents_data[offset : offset + limit]
            metadatas = metadatas[offset : offset + limit]
            results = {"ids": ids, "documents": documents_data, "metadatas": metadatas}

        ids = results.get("ids", []) or []
        documents_data = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []

        chunks = []
        for i, doc_id in enumerate(ids):
            chunks.append(
                {
                    "id": doc_id,
                    "text": documents_data[i] if i < len(documents_data) else "",
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                }
            )

        # total: 仅在无过滤时可靠（count 不支持 where）；过滤时用 None 表示未知
        total = None
        if not where and not where_document:
            try:
                total = self.vector_store._collection.count()
            except Exception:
                total = None

        return {"chunks": chunks, "total": total}

    def get_chunk_by_id(self, chunk_id: str) -> Dict[str, any]:
        """根据 chunk id 获取详情"""
        results = self.vector_store._collection.get(
            ids=[chunk_id],
            include=["documents", "metadatas"],
        )
        ids = results.get("ids", []) or []
        if not ids:
            return {"id": chunk_id, "text": "", "metadata": {}, "found": False}
        doc = (results.get("documents") or [""])[0]
        md = (results.get("metadatas") or [{}])[0]
        return {"id": ids[0], "text": doc or "", "metadata": md or {}, "found": True}

    def delete_chunk_by_id(self, chunk_id: str) -> bool:
        """删除单个 chunk（按 id）"""
        # Chroma collection.delete 支持 ids 参数
        self.vector_store._collection.delete(ids=[chunk_id])
        return True

    def delete_parent_by_id(self, parent_id: str) -> bool:
        """删除父 chunk：同时删除该父下所有子 chunk + SQLite 记录"""
        # 删除子 chunk（where）
        try:
            self.vector_store._collection.delete(where={"parent_id": parent_id})
        except Exception:
            # 兼容性兜底：如果 where delete 不支持，退化为 get 后按 ids delete
            results = self.vector_store._collection.get(
                where={"parent_id": parent_id},
                include=[],
            )
            ids = results.get("ids", []) or []
            if ids:
                self.vector_store._collection.delete(ids=ids)
        # 删除父 chunk 记录
        self.parent_store.delete_parent(parent_id)
        return True

    def list_parents_page(
        self,
        limit: int = 20,
        offset: int = 0,
        file_name: str = "",
        q: str = "",
    ) -> Dict[str, Any]:
        """分页列出父 chunk（SQLite）"""
        items, total = self.parent_store.list_parents(
            limit=limit, offset=offset, file_name=file_name, q=q
        )
        return {"parents": items, "total": total}

    def get_parent_by_id(self, parent_id: str) -> Dict[str, Any]:
        """获取父 chunk（SQLite）"""
        parent = self.parent_store.get_parent(parent_id)
        if not parent:
            return {"parent_id": parent_id, "text": "", "metadata": {}, "found": False}
        return {**parent, "found": True}

    def list_children_by_parent_id(self, parent_id: str) -> List[Dict[str, Any]]:
        """获取某个父 chunk 的所有子 chunk（从 Chroma where 过滤）"""
        results = self.vector_store._collection.get(
            where={"parent_id": parent_id},
            include=["documents", "metadatas"],
        )
        ids = results.get("ids", []) or []
        documents_data = results.get("documents", []) or []
        metadatas = results.get("metadatas", []) or []

        children: List[Dict[str, Any]] = []
        for i, doc_id in enumerate(ids):
            md = metadatas[i] if i < len(metadatas) else {}
            children.append(
                {
                    "id": doc_id,
                    "text": documents_data[i] if i < len(documents_data) else "",
                    "metadata": md,
                    "child_index": (md or {}).get("child_index", i),
                }
            )
        children.sort(key=lambda x: (x.get("child_index") is None, x.get("child_index", 0)))
        return children

    def clear_collection(self) -> bool:
        """清空整个 collection（等价于 delete_all）"""
        return bool(self.delete_all())

    def get_retriever(self, top_k: int = 5):
        """获取检索器"""
        return self.vector_store.as_retriever(
            search_kwargs={"k": top_k}
        )


# 全局向量存储管理器实例
vector_store_manager = VectorStoreManager()
