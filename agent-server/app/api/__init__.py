"""
API路由模块
"""
from fastapi import APIRouter
from app.api import documents, query, health

router = APIRouter()

# 注册子路由
router.include_router(documents.router, prefix="/documents", tags=["文档管理"])
router.include_router(query.router, prefix="/query", tags=["查询"])
router.include_router(health.router, prefix="/health", tags=["健康检查"])

