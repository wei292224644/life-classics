"""测试 POST /api/logs 端点。"""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_accepts_valid_log_entry():
    """合法日志 payload 应返回 200。"""
    resp = client.post("/api/logs", json={
        "level": "error",
        "service": "console-web",
        "message": "TypeError: Cannot read",
        "stack": "at ChunkCard.tsx:42",
        "url": "/chunks",
        "user_agent": "Mozilla/5.0",
        "timestamp": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 200


def test_rejects_missing_required_fields():
    """缺少 message 字段应返回 422。"""
    resp = client.post("/api/logs", json={"level": "error"})
    assert resp.status_code == 422


def test_stack_field_truncated_to_2000_chars():
    """stack 字段超过 2000 字符应被截断，请求仍成功。"""
    long_stack = "x" * 5000
    resp = client.post("/api/logs", json={
        "level": "error",
        "service": "console-web",
        "message": "test",
        "stack": long_stack,
        "url": "/",
        "user_agent": "test",
        "timestamp": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 200


def test_rejects_unknown_log_level():
    """level 字段只接受合法值。"""
    resp = client.post("/api/logs", json={
        "level": "UNKNOWN_LEVEL",
        "service": "console-web",
        "message": "test",
        "stack": "",
        "url": "/",
        "user_agent": "test",
        "timestamp": "2026-03-21T10:00:00Z",
    })
    assert resp.status_code == 422
