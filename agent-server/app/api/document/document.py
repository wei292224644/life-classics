"""
知识库导入API
支持上传文件并导入到知识库，以及查看知识库内容
"""

from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query
from fastapi.responses import StreamingResponse

from app.api.document.models import (
    UploadDocumentResponse,
    ChunksListResponse,
    DocumentsListResponse,
    SearchRequest,
    SearchResponse,
    ChatRequest,
    ChatResponse,
)
from app.api.document.services import (
    DocumentService,
    ChunkService,
    MarkdownService,
    SearchService,
    ChatService,
)

router = APIRouter()


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
    try:
        # 读取文件内容
        content = await file.read()

        # 调用服务层处理业务逻辑
        result = await DocumentService.upload_document(
            file_content=content,
            filename=file.filename or "unknown",
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        return UploadDocumentResponse(**result)

    except ValueError as e:
        # 文件格式或策略验证失败
        raise HTTPException(status_code=400, detail=str(e))
    except NotImplementedError as e:
        # 功能尚未实现
        raise HTTPException(status_code=501, detail=str(e))
    except RuntimeError as e:
        # 运行时错误
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback

        error_detail = traceback.format_exc()
        print(f"导入文件时出错: {error_detail}")
        return UploadDocumentResponse(
            success=False,
            message=f"导入文件时出错: {str(e)}",
            file_name=file.filename or "unknown",
            file_format="unknown",
            strategy=strategy,
        )


@router.get("/chunks", response_model=ChunksListResponse)
async def get_chunks(
    limit: Optional[int] = Query(None, description="返回的最大文档数量", ge=1, le=1000),
    offset: int = Query(0, description="跳过的文档数量", ge=0),
    doc_id: Optional[str] = Query(None, description="按文档 ID 过滤"),
    markdown_id: Optional[str] = Query(None, description="按 markdown ID 过滤"),
    content_type: Optional[str] = Query(None, description="按内容类型过滤"),
):
    """
    获取知识库中的所有 chunks（支持分页和过滤）
    """
    try:
        chunks, total = ChunkService.get_chunks(
            limit=limit,
            offset=offset,
            doc_id=doc_id,
            markdown_id=markdown_id,
            content_type=content_type,
        )

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
        return ChunkService.get_chunks_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取知识库信息失败: {str(e)}")


@router.get("/documents", response_model=DocumentsListResponse)
async def get_documents():
    """
    获取所有文档列表及其统计信息
    """
    try:
        documents = DocumentService.get_all_documents()
        return DocumentsListResponse(documents=documents, total=len(documents))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    删除指定文档及其所有 chunks
    """
    try:
        result = DocumentService.delete_document(doc_id)
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.delete("/clear")
async def clear_all():
    """
    清空所有文档和 chunks
    """
    try:
        result = DocumentService.clear_all()
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空数据失败: {str(e)}")


@router.get("/documents/{doc_id}/markdowns")
async def get_document_markdowns(doc_id: str):
    """
    获取文档的所有 markdown 列表
    """
    try:
        markdown_list = MarkdownService.get_markdowns_by_doc_id(doc_id)
        return {
            "status": "success",
            "doc_id": doc_id,
            "markdowns": markdown_list,
            "total": len(markdown_list),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取 markdown 列表失败: {str(e)}"
        )


@router.get("/documents/{doc_id}/markdown/check")
async def check_markdown_cache(
    doc_id: str,
    markdown_id: Optional[str] = Query(None, description="markdown 文件的唯一标识"),
):
    """
    检查文档是否有 markdown_cache（从数据库检查）

    如果提供了 markdown_id，使用 markdown_id 查找；否则检查是否有任何 markdown
    """
    try:
        return MarkdownService.check_markdown(doc_id, markdown_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"检查 markdown 失败: {str(e)}"
        )


@router.get("/documents/{doc_id}/markdown")
async def get_markdown_cache(
    doc_id: str,
    markdown_id: Optional[str] = Query(None, description="markdown 文件的唯一标识"),
):
    """
    获取文档的 markdown_cache 内容（从数据库读取）

    如果提供了 markdown_id，使用 markdown_id 查找；否则返回第一个 markdown
    """
    try:
        return MarkdownService.get_markdown(doc_id, markdown_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取 markdown 失败: {str(e)}"
        )


@router.put("/documents/{doc_id}/markdown")
async def update_markdown_cache(
    doc_id: str,
    content: str = Form(...),
    markdown_id: Optional[str] = Form(None, description="markdown 文件的唯一标识"),
):
    """
    更新文档的 markdown_cache 内容（更新到数据库）

    如果提供了 markdown_id，使用 markdown_id 保存；否则使用 doc_id（向后兼容）
    """
    try:
        return MarkdownService.update_markdown(doc_id, content, markdown_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"更新 markdown_cache 失败: {str(e)}"
        )


@router.post("/documents/{doc_id}/reprocess")
async def reprocess_document(
    doc_id: str,
    strategy: str = Form("structured"),
    markdown_id: Optional[str] = Form(None, description="markdown 文件的唯一标识"),
):
    """
    重新处理文档：删除现有 chunks，从数据库重新导入

    流程：
    1. 删除该 markdown 的所有 chunks（根据 markdown_id 过滤）
    2. 从数据库读取 markdown 内容
    3. 重新执行后续流程（split + vector store）

    如果提供了 markdown_id，使用 markdown_id 查找并只删除该 markdown 的 chunks；否则使用 doc_id（向后兼容）
    """
    try:
        return MarkdownService.reprocess_markdown(doc_id, strategy, markdown_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        import traceback

        error_detail = traceback.format_exc()
        print(f"重新处理文档时出错: {error_detail}")
        raise HTTPException(status_code=500, detail=f"重新处理文档失败: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    搜索知识库中的文档

    支持两种模式：
    1. 普通搜索：直接使用向量相似度搜索
    2. 重排序搜索：先检索更多结果，然后使用 LLM 进行重排序
    """
    try:
        results = SearchService.search(
            query=request.query,
            top_k=request.top_k,
            use_rerank=request.use_rerank,
            retrieve_k=request.retrieve_k,
        )

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
        response, sources = await ChatService.chat(request)

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


@router.post("/chat/stream/start")
async def start_chat_stream(request: ChatRequest):
    """
    启动流式对话会话
    返回会话 ID，用于后续的 EventSource 连接
    """
    session_id = ChatService.start_chat_stream(request)
    return {"session_id": session_id}


@router.get("/chat/stream/{session_id}")
async def chat_with_knowledge_base_stream(session_id: str):
    """
    基于知识库的流式对话接口（RAG Stream）

    使用 Server-Sent Events (SSE) 流式返回回复
    支持 EventSource 连接（GET 请求）
    """
    return StreamingResponse(
        ChatService.chat_stream_generator(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        },
    )
