"""
API路由模块
"""

from fastapi import APIRouter
from app.api.document import router as document_router

router = APIRouter()

# 注册子路由
router.include_router(document_router, prefix="/doc", tags=["知识库导入"])
