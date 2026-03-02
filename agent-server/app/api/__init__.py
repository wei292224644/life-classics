"""
API路由模块
"""

from fastapi import APIRouter
from app.api.document import router as document_router
from app.api.agent import router as agent_router

router = APIRouter()

# 注册子路由
router.include_router(document_router, prefix="/doc", tags=["知识库"])
router.include_router(agent_router, prefix="/agent", tags=["Agent"])
