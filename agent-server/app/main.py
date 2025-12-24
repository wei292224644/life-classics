"""
FastAPI主应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from app.api import router as api_router
from app.core.config import settings

app = FastAPI(
    title="个人知识库系统",
    description="基于FastAPI + LlamaIndex + ChromaDB的个人知识库",
    version="0.1.0",
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api")


@app.get("/swagger")
async def custom_swagger_ui():
    """自定义 Swagger UI 页面，便于直接调用 API"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="个人知识库系统 - Swagger UI",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )
