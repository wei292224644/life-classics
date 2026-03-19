"""
API路由模块
"""

from fastapi import APIRouter

from app.api.documents.router import router as documents_router
from app.api.chunks.router import router as chunks_router
from app.api.kb.router import router as kb_router
from app.api.search.router import router as search_router
from app.api.agent import router as agent_router

router = APIRouter()

router.include_router(documents_router, prefix="/documents", tags=["Documents"])
router.include_router(chunks_router, prefix="/chunks", tags=["Chunks"])
router.include_router(kb_router, prefix="/kb", tags=["Knowledge Base"])
router.include_router(search_router, tags=["Search & Chat"])
router.include_router(agent_router, prefix="/agent", tags=["Agent"])
