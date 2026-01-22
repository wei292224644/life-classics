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


@router.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    """检索测试页面"""
    return templates.TemplateResponse("search.html", {"request": request})


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """知识库对话页面"""
    return templates.TemplateResponse("chat.html", {"request": request})


@router.get("/documents/{doc_id}/edit", response_class=HTMLResponse)
async def edit_document_page(request: Request, doc_id: str):
    """编辑文档的 markdown_cache 页面"""
    return templates.TemplateResponse("edit_document.html", {
        "request": request,
        "doc_id": doc_id,
    })
