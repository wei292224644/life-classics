"""MinerU 适配器测试（mock HTTP）"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.pdf.mineru_adapter import pdf_to_markdown


@patch("app.core.pdf.mineru_adapter.requests.post")
@patch("app.core.pdf.mineru_adapter.Path.exists", return_value=True)
def test_pdf_to_markdown_returns_markdown_string(mock_exists, mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"markdown": "## 测试\n内容"}
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    with patch("builtins.open", MagicMock()):
        result = pdf_to_markdown("/tmp/test.pdf")

    assert "## 测试" in result
    assert "内容" in result


@patch("app.core.pdf.mineru_adapter.requests.post")
@patch("app.core.pdf.mineru_adapter.Path.exists", return_value=True)
def test_pdf_to_markdown_accepts_content_key(mock_exists, mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"content": "# 标题\n正文"}
    mock_resp.raise_for_status = MagicMock()
    mock_post.return_value = mock_resp

    with patch("builtins.open", MagicMock()):
        result = pdf_to_markdown("/tmp/test.pdf")

    assert "标题" in result
    assert "正文" in result
