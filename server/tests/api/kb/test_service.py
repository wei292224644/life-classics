from unittest.mock import MagicMock, patch


def test_get_stats_counts_correctly():
    mock_col = MagicMock()
    mock_col.get.return_value = {
        "ids": ["c1", "c2", "c3"],
        "metadatas": [
            {"doc_id": "d1", "semantic_type": "scope"},
            {"doc_id": "d1", "semantic_type": "definition"},
            {"doc_id": "d2", "semantic_type": "scope"},
        ],
    }

    with patch("app.api.kb.service.get_collection", return_value=mock_col):
        from app.api.kb.service import KBService
        stats = KBService.get_stats()

    assert stats["total_chunks"] == 3
    assert stats["total_documents"] == 2
    assert stats["semantic_types"]["scope"] == 2
    assert stats["semantic_types"]["definition"] == 1


def test_clear_all_deletes_from_chroma_and_fts():
    mock_col = MagicMock()
    mock_col.get.return_value = {"ids": ["c1", "c2"], "metadatas": [
        {"doc_id": "d1"}, {"doc_id": "d2"}
    ]}

    with patch("app.api.kb.service.get_collection", return_value=mock_col), \
         patch("app.api.kb.service.fts_writer") as mock_fts:
        from app.api.kb.service import KBService
        result = KBService.clear_all()

    mock_col.delete.assert_called_once_with(ids=["c1", "c2"])
    assert result["deleted_chunks"] == 2
