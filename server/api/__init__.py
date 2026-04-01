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
from api.product.router import router as product_router
from api.analysis.router import router as analysis_router
from api.ingredient_alias.router import router as ingredient_alias_router
from api.ingredients.router import router as ingredients_router
from api.ingredient_analysis.router import router as ingredient_analysis_router

router = APIRouter()

router.include_router(documents_router, prefix="/documents", tags=["Documents"])
router.include_router(chunks_router, prefix="/chunks", tags=["Chunks"])
router.include_router(kb_router, prefix="/kb", tags=["Knowledge Base"])
router.include_router(search_router, tags=["Search & Chat"])
router.include_router(agent_router, prefix="/agent", tags=["Agent"])
router.include_router(frontend_logs_router, tags=["Observability"])
router.include_router(product_router, tags=["Product"])
router.include_router(analysis_router, prefix="/analysis", tags=["Analysis"])
router.include_router(ingredient_alias_router, prefix="/ingredient-aliases", tags=["Ingredient Alias"])
router.include_router(ingredients_router, prefix="/ingredients", tags=["Ingredient"])
router.include_router(ingredient_analysis_router, tags=["IngredientAnalysis"])
