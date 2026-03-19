from unittest.mock import MagicMock, patch

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
    mock_col = MagicMock()
    mock_col.get.return_value = {
        "ids": ["c1", "c2", "c3"],
        "metadatas": [
            _make_meta("d1", "GB 2762-2022", "food_safety"),
            _make_meta("d1", "GB 2762-2022", "food_safety", "definition"),
            _make_meta("d2", "GB 5009.3", "method"),
        ],
    }

    with patch("app.api.documents.service.get_collection", return_value=mock_col):
        from app.api.documents.service import DocumentsService
        docs = DocumentsService.get_all_documents()

    assert len(docs) == 2
    d1 = next(d for d in docs if d["doc_id"] == "d1")
    assert d1["standard_no"] == "GB 2762-2022"
    assert d1["doc_type"] == "food_safety"
    assert d1["chunks_count"] == 2


def test_get_all_documents_returns_empty_list_when_no_chunks():
    mock_col = MagicMock()
    mock_col.get.return_value = {"ids": [], "metadatas": []}

    with patch("app.api.documents.service.get_collection", return_value=mock_col):
        from app.api.documents.service import DocumentsService
        docs = DocumentsService.get_all_documents()

    assert docs == []


def test_delete_document_calls_chroma_and_fts():
    """删除时同时清理 ChromaDB 和 FTS"""
    mock_col = MagicMock()

    with patch("app.api.documents.service.get_collection", return_value=mock_col), \
         patch("app.api.documents.service.fts_writer") as mock_fts:
        from app.api.documents.service import DocumentsService
        result = DocumentsService.delete_document("d1")

    mock_col.delete.assert_called_once_with(where={"doc_id": {"$eq": "d1"}})
    mock_fts.delete_by_doc_id.assert_called_once()
    assert result["doc_id"] == "d1"


async def test_upload_document_returns_501():
    """上传文档返回 501 Not Implemented"""
    from app.api.documents.service import DocumentsService
    with pytest.raises(HTTPException) as exc_info:
        await DocumentsService.upload_document(b"content", "test.md", "text")
    assert exc_info.value.status_code == 501
    assert "文档上传功能尚未实现" in exc_info.value.detail
