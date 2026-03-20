"""
tests/core/tools/test_neo4j_vector_search.py

测试 neo4j_vector_search 工具：嵌入请求格式、不支持标签、结果格式、错误处理、top_k 传递。
"""

import json
import pytest
import requests as requests_lib
from unittest.mock import MagicMock, patch, AsyncMock


def make_to_thread_passthrough():
    """
    返回一个替代 asyncio.to_thread 的 async 函数，
    直接在当前线程同步调用传入的函数，使 mock patch 对被调函数仍然生效。
    """
    async def _passthrough(fn, *args, **kwargs):
        return fn(*args, **kwargs)
    return _passthrough


@pytest.mark.asyncio
async def test_embedding_request_format():
    """验证向 Ollama 发送的 POST 请求 URL 和 body 均正确。"""
    search_text = "菜罐头"

    mock_embed_response = MagicMock()
    mock_embed_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
    mock_embed_response.raise_for_status = MagicMock()

    def fake_execute_read(fn):
        mock_tx = MagicMock()
        mock_tx.run.return_value = iter([])
        fn(mock_tx)
        return []

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute_read = MagicMock(side_effect=fake_execute_read)

    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session

    with patch("agent.tools.neo4j_vector_search.requests.post", return_value=mock_embed_response) as mock_post, \
         patch("agent.tools.neo4j_vector_search.get_driver", return_value=mock_driver), \
         patch("agent.tools.neo4j_vector_search.asyncio.to_thread", new=make_to_thread_passthrough()):
        from agent.tools.neo4j_vector_search import neo4j_vector_search

        await neo4j_vector_search(search_text, "FoodCategory")

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    url = call_args[0][0]
    assert "/api/embed" in url, f"URL 应包含 /api/embed，实际为: {url}"

    json_body = call_args[1]["json"]
    assert json_body["model"] == "qwen3-embedding:4b", f"model 应为 qwen3-embedding:4b，实际为: {json_body.get('model')}"
    assert json_body["input"] == search_text, f"input 应为搜索文本，实际为: {json_body.get('input')}"


@pytest.mark.asyncio
async def test_unsupported_label_returns_error():
    """传入不支持的 node_label 时返回含支持类型信息的错误字符串。"""
    from agent.tools.neo4j_vector_search import neo4j_vector_search

    result = await neo4j_vector_search("test", "InvalidLabel")

    assert isinstance(result, str), "返回值应为字符串"
    # 应包含支持的节点类型信息
    assert "Chemical" in result or "支持" in result or "支持的节点" in result or "node_label" in result, \
        f"错误信息应包含支持的节点类型，实际为: {result}"


@pytest.mark.asyncio
async def test_result_json_format():
    """正常调用返回含 node_label/results/count 的 JSON 字符串。"""
    mock_embed_response = MagicMock()
    mock_embed_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
    mock_embed_response.raise_for_status = MagicMock()

    mock_node = MagicMock()
    mock_node.__getitem__ = MagicMock(side_effect=lambda key: {"code": "04.01", "name": "蔬菜及其制品"}[key])

    mock_record = MagicMock()
    mock_record.__getitem__ = MagicMock(side_effect=lambda key: {
        "node": mock_node,
        "score": 0.92,
    }[key])

    def fake_execute_read(fn):
        mock_tx = MagicMock()
        mock_tx.run.return_value = iter([mock_record])
        fn(mock_tx)
        return [mock_record]

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute_read = MagicMock(side_effect=fake_execute_read)

    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session

    with patch("agent.tools.neo4j_vector_search.requests.post", return_value=mock_embed_response), \
         patch("agent.tools.neo4j_vector_search.get_driver", return_value=mock_driver), \
         patch("agent.tools.neo4j_vector_search.asyncio.to_thread", new=make_to_thread_passthrough()):
        from agent.tools.neo4j_vector_search import neo4j_vector_search

        result = await neo4j_vector_search("蔬菜罐头", "FoodCategory")

    parsed = json.loads(result)
    assert "node_label" in parsed, "返回 JSON 应含 node_label"
    assert "results" in parsed, "返回 JSON 应含 results"
    assert "count" in parsed, "返回 JSON 应含 count"
    assert parsed["node_label"] == "FoodCategory"


@pytest.mark.asyncio
async def test_ollama_error_returns_string():
    """requests.post 抛异常时返回字符串，不 raise。"""
    with patch("agent.tools.neo4j_vector_search.requests.post",
               side_effect=requests_lib.exceptions.ConnectionError("连接失败")), \
         patch("agent.tools.neo4j_vector_search.asyncio.to_thread", new=make_to_thread_passthrough()):
        from agent.tools.neo4j_vector_search import neo4j_vector_search

        result = await neo4j_vector_search("test", "Chemical")

    assert isinstance(result, str), "Ollama 连接失败时应返回字符串"


@pytest.mark.asyncio
async def test_top_k_passed_to_query():
    """top_k 参数正确传入向量查询（Cypher 参数中含 top_k=3）。"""
    mock_embed_response = MagicMock()
    mock_embed_response.json.return_value = {"embeddings": [[0.1, 0.2, 0.3]]}
    mock_embed_response.raise_for_status = MagicMock()

    captured_params = {}

    def fake_execute_read(fn):
        mock_tx = MagicMock()

        def capture_run(query, **kwargs):
            captured_params.update(kwargs)
            captured_params["_query"] = query
            return iter([])

        mock_tx.run = capture_run
        fn(mock_tx)
        return []

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute_read = MagicMock(side_effect=fake_execute_read)

    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session

    with patch("agent.tools.neo4j_vector_search.requests.post", return_value=mock_embed_response), \
         patch("agent.tools.neo4j_vector_search.get_driver", return_value=mock_driver), \
         patch("agent.tools.neo4j_vector_search.asyncio.to_thread", new=make_to_thread_passthrough()):
        from agent.tools.neo4j_vector_search import neo4j_vector_search

        await neo4j_vector_search("test", "Chemical", top_k=3)

    # top_k=3 应体现在 Cypher 参数中
    assert captured_params.get("top_k") == 3, \
        f"top_k=3 应传入查询参数，捕获到的参数: {captured_params}"
