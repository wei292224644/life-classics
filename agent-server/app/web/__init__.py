"""
Web UI 路由模块（用于在浏览器中查看 ChromaDB 数据）
"""

from fastapi import APIRouter

from app.web.chroma_viewer import router as chroma_viewer_router

router = APIRouter()

# Web UI 入口（不放在 /api 下，方便直接在浏览器访问）
router.include_router(chroma_viewer_router, tags=["ChromaDB Viewer"])


