"""
ChromaDB 数据查看页面（轻量 Web UI）
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.vector_store import vector_store_manager
from app.core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="app/web/templates")


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)
    except Exception:
        return str(obj)


@router.get("/chroma", response_class=HTMLResponse)
async def chroma_home(request: Request):
    """ChromaDB 概览页"""
    if settings.ENABLE_PARENT_CHILD:
        return RedirectResponse(url="/chroma/parents", status_code=302)
    info = vector_store_manager.get_collection_info()
    # 复用已有聚合逻辑（按 file_name 汇总）
    all_docs = vector_store_manager.get_all_documents()
    summary: Dict[str, Dict[str, Any]] = {}
    for d in all_docs:
        md = d.get("metadata") or {}
        file_name = md.get("file_name", "unknown")
        s = summary.setdefault(
            file_name,
            {
                "file_name": file_name,
                "file_type": md.get("file_type", "unknown"),
                "total_chunks": 0,
                "content_types": {},
            },
        )
        s["total_chunks"] += 1
        ct = md.get("content_type", "unknown")
        s["content_types"][ct] = s["content_types"].get(ct, 0) + 1

    files = sorted(summary.values(), key=lambda x: (-x["total_chunks"], x["file_name"]))
    return templates.TemplateResponse(
        "chroma_home.html",
        {
            "request": request,
            "info": info,
            "files": files,
        },
    )


@router.get("/chroma/parents", response_class=HTMLResponse)
async def chroma_parents(
    request: Request,
    q: str = Query("", description="父 chunk 文本 contains 搜索（SQLite LIKE）"),
    file_name: str = Query("", description="按文件名过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=200),
):
    """父 chunk 列表页（父子模式）"""
    info = vector_store_manager.get_collection_info()
    offset = (page - 1) * page_size
    page_data = vector_store_manager.list_parents_page(
        limit=page_size, offset=offset, file_name=file_name, q=q
    )
    parents = page_data.get("parents", [])
    total = page_data.get("total", 0)
    return templates.TemplateResponse(
        "chroma_parents.html",
        {
            "request": request,
            "info": info,
            "q": q,
            "file_name": file_name,
            "page": page,
            "page_size": page_size,
            "total": total,
            "parents": parents,
        },
    )


@router.get("/chroma/parent/{parent_id}", response_class=HTMLResponse)
async def chroma_parent_detail(request: Request, parent_id: str):
    """父 chunk 详情页：展示父 + 所有子 chunk"""
    parent = vector_store_manager.get_parent_by_id(parent_id)
    children = vector_store_manager.list_children_by_parent_id(parent_id)
    return templates.TemplateResponse(
        "chroma_parent_detail.html",
        {
            "request": request,
            "parent": parent,
            "children": children,
            "parent_metadata_json": _safe_json(parent.get("metadata")),
        },
    )


@router.get("/chroma/chunks", response_class=HTMLResponse)
async def chroma_chunks(
    request: Request,
    q: str = Query("", description="在 chunk 文本中 contains 搜索"),
    file_name: str = Query("", description="按文件名过滤"),
    content_type: str = Query("", description="按 content_type 过滤"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=200),
):
    """Chunks 列表页（分页 + 简单过滤）"""
    where: Optional[Dict[str, Any]] = None
    if file_name or content_type:
        where = {}
        if file_name:
            where["file_name"] = file_name
        if content_type:
            where["content_type"] = content_type

    where_document: Optional[Dict[str, Any]] = None
    if q.strip():
        # Chroma 支持 where_document={"$contains": "..."} 做简单文本包含过滤
        where_document = {"$contains": q.strip()}

    offset = (page - 1) * page_size
    page_data = vector_store_manager.list_chunks_page(
        limit=page_size,
        offset=offset,
        where=where,
        where_document=where_document,
    )

    # 过滤条件下的 total 可能较难精确计算；这里尽量从底层返回的 total 拿到
    total = page_data.get("total")
    chunks = page_data.get("chunks", [])

    return templates.TemplateResponse(
        "chroma_chunks.html",
        {
            "request": request,
            "q": q,
            "file_name": file_name,
            "content_type": content_type,
            "page": page,
            "page_size": page_size,
            "total": total,
            "chunks": chunks,
        },
    )


@router.get("/chroma/chunk/{chunk_id}", response_class=HTMLResponse)
async def chroma_chunk_detail(request: Request, chunk_id: str):
    """Chunk 详情页"""
    chunk = vector_store_manager.get_chunk_by_id(chunk_id)
    return templates.TemplateResponse(
        "chroma_chunk_detail.html",
        {
            "request": request,
            "chunk": chunk,
            "chunk_metadata_json": _safe_json(chunk.get("metadata")),
        },
    )


@router.post("/chroma/chunk/{chunk_id}/delete")
async def chroma_delete_chunk(request: Request, chunk_id: str):
    """删除单个 chunk"""
    # 即使不存在也执行 delete（幂等）
    vector_store_manager.delete_chunk_by_id(chunk_id)
    return RedirectResponse(url="/chroma/chunks", status_code=303)


@router.post("/chroma/clear")
async def chroma_clear_all(request: Request):
    """清空整个 collection"""
    vector_store_manager.clear_collection()
    return RedirectResponse(url="/chroma" if not settings.ENABLE_PARENT_CHILD else "/chroma/parents", status_code=303)


@router.post("/chroma/parent/{parent_id}/delete")
async def chroma_delete_parent(request: Request, parent_id: str):
    """删除父 chunk（会级联删除子 chunk）"""
    vector_store_manager.delete_parent_by_id(parent_id)
    return RedirectResponse(url="/chroma/parents", status_code=303)


