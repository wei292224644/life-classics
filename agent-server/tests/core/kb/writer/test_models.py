from app.core.kb.writer.models import WriteResult

def test_write_result_structure():
    result: WriteResult = {
        "standard_no": "GB/T-001",
        "chunks_written": 5,
        "chroma_ok": True,
        "neo4j_ok": False,
        "errors": ["neo4j write error: timeout"],
    }
    assert result["standard_no"] == "GB/T-001"
    assert result["chunks_written"] == 5
    assert result["chroma_ok"] is True
    assert result["neo4j_ok"] is False
    assert len(result["errors"]) == 1
