"""
API路由模块
"""

from fastapi import APIRouter

from api.documents.router import router as documents_router
from api.chunks.router import router as chunks_router
from api.kb.router import router as kb_router
from api.search.router import router as search_router
from api.agent import router as agent_router
from api.frontend_logs.router import router as frontend_logs_router

router = APIRouter()

router.include_router(documents_router, prefix="/documents", tags=["Documents"])
router.include_router(chunks_router, prefix="/chunks", tags=["Chunks"])
router.include_router(kb_router, prefix="/kb", tags=["Knowledge Base"])
router.include_router(search_router, tags=["Search & Chat"])
router.include_router(agent_router, prefix="/agent", tags=["Agent"])
router.include_router(frontend_logs_router, tags=["Observability"])
