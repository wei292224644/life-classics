import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


def _make_meta(doc_id="d1", standard_no="GB 2762-2022", doc_type="food_safety", semantic_type="scope", section_path="1|1.1"):
    return {
        "doc_id": doc_id,
        "standard_no": standard_no,
        "doc_type": doc_type,
        "semantic_type": semantic_type,
        "section_path": section_path,
    }


def test_get_all_documents_aggregates_by_doc_id():
    """按 doc_id 聚合，返回 standard_no / doc_type / chunks_count"""
    from api.documents.service import DocumentsService  # ensure module in sys.modules

    mock_col = MagicMock()
    mock_col.get.return_value = {
        "ids": ["c1", "c2", "c3"],
        "metadatas": [
            _make_meta("d1", "GB 2762-2022", "food_safety"),
            _make_meta("d1", "GB 2762-2022", "food_safety", "definition"),
            _make_meta("d2", "GB 5009.3", "method"),
        ],
    }

    with patch("api.documents.service.get_collection", return_value=mock_col):
        docs = DocumentsService.get_all_documents()

    assert len(docs) == 2
    d1 = next(d for d in docs if d["doc_id"] == "d1")
    assert d1["standard_no"] == "GB 2762-2022"
    assert d1["doc_type"] == "food_safety"
    assert d1["chunks_count"] == 2


def test_get_all_documents_returns_empty_list_when_no_chunks():
    from api.documents.service import DocumentsService  # ensure module in sys.modules

    mock_col = MagicMock()
    mock_col.get.return_value = {"ids": [], "metadatas": []}

    with patch("api.documents.service.get_collection", return_value=mock_col):
        docs = DocumentsService.get_all_documents()

    assert docs == []


def test_delete_document_calls_chroma_and_fts():
    """删除时同时清理 ChromaDB 和 FTS"""
    from api.documents.service import DocumentsService  # ensure module in sys.modules

    mock_col = MagicMock()

    with patch("api.documents.service.get_collection", return_value=mock_col), \
         patch("api.documents.service.fts_writer") as mock_fts:
        result = DocumentsService.delete_document("d1")

    mock_col.delete.assert_called_once_with(where={"doc_id": {"$eq": "d1"}})
    mock_fts.delete_by_doc_id.assert_called_once()
    assert result["doc_id"] == "d1"


@pytest.mark.asyncio
async def test_upload_document_stream_yields_stage_events():
    """upload_document_stream 应依次 yield stage 事件和 done 事件，并写入 KB"""
    from api.documents.service import DocumentsService  # ensure module in sys.modules

    fake_events = [
        {"type": "stage", "stage": "parse", "status": "active"},
        {"type": "stage", "stage": "parse", "status": "done"},
        {"type": "workflow_done", "chunks": [{"chunk_id": "abc"}]},
    ]

    async def fake_stream(*args, **kwargs):
        for e in fake_events:
            yield e

    with patch("api.documents.service.run_parser_workflow_stream", fake_stream), \
         patch("api.documents.service.chroma_writer") as mock_chroma, \
         patch("api.documents.service.fts_writer") as mock_fts:
        mock_chroma.write = AsyncMock()

        results = []
        async for line in DocumentsService.upload_document_stream(b"# test", "test.md"):
            results.append(line)

    assert results[0] == f"data: {json.dumps({'type': 'stage', 'stage': 'parse', 'status': 'active'})}\n\n"
    assert results[1] == f"data: {json.dumps({'type': 'stage', 'stage': 'parse', 'status': 'done'})}\n\n"
    assert results[2] == f"data: {json.dumps({'type': 'done', 'chunks_count': 1})}\n\n"
    mock_chroma.write.assert_called_once()
    mock_fts.write.assert_called_once()


@pytest.mark.asyncio
async def test_upload_document_stream_utf8_error():
    """非 UTF-8 文件应 yield error 事件并直接返回"""
    from api.documents.service import DocumentsService  # ensure module in sys.modules

    results = []
    async for line in DocumentsService.upload_document_stream(b"\xff\xfe", "bad.md"):
        results.append(line)

    assert len(results) == 1
    payload = json.loads(results[0].removeprefix("data: ").rstrip())
    assert payload["type"] == "error"
    assert "UTF-8" in payload["message"]
