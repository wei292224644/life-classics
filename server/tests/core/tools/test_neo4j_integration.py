"""
tests/core/tools/test_neo4j_integration.py

Neo4j 集成测试：验证与真实 gb2760_2024 database 的连接和两阶段查询流程。

注意：
- 这些测试需要真实的 Neo4j 实例 + Ollama 服务
- 需要 pyproject.toml 注册的 integration marker
- 运行时：pytest -v -m integration
"""

import json
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_connectivity():
    """
    确认 gb2760_2024 database 可连接且含数据。

    目的：验证 Neo4j 连接、数据库存在、至少有 1 个节点
    """
    from agent.tools.neo4j_query import neo4j_query

    result = await neo4j_query("MATCH (n) RETURN count(n) AS cnt")

    # 返回值应为 JSON 字符串
    assert isinstance(result, str), f"预期返回字符串，实际为 {type(result)}"

    # 解析 JSON
    data = json.loads(result)

    # 验证响应格式
    assert "columns" in data, "响应应包含 columns"
    assert "rows" in data, "响应应包含 rows"
    assert "count" in data, "响应应包含 count"

    # 验证查询成功（count 返回 1 行）
    assert data["count"] == 1, f"COUNT 查询应返回 1 行，实际 {data['count']}"

    # 验证节点数 > 0
    cnt = data["rows"][0][0]
    assert cnt > 0, f"图谱中节点数应 > 0，实际 {cnt}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vector_search_food_category():
    """
    搜索 '蔬菜罐头'，验证返回的 FoodCategory 节点。

    目的：验证向量搜索功能、Ollama 嵌入调用、Neo4j 向量索引查询
    预期：top-1 score 应 > 0.7
    """
    from agent.tools.neo4j_vector_search import neo4j_vector_search

    result = await neo4j_vector_search("蔬菜罐头", "FoodCategory")

    # 返回值应为 JSON 字符串
    assert isinstance(result, str), f"预期返回字符串，实际为 {type(result)}"

    # 解析 JSON
    data = json.loads(result)

    # 验证响应格式
    assert "node_label" in data, "响应应包含 node_label"
    assert "results" in data, "响应应包含 results"
    assert "count" in data, "响应应包含 count"

    # 验证 node_label 正确
    assert data["node_label"] == "FoodCategory", \
        f"node_label 应为 FoodCategory，实际 {data['node_label']}"

    # 验证至少有一条结果
    assert data["count"] > 0, f"应至少找到 1 条 FoodCategory，实际 {data['count']}"

    # 验证 top-1 score
    top_result = data["results"][0]
    assert "score" in top_result, "结果应包含 score 字段"
    assert top_result["score"] > 0.7, \
        f"top-1 score 应 > 0.7，实际 {top_result['score']}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_two_phase():
    """
    完整的两阶段流程：
    1. 向量搜索 '蔬菜罐头' 获取 FoodCategory 节点的 code
    2. Cypher 查询该 code 对应的所有 Chemical 及其许可使用信息

    目的：验证两个工具的端到端集成
    """
    from agent.tools.neo4j_vector_search import neo4j_vector_search
    from agent.tools.neo4j_query import neo4j_query

    # ===== 阶段 1：向量搜索解析实体 =====
    result1 = await neo4j_vector_search("蔬菜罐头", "FoodCategory")

    # 验证第一阶段成功
    assert isinstance(result1, str), f"第一阶段返回值应为字符串，实际 {type(result1)}"
    data1 = json.loads(result1)

    assert data1["count"] > 0, f"第一阶段应找到结果，实际 count={data1['count']}"

    # 提取 code（用于下一阶段的结构化查询）
    top_match = data1["results"][0]
    assert "code" in top_match, "FoodCategory 结果应包含 code 字段"
    code = top_match["code"]
    assert isinstance(code, str) and len(code) > 0, f"code 应为非空字符串，实际 {code}"

    # ===== 阶段 2：结构化查询获取该分类下的添加剂 =====
    # Cypher 查询：该 FoodCategory 允许使用的所有 Chemical（通过 PERMITTED_IN 关系）
    cypher = (
        f"MATCH (c:Chemical)-[r:PERMITTED_IN]->(f:FoodCategory {{code:'{code}'}}) "
        "RETURN c.name_zh, r.max_usage, r.unit"
    )
    result2 = await neo4j_query(cypher)

    # 验证第二阶段成功
    assert isinstance(result2, str), f"第二阶段返回值应为字符串，实际 {type(result2)}"
    data2 = json.loads(result2)

    # 验证响应格式
    assert "columns" in data2, "第二阶段响应应包含 columns"
    assert "rows" in data2, "第二阶段响应应包含 rows"
    assert "count" in data2, "第二阶段响应应包含 count"

    # 验证至少找到 1 个许可的添加剂（大多数食品分类都有法规限制的添加剂）
    assert data2["count"] >= 1, \
        f"食品分类 {code} 应至少有 1 个许可的添加剂，实际 {data2['count']}"

    # 验证列名包含期望的字段
    assert "name_zh" in data2["columns"], "应返回 Chemical 的 name_zh（中文名）"
