"""
tests/core/tools/test_neo4j_query.py

测试 neo4j_query 工具：只读事务、LIMIT 注入、错误处理、结果格式。
"""

import json
import pytest
from unittest.mock import MagicMock, patch

import neo4j.exceptions


@pytest.mark.asyncio
async def test_readonly_transaction():
    """确保使用 execute_read 而非 execute_write，且 lambda 真正被执行。"""
    called = {"execute_read": False, "execute_write": False}
    executed_queries = []

    def fake_execute_read(fn):
        called["execute_read"] = True
        mock_tx = MagicMock()
        mock_tx.run.return_value = iter([])
        fn(mock_tx)
        executed_queries.append(mock_tx.run.call_args[0][0])
        return []

    def fake_execute_write(fn):
        called["execute_write"] = True

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute_read = fake_execute_read
    mock_session.execute_write = fake_execute_write

    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session

    with patch("agent.tools.neo4j_query.get_driver", return_value=mock_driver):
        from agent.tools.neo4j_query import neo4j_query

        await neo4j_query("MATCH (n) RETURN n LIMIT 10")

    assert called["execute_read"] is True, "execute_read 应被调用"
    assert called["execute_write"] is False, "execute_write 不应被调用"
    assert len(executed_queries) == 1, "lambda 应真正执行并调用 tx.run"


@pytest.mark.asyncio
async def test_limit_injection_when_missing():
    """Cypher 无 LIMIT 时末尾自动追加 LIMIT 50。"""
    captured_queries = []

    def fake_execute_read(func):
        mock_tx = MagicMock()

        def capture_run(q, **kwargs):
            captured_queries.append(q)
            return iter([])

        mock_tx.run = capture_run
        func(mock_tx)
        return []

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute_read = MagicMock(side_effect=fake_execute_read)

    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session

    with patch("agent.tools.neo4j_query.get_driver", return_value=mock_driver):
        from agent.tools.neo4j_query import neo4j_query

        await neo4j_query("MATCH (n) RETURN n")

    assert len(captured_queries) == 1
    assert captured_queries[0].upper().endswith("LIMIT 50")


@pytest.mark.asyncio
async def test_limit_injection_case_insensitive():
    """Cypher 含小写 'limit 10' 时不重复追加。"""
    captured_queries = []

    def fake_execute_read(func):
        mock_tx = MagicMock()

        def capture_run(q, **kwargs):
            captured_queries.append(q)
            return iter([])

        mock_tx.run = capture_run
        func(mock_tx)
        return []

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute_read = MagicMock(side_effect=fake_execute_read)

    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session

    with patch("agent.tools.neo4j_query.get_driver", return_value=mock_driver):
        from agent.tools.neo4j_query import neo4j_query

        await neo4j_query("MATCH (n) RETURN n limit 10")

    assert len(captured_queries) == 1
    # 只有一处 LIMIT 相关子句（大小写不敏感计数）
    import re
    limit_matches = re.findall(r"\bLIMIT\b", captured_queries[0], re.IGNORECASE)
    assert len(limit_matches) == 1


@pytest.mark.asyncio
async def test_connection_error_returns_string():
    """get_driver() 抛异常时返回字符串而非抛异常。"""
    with patch(
        "agent.tools.neo4j_query.get_driver",
        side_effect=RuntimeError("连接被拒绝"),
    ):
        from agent.tools.neo4j_query import neo4j_query

        result = await neo4j_query("MATCH (n) RETURN n")

    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_cypher_error_returns_string():
    """execute_read 内部抛 CypherSyntaxError 时返回错误字符串。"""
    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute_read = MagicMock(
        side_effect=neo4j.exceptions.CypherSyntaxError("Invalid Cypher")
    )

    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session

    with patch("agent.tools.neo4j_query.get_driver", return_value=mock_driver):
        from agent.tools.neo4j_query import neo4j_query

        result = await neo4j_query("MATCH (n) RETURN invalid syntax @@")

    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_result_json_format():
    """正常查询返回含 columns/rows/count 的 JSON 字符串。"""
    mock_record = MagicMock()
    mock_record.keys.return_value = ["name_zh", "max_usage"]
    mock_record.values.return_value = ["山梨酸", "1.0"]

    mock_session = MagicMock()
    mock_session.__enter__ = MagicMock(return_value=mock_session)
    mock_session.__exit__ = MagicMock(return_value=False)
    mock_session.execute_read = MagicMock(return_value=[mock_record])

    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session

    with patch("agent.tools.neo4j_query.get_driver", return_value=mock_driver):
        from agent.tools.neo4j_query import neo4j_query

        result = await neo4j_query("MATCH (n) RETURN n.name_zh, n.max_usage LIMIT 1")

    parsed = json.loads(result)
    assert "columns" in parsed
    assert "rows" in parsed
    assert "count" in parsed
    assert parsed["count"] == 1
