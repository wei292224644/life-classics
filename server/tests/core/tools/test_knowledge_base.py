"""
tests/core/tools/test_knowledge_base.py

测试 knowledge_base 工具的格式化输出、空结果处理、异常处理。
"""

import importlib
import pytest
from unittest.mock import AsyncMock, patch

import agent.tools.knowledge_base  # 确保模块已导入，使 patch 可以解析路径


@pytest.mark.asyncio
async def test_knowledge_base_formats_results():
    """验证工具正确格式化标准号、原始内容和相关度分数。"""
    mock_results = [
        {
            "chunk_id": "id1",
            "standard_no": "GB-001",
            "semantic_type": "scope",
            "section_path": "1|1.1",
            "content": "检测内容",
            "raw_content": "原始内容",
            "score": 0.95,
        }
    ]
    with patch("app.core.tools.knowledge_base.search", AsyncMock(return_value=mock_results)):
        from agent.tools.knowledge_base import knowledge_base

        result = await knowledge_base.ainvoke({"query": "农药残留", "top_k": 5})

    assert "GB-001" in result
    assert "原始内容" in result
    assert "0.95" in result


@pytest.mark.asyncio
async def test_knowledge_base_multiple_results():
    """验证多条结果按 [1] [2] 序号格式化。"""
    mock_results = [
        {
            "chunk_id": "id1",
            "standard_no": "GB 2762-2022",
            "semantic_type": "specification_table",
            "section_path": "3",
            "content": "铅限量内容",
            "raw_content": "铅（Pb）限量：0.1 mg/kg",
            "score": 0.92,
        },
        {
            "chunk_id": "id2",
            "standard_no": "GB 2763-2021",
            "semantic_type": "scope",
            "section_path": "1",
            "content": "农药残留内容",
            "raw_content": "农药最大残留限量",
            "score": 0.85,
        },
    ]
    with patch("app.core.tools.knowledge_base.search", AsyncMock(return_value=mock_results)):
        from agent.tools.knowledge_base import knowledge_base

        result = await knowledge_base.ainvoke({"query": "铅限量", "top_k": 5})

    assert "[1]" in result
    assert "[2]" in result
    assert "GB 2762-2022" in result
    assert "GB 2763-2021" in result
    assert "铅（Pb）限量：0.1 mg/kg" in result
    assert "农药最大残留限量" in result


@pytest.mark.asyncio
async def test_knowledge_base_empty_results():
    """验证空结果时返回 '未检索到相关文档'。"""
    with patch("app.core.tools.knowledge_base.search", AsyncMock(return_value=[])):
        from agent.tools.knowledge_base import knowledge_base

        result = await knowledge_base.ainvoke({"query": "不存在的内容", "top_k": 5})

    assert "未检索到相关文档" in result


@pytest.mark.asyncio
async def test_knowledge_base_exception_handling():
    """验证 search 抛出异常时返回错误信息字符串。"""
    with patch(
        "app.core.tools.knowledge_base.search",
        AsyncMock(side_effect=RuntimeError("连接失败")),
    ):
        from agent.tools.knowledge_base import knowledge_base

        result = await knowledge_base.ainvoke({"query": "测试查询", "top_k": 5})

    assert "知识库检索失败" in result
    assert "连接失败" in result
