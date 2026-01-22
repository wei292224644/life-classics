"""
知识库导入API
支持上传文件并导入到知识库，以及查看知识库内容
"""

import os
import tempfile
import json
import time
import uuid
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

from app.core.kb import import_file_step, split_step
from app.core.kb.vector_store import vector_store_manager
from app.core.kb.imports.import_markdown import import_markdown


router = APIRouter()


class UploadDocumentResponse(BaseModel):
    """导入响应模型"""

    success: bool
    message: str
    doc_id: Optional[str] = None
    chunks_count: int = 0
    file_name: str
    file_format: str
    strategy: str


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(
    file: UploadFile = File(..., description="要导入的文件"),
    strategy: str = Form(
        "text", description="切分策略（text、table、heading、structured、parent_child）"
    ),
    chunk_size: Optional[int] = Form(
        None, description="切分大小（仅对 text 策略有效）"
    ),
    chunk_overlap: Optional[int] = Form(
        None, description="切分重叠大小（仅对 text 策略有效）"
    ),
):
    """
    上传文档到知识库

    支持的文件格式：
    - PDF (.pdf)
    - Markdown (.md, .markdown)
    - JSON (.json)
    - Text (.txt)

    支持的切分策略：
    - text: 文本切分（默认）
    - table: 表格切分
    - heading: 标题切分
    - structured: 结构化切分
    - parent_child: 父子切分
    """
    # 创建临时文件保存上传的文件
    temp_file = None
    temp_file_path = None
    file_ext = None

    try:
        # 获取文件扩展名
        from pathlib import Path

        file_ext = Path(file.filename).suffix.lower()

        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            # 读取上传的文件内容
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # 调用导入函数处理业务逻辑
        try:
            documents = import_file_step(
                file_path=temp_file_path,
                strategy=strategy,
                original_filename=file.filename,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            if not documents:
                return UploadDocumentResponse(
                    success=False,
                    message="未能从文件中提取到内容",
                    file_name=file.filename or "unknown",
                    file_format=file_ext or "unknown",
                    strategy=strategy,
                )

            # 从文档列表中提取信息
            doc_id = documents[0].doc_id if documents else None
            chunks_count = len(documents)

            return UploadDocumentResponse(
                success=True,
                message=f"成功导入 {chunks_count} 个 chunks",
                doc_id=doc_id,
                chunks_count=chunks_count,
                file_name=file.filename or "unknown",
                file_format=file_ext or "unknown",
                strategy=strategy,
            )

        except ValueError as e:
            # 文件格式或策略验证失败
            raise HTTPException(status_code=400, detail=str(e))
        except NotImplementedError as e:
            # 功能尚未实现
            raise HTTPException(status_code=501, detail=str(e))
        except RuntimeError as e:
            # 运行时错误
            raise HTTPException(status_code=500, detail=str(e))

    except HTTPException:
        # 重新抛出 HTTP 异常
        raise
    except Exception as e:
        import traceback

        error_detail = traceback.format_exc()
        print(f"导入文件时出错: {error_detail}")
        return UploadDocumentResponse(
            success=False,
            message=f"导入文件时出错: {str(e)}",
            file_name=file.filename or "unknown",
            file_format=file_ext or "unknown",
            strategy=strategy,
        )

    finally:
        # 清理临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass


class ChunkResponse(BaseModel):
    """Chunk 响应模型"""

    id: str
    content: str
    metadata: Dict[str, Any]


class ChunksListResponse(BaseModel):
    """Chunks 列表响应模型"""

    chunks: List[ChunkResponse]
    total: Optional[int] = None
    limit: Optional[int] = None
    offset: int = 0


@router.get("/chunks", response_model=ChunksListResponse)
async def get_chunks(
    limit: Optional[int] = Query(None, description="返回的最大文档数量", ge=1, le=1000),
    offset: int = Query(0, description="跳过的文档数量", ge=0),
    doc_id: Optional[str] = Query(None, description="按文档 ID 过滤"),
    content_type: Optional[str] = Query(None, description="按内容类型过滤"),
):
    """
    获取知识库中的所有 chunks（支持分页和过滤）
    """
    try:
        # 构建过滤条件
        where = {}
        if doc_id:
            where["doc_id"] = doc_id
        if content_type:
            where["content_type"] = content_type

        # 获取文档（ids 是默认返回的，不需要在 include 中指定）
        include = ["documents", "metadatas"]
        # 如果 where 为空，传递 None；否则传递 where 字典
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

        # 还原复杂的 metadata
        chunks = []
        for i, chunk_id in enumerate(ids):
            metadata = metadatas[i] if i < len(metadatas) else {}
            # 尝试还原 JSON 字符串的 metadata
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

            # 额外的客户端过滤：如果指定了 doc_id，确保 metadata 中的 doc_id 匹配
            # 这是为了防止 ChromaDB 的 where 过滤在某些情况下不生效
            if doc_id and restored_metadata.get("doc_id") != doc_id:
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
                # 如果指定了 doc_id，还需要在客户端再次过滤以确保准确性
                if doc_id:
                    filtered_ids = []
                    filtered_metadatas = count_results.get("metadatas", []) or []
                    filtered_ids_list = count_results.get("ids", []) or []
                    for j, meta in enumerate(filtered_metadatas):
                        if j < len(filtered_ids_list) and meta.get("doc_id") == doc_id:
                            filtered_ids.append(filtered_ids_list[j])
                    total = len(filtered_ids)
                else:
                    total = len(count_results.get("ids", []))
            except:
                pass

        return ChunksListResponse(
            chunks=chunks,
            total=total,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 chunks 失败: {str(e)}")


@router.get("/chunks/info")
async def get_chunks_info():
    """
    获取知识库统计信息
    """
    try:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库信息失败: {str(e)}")


class DocumentInfo(BaseModel):
    """文档信息模型"""

    doc_id: str
    doc_title: str
    chunks_count: int
    content_types: Dict[str, int]
    source: Optional[str] = None
    has_markdown_cache: Optional[bool] = False


class DocumentsListResponse(BaseModel):
    """文档列表响应模型"""

    documents: List[DocumentInfo]
    total: int


@router.get("/documents", response_model=DocumentsListResponse)
async def get_documents():
    """
    获取所有文档列表及其统计信息
    """
    from pathlib import Path

    try:
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
                # 检查是否有 markdown_cache
                markdown_path = Path(f"./markdown_cache/{doc_id}.md")
                has_markdown_cache = markdown_path.exists()

                doc_stats[doc_id] = {
                    "doc_id": doc_id,
                    "doc_title": doc_title,
                    "chunks_count": 0,
                    "content_types": {},
                    "source": source_str,
                    "has_markdown_cache": has_markdown_cache,
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
                has_markdown_cache=info.get("has_markdown_cache", False),
            )
            for info in doc_stats.values()
        ]

        # 按文档 ID 排序
        documents.sort(key=lambda x: x.doc_id)

        return DocumentsListResponse(documents=documents, total=len(documents))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    删除指定文档及其所有 chunks
    """
    try:
        success = vector_store_manager.delete_by_doc_id(doc_id)
        if success:
            return {
                "status": "success",
                "message": f"文档 {doc_id} 及其所有 chunks 已删除",
            }
        else:
            raise HTTPException(status_code=500, detail="删除失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.delete("/clear")
async def clear_all():
    """
    清空所有文档和 chunks
    """
    try:
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

        # 清空所有数据
        success = vector_store_manager.clear_all()

        if success:
            return {
                "status": "success",
                "message": f"已清空所有数据，共删除 {total_docs} 个文档，{total_chunks} 个 chunks",
                "deleted_documents": total_docs,
                "deleted_chunks": total_chunks,
            }
        else:
            raise HTTPException(status_code=500, detail="清空数据失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空数据失败: {str(e)}")


@router.get("/documents/{doc_id}/markdown/check")
async def check_markdown_cache(doc_id: str):
    """
    检查文档是否有 markdown_cache
    """
    from pathlib import Path

    markdown_path = Path(f"./markdown_cache/{doc_id}.md")
    exists = markdown_path.exists()

    return {
        "status": "success",
        "doc_id": doc_id,
        "exists": exists,
    }


@router.get("/documents/{doc_id}/markdown")
async def get_markdown_cache(doc_id: str):
    """
    获取文档的 markdown_cache 内容（如果存在）
    """
    from pathlib import Path

    markdown_path = Path(f"./markdown_cache/{doc_id}.md")

    if not markdown_path.exists():
        raise HTTPException(
            status_code=404, detail=f"文档 {doc_id} 的 markdown_cache 不存在"
        )

    try:
        with open(markdown_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {
            "status": "success",
            "doc_id": doc_id,
            "content": content,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"读取 markdown_cache 失败: {str(e)}"
        )


@router.put("/documents/{doc_id}/markdown")
async def update_markdown_cache(doc_id: str, content: str = Form(...)):
    """
    更新文档的 markdown_cache 内容
    """
    from pathlib import Path

    markdown_path = Path(f"./markdown_cache/{doc_id}.md")

    # 确保目录存在
    markdown_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(markdown_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "success",
            "message": f"markdown_cache 已更新",
            "doc_id": doc_id,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"更新 markdown_cache 失败: {str(e)}"
        )


@router.post("/documents/{doc_id}/reprocess")
async def reprocess_document(doc_id: str, strategy: str = Form("structured")):
    """
    重新处理文档：删除现有 chunks，从 markdown_cache 重新导入

    流程：
    1. 删除该文档的所有 chunks
    2. 从 markdown_cache 读取 md 文件
    3. 重新执行后续流程（split + vector store）
    """
    from pathlib import Path

    # 检查 markdown_cache 是否存在
    markdown_path = Path(f"./markdown_cache/{doc_id}.md")
    if not markdown_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"文档 {doc_id} 的 markdown_cache 不存在，无法重新处理",
        )

    try:
        # 1. 删除该文档的所有 chunks
        success = vector_store_manager.delete_by_doc_id(doc_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除现有 chunks 失败")

        # 2. 从 markdown_cache 重新导入
        documents = import_markdown(
            str(markdown_path), original_filename=f"{doc_id}.md"
        )

        if not documents:
            raise HTTPException(status_code=500, detail="从 markdown_cache 导入失败")

        # 3. 执行后续流程（split + vector store）
        documents = split_step(documents, strategy)
        vector_store_manager.add_chunks(documents)

        return {
            "status": "success",
            "message": f"文档 {doc_id} 已重新处理",
            "doc_id": doc_id,
            "chunks_count": len(documents),
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        error_detail = traceback.format_exc()
        print(f"重新处理文档时出错: {error_detail}")
        raise HTTPException(status_code=500, detail=f"重新处理文档失败: {str(e)}")


class SearchRequest(BaseModel):
    """搜索请求模型"""

    query: str
    top_k: int = 10
    use_rerank: bool = False
    retrieve_k: Optional[int] = None


class SearchResult(BaseModel):
    """搜索结果模型"""

    id: str
    content: str
    metadata: Dict[str, Any]
    relevance_score: Optional[float] = None
    relevance_reason: Optional[str] = None


class SearchResponse(BaseModel):
    """搜索响应模型"""

    results: List[SearchResult]
    total: int
    query: str


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    搜索知识库中的文档

    支持两种模式：
    1. 普通搜索：直接使用向量相似度搜索
    2. 重排序搜索：先检索更多结果，然后使用 LLM 进行重排序
    """
    try:
        if request.use_rerank:
            # 使用重排序搜索
            retrieve_k = request.retrieve_k or max(request.top_k * 2, 20)
            reranked_chunks = vector_store_manager.search_with_rerank(
                query=request.query,
                top_k=request.top_k,
                retrieve_k=retrieve_k,
                use_llm=True,
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
                query=request.query,
                top_k=request.top_k,
            )

            results = [
                SearchResult(
                    id=doc.metadata.get("chunk_id", ""),
                    content=doc.page_content,
                    metadata=doc.metadata,
                )
                for doc in documents
            ]

        return SearchResponse(
            results=results,
            total=len(results),
            query=request.query,
        )
    except ConnectionError as e:
        # Ollama 或其他服务连接错误
        error_msg = str(e)
        if "Ollama" in error_msg or "ollama" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="无法连接到 Ollama 服务。请确保 Ollama 已安装并正在运行。访问 https://ollama.com/download 下载 Ollama。",
            )
        else:
            raise HTTPException(status_code=503, detail=f"服务连接失败: {error_msg}")
    except Exception as e:
        import traceback

        error_detail = traceback.format_exc()
        print(f"搜索失败: {error_detail}")

        # 提供更友好的错误信息
        error_msg = str(e)
        if "ConnectionError" in error_msg or "连接" in error_msg:
            raise HTTPException(status_code=503, detail=f"服务连接失败: {error_msg}")
        else:
            raise HTTPException(status_code=500, detail=f"搜索失败: {error_msg}")


class ChatRequest(BaseModel):
    """对话请求模型"""

    message: str
    top_k: int = 5
    use_rerank: bool = True
    conversation_history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    """对话响应模型"""

    response: str
    sources: Optional[List[SearchResult]] = None


async def _prepare_chat_context(request: ChatRequest):
    """准备对话上下文（检索文档和构建消息）"""
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    # 1. 从知识库检索相关文档
    if request.use_rerank:
        # 使用重排序搜索
        retrieve_k = max(request.top_k * 2, 20)
        reranked_chunks = vector_store_manager.search_with_rerank(
            query=request.message,
            top_k=request.top_k,
            retrieve_k=retrieve_k,
            use_llm=True,
        )

        retrieved_docs = [chunk.document for chunk in reranked_chunks]
        sources = [
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
        retrieved_docs = vector_store_manager.search(
            query=request.message,
            top_k=request.top_k,
        )

        sources = [
            SearchResult(
                id=doc.metadata.get("chunk_id", ""),
                content=doc.page_content,
                metadata=doc.metadata,
            )
            for doc in retrieved_docs
        ]

    # 2. 构建上下文
    context_parts = []
    for i, doc in enumerate(retrieved_docs, 1):
        metadata = doc.metadata or {}
        doc_title = metadata.get("doc_title", metadata.get("doc_id", "未知文档"))
        section_path = metadata.get("section_path", [])
        section_path_str = " > ".join(section_path) if section_path else ""

        context_part = f"[文档 {i}]"
        if doc_title:
            context_part += f" 来源: {doc_title}"
        if section_path_str:
            context_part += f" ({section_path_str})"
        context_part += f"\n内容: {doc.page_content}\n"
        context_parts.append(context_part)

    context = "\n".join(context_parts)

    # 3. 构建消息列表
    messages = []

    # 系统提示
    system_prompt = """你是一个专业的知识库助手。你的任务是基于提供的知识库内容回答用户的问题。

重要规则：
1. 只基于提供的知识库内容回答问题，不要编造信息
2. 如果知识库中没有相关信息，明确告诉用户
3. 回答要准确、简洁、有条理
4. 可以引用具体的文档来源
5. 如果用户的问题与知识库内容无关，礼貌地说明你的职责范围

知识库内容：
{context}"""

    messages.append(SystemMessage(content=system_prompt.format(context=context)))

    # 对话历史
    if request.conversation_history:
        for msg in request.conversation_history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

    # 当前用户消息
    messages.append(HumanMessage(content=request.message))

    return messages, sources


@router.post("/chat", response_model=ChatResponse)
async def chat_with_knowledge_base(request: ChatRequest):
    """
    基于知识库的对话接口（RAG）- 非流式版本（保留用于兼容）

    流程：
    1. 从知识库检索相关文档
    2. 将检索到的文档作为上下文
    3. 使用 LLM 基于上下文生成回复
    """
    try:
        messages, sources = await _prepare_chat_context(request)

        # 4. 调用 LLM 生成回复
        from app.core.llm import chat as llm_chat

        response = llm_chat(
            messages=messages,
            provider_name="dashscope",
            provider_config={
                "model": "qwen3-max-preview",
                "temperature": 0.4,
                "reasoning": True,
            },
        )

        return ChatResponse(
            response=response,
            sources=sources,
        )

    except ConnectionError as e:
        error_msg = str(e)
        if "Ollama" in error_msg or "ollama" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="无法连接到 Ollama 服务。请确保 Ollama 已安装并正在运行。访问 https://ollama.com/download 下载 Ollama。",
            )
        else:
            raise HTTPException(
                status_code=503,
                detail=f"服务连接失败: {error_msg}",
            )
    except Exception as e:
        import traceback

        error_detail = traceback.format_exc()
        print(f"对话失败: {error_detail}")

        error_msg = str(e)
        if "ConnectionError" in error_msg or "连接" in error_msg:
            raise HTTPException(
                status_code=503,
                detail=f"服务连接失败: {error_msg}",
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"对话失败: {error_msg}",
            )


# 临时存储会话数据（生产环境应使用 Redis 等）
_chat_sessions = {}


@router.post("/chat/stream/start")
async def start_chat_stream(request: ChatRequest):
    """
    启动流式对话会话
    返回会话 ID，用于后续的 EventSource 连接
    """
    session_id = str(uuid.uuid4())
    _chat_sessions[session_id] = {
        "request": request,
        "created_at": time.time(),
    }
    return {"session_id": session_id}


@router.get("/chat/stream/{session_id}")
async def chat_with_knowledge_base_stream(session_id: str):
    """
    基于知识库的流式对话接口（RAG Stream）
    
    使用 Server-Sent Events (SSE) 流式返回回复
    支持 EventSource 连接（GET 请求）
    """
    # 获取会话数据
    if session_id not in _chat_sessions:
        async def error_generate():
            error_data = json.dumps({'type': 'error', 'data': '会话不存在或已过期'}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
        return StreamingResponse(
            error_generate(),
            media_type="text/event-stream",
        )
    
    request = _chat_sessions[session_id]["request"]
    
    # 清理会话（使用后删除）
    del _chat_sessions[session_id]
    
    async def generate():
        try:
            messages, sources = await _prepare_chat_context(request)

            # 先发送来源信息
            sources_data = json.dumps([source.dict() for source in sources], ensure_ascii=False)
            yield f"data: {json.dumps({'type': 'sources', 'data': sources_data}, ensure_ascii=False)}\n\n"

            # 调用流式 LLM 生成回复
            from app.core.llm import chat_stream

            full_response = ""
            async for chunk in chat_stream(
                messages=messages,
                provider_name="dashscope",
                provider_config={
                    "model": "qwen3-max-preview",
                    "temperature": 0.4,
                    "reasoning": True,
                },
            ):
                if chunk:
                    full_response += chunk
                    # 发送文本块
                    yield f"data: {json.dumps({'type': 'chunk', 'data': chunk}, ensure_ascii=False)}\n\n"

            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'data': full_response}, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"流式对话失败: {error_detail}")
            
            error_msg = str(e)
            error_data = json.dumps({'type': 'error', 'data': error_msg}, ensure_ascii=False)
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )
