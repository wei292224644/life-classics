"""
查询API
"""
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.vector_store import vector_store_manager
from app.core.llm import get_llm

router = APIRouter()


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str
    top_k: Optional[int] = 5


class QueryResponse(BaseModel):
    """查询响应模型"""
    answer: str
    sources: list
    metadata: dict


@router.post("/", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest):
    """查询知识库"""
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    
    # 执行向量查询
    documents = vector_store_manager.query(
        query_str=request.query,
        top_k=request.top_k
    )
    
    # 提取答案和来源
    answer_parts = []
    sources = []
    
    for i, doc in enumerate(documents, 1):
        text = doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
        answer_parts.append(f"[文档{i}]\n{text}")
        source_info = {
            "text": text,
            "metadata": doc.metadata if hasattr(doc, "metadata") else {}
        }
        sources.append(source_info)
    
    answer = "\n\n".join(answer_parts) if answer_parts else "未找到相关文档"
    
    return QueryResponse(
        answer=answer,
        sources=sources,
        metadata={
            "query": request.query,
            "top_k": request.top_k
        }
    )


@router.get("/test")
async def test_query():
    """测试查询接口"""
    return {
        "message": "查询接口正常",
        "usage": "POST /api/query/ 发送查询请求"
    }

