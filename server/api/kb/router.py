import asyncio

from fastapi import APIRouter

from api.kb.models import KBStatsResponse
from api.kb.service import KBService

router = APIRouter()


@router.get("/stats", response_model=KBStatsResponse)
async def get_stats():
    return await asyncio.to_thread(KBService.get_stats)
