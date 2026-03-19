"""
PostgreSQL 查询工具：供 Agent 执行只读 SQL 查询。
"""

from langchain_core.tools import tool


@tool
def postgres_query(query: str) -> str:
    """
    对 PostgreSQL 执行只读 SQL 查询。

    Args:
        query: SQL 查询字符串（仅支持 SELECT 等只读操作）

    Returns:
        查询结果摘要或错误信息
    """
    # 占位：后续接入 asyncpg 等执行只读 SQL
    return "PostgreSQL query not implemented yet. Configure POSTGRES_URI and implement in app.core.tools.postgres_query."
