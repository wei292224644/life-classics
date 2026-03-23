"""
FastAPI 主应用入口
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from prometheus_fastapi_instrumentator import Instrumentator

from api import router as api_router
from config import settings
from observability.configure import configure_logging, setup_otel
from observability.middleware import RequestLoggingMiddleware

# ── 可观测性初始化（在 app 创建之前）─────────────────────────────────────────
configure_logging(log_level=settings.LOG_LEVEL, service_name=settings.OTEL_SERVICE_NAME)
setup_otel(otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT, service_name=settings.OTEL_SERVICE_NAME)

app = FastAPI(
    title="个人知识库系统",
    description="基于FastAPI + LlamaIndex + ChromaDB的个人知识库",
    version="0.1.0",
)

# OTel FastAPI 自动 instrumentation
FastAPIInstrumentor.instrument_app(app)

# Prometheus /metrics 端点
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# 请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# 注册路由
app.include_router(api_router, prefix="/api")

# 挂载 admin 静态文件（build 后才存在）
_admin_dist = os.path.join(os.path.dirname(__file__), "..", "..", "web", "apps", "console", "dist")
if os.path.isdir(_admin_dist):
    from fastapi.staticfiles import StaticFiles
    app.mount("/admin", StaticFiles(directory=_admin_dist, html=True), name="admin")


@app.get("/swagger")
async def custom_swagger_ui():
    """自定义 Swagger UI 页面，便于直接调用 API"""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="个人知识库系统 - Swagger UI",
        swagger_favicon_url="https://fastapi.tiangolo.com/img/favicon.png",
    )

# 将 CORS 作为最外层 ASGI 包裹，确保即使出现未处理异常（500）也会带上 CORS 头。
app = CORSMiddleware(
    app=app,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
