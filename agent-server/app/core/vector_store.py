"""
向量存储管理 - 基于ChromaDB (LangChain版本)
"""

import os
import uuid
import re
import time
from typing import List, Optional, Dict, Any
from langchain_chroma import Chroma
from langchain_core.documents import Document
from app.core.config import settings
from app.core.embeddings import get_embedding_model
from app.core.parent_store import ParentChunkStore
from app.core.document_loader import document_loader


class VectorStoreManager:
    """向量存储管理器"""

    # ==================== 初始化方法 ====================

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

    # ==================== 内部函数（私有方法） ====================

    def _clean_text(self, text: str) -> str:
        """
        清理文本：替换连续的空格、换行符和制表符
        - 连续的空格 -> 单个空格
        - 连续的换行符 -> 单个换行符
        - 连续的制表符 -> 单个空格
        """
        # 替换连续的制表符为单个空格
        text = re.sub(r'\t+', ' ', text)
        # 替换连续的空格为单个空格
        text = re.sub(r' +', ' ', text)
        # 替换连续的换行符为单个换行符（保留换行符，因为用于切分）
        text = re.sub(r'\n+', '\n', text)
        # 去除首尾空白字符
        return text.strip()

    def _split_parent_chunks(self, text: str) -> List[str]:
        """
        按照dify设计切分父层级chunk
        - 按照段落（PARENT_SEPARATOR，默认\n\n）分割
        - 每个chunk最大长度为PARENT_CHUNK_SIZE（默认1024）
        """
        # 先按照父层级分隔符分割段落（在清理之前，保留分隔符）
        paragraphs = text.split(settings.PARENT_SEPARATOR)
        
        parent_chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # 清理段落文本
            paragraph = self._clean_text(paragraph)
            if not paragraph:
                continue
            
            # 如果当前chunk加上新段落不超过最大长度，则合并
            if not current_chunk:
                current_chunk = paragraph
            elif len(current_chunk) + len(settings.PARENT_SEPARATOR) + len(paragraph) <= settings.PARENT_CHUNK_SIZE:
                current_chunk += settings.PARENT_SEPARATOR + paragraph
            else:
                # 保存当前chunk，开始新chunk
                if current_chunk:
                    parent_chunks.append(current_chunk)
                current_chunk = paragraph
                
                # 如果单个段落就超过最大长度，需要强制分割
                if len(paragraph) > settings.PARENT_CHUNK_SIZE:
                    # 按字符强制分割
                    while len(paragraph) > settings.PARENT_CHUNK_SIZE:
                        parent_chunks.append(paragraph[:settings.PARENT_CHUNK_SIZE])
                        paragraph = paragraph[settings.PARENT_CHUNK_SIZE:]
                    current_chunk = paragraph
        
        # 保存最后一个chunk
        if current_chunk:
            parent_chunks.append(current_chunk)
        
        return parent_chunks

    def _add_documents_parent_child(self, raw_documents: List[Document]) -> None:
        """
        父子 chunk 入库策略（Dify风格）：
        - parent: 仅保存到 SQLite（避免向量库重复存大段文本）
        - child: 保存到 Chroma（用于向量检索）
        - 按照段落（\n\n）切分父层级，最大长度1024
        - 按照行（\n）切分子块，最大长度512
        - 清理连续的空格、换行符和制表符
        """
        child_docs_to_add: List[Document] = []
        child_ids: List[str] = []

        # 处理每个原始文档
        for doc in raw_documents:
            text = doc.page_content or ""
            
            # 切分父chunk
            parent_texts = self._split_parent_chunks(text)
            
            for parent_idx, parent_text in enumerate(parent_texts):
                parent_id = str(uuid.uuid4())

                parent_metadata: Dict[str, Any] = dict(doc.metadata or {})
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
                    text=parent_text,
                    metadata=parent_metadata,
                )

                # 为父 chunk 创建子 chunk（只将子 chunk 写入向量库）
                child_docs = document_loader.split_child_chunks_for_parent(
                    parent_text, doc.metadata, parent_idx
                )
                for child_idx, child_doc in enumerate(child_docs):
                    child_metadata: Dict[str, Any] = dict(child_doc.metadata or {})
                    child_metadata.update(
                        {
                            "chunk_type": "child",
                            "split_strategy": document_loader.split_strategy,
                            "parent_id": parent_id,
                            "parent_index": parent_idx,
                            "child_index": child_idx,
                        }
                    )
                    child_doc.metadata = child_metadata

                    child_id = f"{parent_id}:{child_idx}"
                    child_ids.append(child_id)
                    child_docs_to_add.append(child_doc)

        if child_docs_to_add:
            # 批量添加子chunk，添加重试机制和分批处理
            self._add_documents_with_retry(child_docs_to_add, child_ids)
    
    def _add_documents_with_retry(
        self, 
        documents: List[Document], 
        ids: List[str],
        batch_size: int = 50,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        带重试机制和分批处理的文档添加方法
        
        Args:
            documents: 要添加的文档列表
            ids: 文档ID列表
            batch_size: 每批处理的文档数量
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        total = len(documents)
        if total == 0:
            return
        
        print(f"  开始批量添加 {total} 个文档（每批 {batch_size} 个）...")
        
        # 分批处理
        for batch_start in range(0, total, batch_size):
            batch_end = min(batch_start + batch_size, total)
            batch_docs = documents[batch_start:batch_end]
            batch_ids = ids[batch_start:batch_end]
            
            # 重试机制
            for attempt in range(max_retries):
                try:
                    self.vector_store.add_documents(batch_docs, ids=batch_ids)
                    print(f"  ✓ 成功添加批次 {batch_start//batch_size + 1} ({batch_start+1}-{batch_end}/{total})")
                    break
                except Exception as e:
                    error_msg = str(e)
                    is_connection_error = any(keyword in error_msg.lower() for keyword in [
                        'disconnected', 'connection', 'timeout', 'remote', 'protocol'
                    ])
                    
                    if attempt < max_retries - 1:
                        wait_time = retry_delay * (attempt + 1)
                        print(f"  ⚠ 批次 {batch_start//batch_size + 1} 添加失败 (尝试 {attempt + 1}/{max_retries}): {error_msg[:100]}")
                        print(f"  ⏳ {wait_time}秒后重试...")
                        time.sleep(wait_time)
                    else:
                        print(f"  ✗ 批次 {batch_start//batch_size + 1} 添加失败，已重试 {max_retries} 次: {error_msg}")
                        # 如果是连接错误，建议检查Ollama服务
                        if is_connection_error:
                            print(f"  💡 提示: 可能是Ollama服务连接问题，请检查:")
                            print(f"     - Ollama服务是否运行: curl {settings.OLLAMA_BASE_URL}/api/tags")
                            print(f"     - 网络连接是否正常")
                            print(f"     - 是否处理了太多文档，可以减小batch_size")
                        raise

    # ==================== 公开函数（核心业务逻辑） ====================

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
            # 普通模式：使用带重试的批量添加
            try:
                self._add_documents_with_retry(documents, [str(uuid.uuid4()) for _ in documents])
            except Exception:
                # 如果批量添加失败，回退到直接添加（兼容性）
                print("  ⚠ 批量添加失败，尝试直接添加...")
            self.vector_store.add_documents(documents)

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
                matched = parent_children.get(pid, [])[:3]
                md["matched_children_preview"] = [
                    (c.page_content or "")[:200] for c in matched
                ]
                parent_text = self.assemble_parent_text_from_children(pid)
                parent_docs.append(
                    Document(page_content=parent_text, metadata=md)
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

    def delete_parents_by_file(self, file_name: str) -> bool:
        """删除某个文件对应的父和子 chunk"""
        if not file_name:
            return False
        parent_ids = self.parent_store.delete_parents_by_file_name(file_name)
        if parent_ids:
            try:
                self.vector_store._collection.delete(where={"parent_id": {"$in": parent_ids}})
            except Exception:
                # 兼容老版本：逐个删除
                for pid in parent_ids:
                    self.vector_store._collection.delete(where={"parent_id": pid})
        return True

    def file_exists(self, file_name: str) -> bool:
        """检查文件是否已经在知识库中"""
        if not settings.ENABLE_PARENT_CHILD:
            # 非父子模式：检查 ChromaDB 中是否有该文件的文档
            try:
                results = self.vector_store._collection.get(
                    where={"file_name": file_name},
                    limit=1,
                )
                return len(results.get("ids", [])) > 0
            except Exception:
                return False
        else:
            # 父子模式：检查 SQLite 中是否有该文件的父 chunk
            parent_ids = self.parent_store.list_parent_ids_by_file(file_name)
            return len(parent_ids) > 0

    def assemble_parent_text_from_children(self, parent_id: str) -> str:
        """根据子 chunk 拼接父 chunk 的文本内容"""
        children = self.list_children_by_parent_id(parent_id)
        texts = []
        for child in children:
            text = (child.get("text") or "").strip()
            if text:
                texts.append(text)
        if texts:
            return "\n".join(texts)
        parent = self.parent_store.get_parent(parent_id)
        if parent:
            return parent.get("text") or ""
        return ""

    def update_child_chunk_text(self, chunk_id: str, new_text: str) -> bool:
        """更新指定子 chunk 的文本内容"""
        if not settings.ENABLE_PARENT_CHILD:
            return False
        # 获取当前 chunk metadata
        try:
            existing = self.vector_store._collection.get(
                ids=[chunk_id], include=["documents", "metadatas"]
            )
        except Exception:
            return False
        ids = existing.get("ids") or []
        if not ids:
            return False
        metadatas = existing.get("metadatas") or [{}]
        metadata = metadatas[0] if metadatas else {}
        metadata = metadata or {}
        doc = Document(page_content=new_text or "", metadata=metadata)
        self.vector_store.add_documents([doc], ids=[chunk_id])
        return True

    def add_child_chunk(self, parent_id: str, text: str) -> Optional[str]:
        """为指定父 chunk 添加一个新的子 chunk"""
        if not settings.ENABLE_PARENT_CHILD:
            return None

        parent = self.parent_store.get_parent(parent_id)
        if not parent:
            return None

        children = self.list_children_by_parent_id(parent_id)
        max_index = -1
        for child in children:
            idx = child.get("child_index")
            if isinstance(idx, int):
                max_index = max(max_index, idx)
            else:
                try:
                    max_index = max(max_index, int(idx))
                except (TypeError, ValueError):
                    continue

        new_index = max_index + 1

        metadata: Dict[str, Any] = dict(parent.get("metadata") or {})
        metadata.update(
            {
                "chunk_type": "child",
                "split_strategy": document_loader.split_strategy,
                "parent_id": parent_id,
                "parent_index": metadata.get("parent_index"),
                "child_index": new_index,
            }
        )

        child_id = f"{parent_id}:{new_index}"
        child_doc = Document(page_content=text or "", metadata=metadata)
        self.vector_store.add_documents([child_doc], ids=[child_id])
        return child_id

    def clear_collection(self) -> bool:
        """清空整个 collection（等价于 delete_all）"""
        return bool(self.delete_all())

    def get_retriever(self, top_k: int = 5):
        """获取检索器"""
        return self.vector_store.as_retriever(
            search_kwargs={"k": top_k}
        )

    # ==================== WebAPI 性质的函数（返回字典，用于API响应） ====================

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
        for item in items:
            item["assembled_text"] = self.assemble_parent_text_from_children(
                item["parent_id"]
            )
        return {"parents": items, "total": total}

    def list_parent_files(self) -> List[Dict[str, Any]]:
        """返回按文件聚合的父 chunk 汇总信息"""
        if not settings.ENABLE_PARENT_CHILD:
            return []
        return self.parent_store.list_file_groups()

    def list_parent_files_page(
        self,
        limit: int = 20,
        offset: int = 0,
        search: str = "",
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> Dict[str, Any]:
        """返回按文件聚合的父 chunk 汇总信息（分页版本，支持搜索和排序）"""
        if not settings.ENABLE_PARENT_CHILD:
            return {"files": [], "total": 0}
        files, total = self.parent_store.list_file_groups_page(
            limit=limit,
            offset=offset,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return {"files": files, "total": total}

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


# 全局向量存储管理器实例
vector_store_manager = VectorStoreManager()
