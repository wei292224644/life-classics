from fastapi import APIRouter

from app.api.kb.service import KBService

router = APIRouter()


@router.get("/stats")
def get_stats():
    return KBService.get_stats()


@router.delete("")
def clear_all():
    return KBService.clear_all()
