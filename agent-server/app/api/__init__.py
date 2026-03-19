"""
API路由模块
"""

from fastapi import APIRouter

router = APIRouter()

try:
    from app.api.document import router as document_router
    router.include_router(document_router, prefix="/doc", tags=["知识库"])
except Exception:
    pass

from app.api.agent import router as agent_router
router.include_router(agent_router, prefix="/agent", tags=["Agent"])
