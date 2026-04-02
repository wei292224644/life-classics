import asyncio

from fastapi import APIRouter, Depends

from api.kb.models import KBStatsResponse
from api.kb.service import KBApiService
from services.kb_service import KBService as L2KBService

router = APIRouter()


def get_l2_kb_service() -> L2KBService:
    return L2KBService()


def get_kb_api_service() -> KBApiService:
    return KBApiService(l2_kb_service=get_l2_kb_service())


@router.get("/stats", response_model=KBStatsResponse)
async def get_stats(svc: KBApiService = Depends(get_kb_api_service)):
    return await asyncio.to_thread(svc.get_stats)
