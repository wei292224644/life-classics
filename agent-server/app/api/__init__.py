"""
API路由模块
"""

from fastapi import APIRouter
from app.api import query, health, chat, translate, document

router = APIRouter()

# 注册子路由
router.include_router(query.router, prefix="/query", tags=["查询"])
router.include_router(chat.router, prefix="/chat", tags=["对话"])
router.include_router(health.router, prefix="/health", tags=["健康检查"])
router.include_router(translate.router, prefix="/translate", tags=["翻译"])
router.include_router(document.router, prefix="/doc", tags=["知识库导入"])
