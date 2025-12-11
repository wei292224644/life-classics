"""
健康检查API
"""
from fastapi import APIRouter
from app.core.vector_store import vector_store_manager

router = APIRouter()


@router.get("/")
async def health_check():
    """健康检查"""
    try:
        info = vector_store_manager.get_collection_info()
        return {
            "status": "healthy",
            "vector_store": info
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

