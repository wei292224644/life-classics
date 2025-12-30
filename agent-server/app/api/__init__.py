"""
API路由模块
"""

from fastapi import APIRouter
from app.api import document

router = APIRouter()

# 注册子路由
router.include_router(document.router, prefix="/doc", tags=["知识库导入"])
