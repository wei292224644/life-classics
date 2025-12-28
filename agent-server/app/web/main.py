"""
Web 路由模块
提供知识库查看器的各个页面路由
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()

# 模板目录
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主入口页面（SPA路由）"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    """文档列表页面"""
    return templates.TemplateResponse("documents.html", {"request": request})


@router.get("/chunks", response_class=HTMLResponse)
async def chunks_page(request: Request):
    """Chunks 列表页面"""
    return templates.TemplateResponse("chunks.html", {"request": request})


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """文档上传页面"""
    return templates.TemplateResponse("upload.html", {"request": request})
