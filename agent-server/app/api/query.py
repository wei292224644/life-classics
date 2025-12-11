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
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="查询内容不能为空")
        
        # 执行向量查询
        response = vector_store_manager.query(
            query_str=request.query,
            top_k=request.top_k
        )
        
        # 提取答案和来源
        answer = str(response)
        sources = []
        
        # 尝试提取来源信息
        if hasattr(response, "source_nodes"):
            for node in response.source_nodes:
                source_info = {
                    "text": node.text[:200] + "..." if len(node.text) > 200 else node.text,
                    "metadata": node.metadata if hasattr(node, "metadata") else {}
                }
                sources.append(source_info)
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            metadata={
                "query": request.query,
                "top_k": request.top_k
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/test")
async def test_query():
    """测试查询接口"""
    return {
        "message": "查询接口正常",
        "usage": "POST /api/query/ 发送查询请求"
    }

