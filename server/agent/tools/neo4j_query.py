"""
Neo4j 查询工具：对 GB2760_2024 知识图谱执行只读 Cypher 查询。
"""

import json
import re

from agent.tools.neo4j_client import get_database, get_driver


async def neo4j_query(query: str) -> str:
    """
    对 GB2760_2024 知识图谱执行只读 Cypher 查询，返回 JSON 字符串。

    Args:
        query: Cypher 查询语句

    Returns:
        成功：JSON 字符串 {"columns": [...], "rows": [[...], ...], "count": N}
        失败：可读错误字符串（不抛异常）
    """
    # 若无 LIMIT 则自动追加
    if not re.search(r"\bLIMIT\b", query, re.IGNORECASE):
        query = query.rstrip() + " LIMIT 50"

    try:
        driver = get_driver()
        with driver.session(database=get_database()) as session:
            records = session.execute_read(lambda tx: list(tx.run(query)))

        if records:
            columns = list(records[0].keys())
            rows = [list(r.values()) for r in records]
        else:
            columns = []
            rows = []

        return json.dumps(
            {"columns": columns, "rows": rows, "count": len(records)},
            ensure_ascii=False,
        )
    except Exception as e:
        return f"Neo4j 查询失败：{e}"
