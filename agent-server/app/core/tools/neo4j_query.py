"""
Neo4j 图查询工具：供 Agent 执行只读 Cypher 查询（文档/块关系等）。
"""

from langchain_core.tools import tool


@tool
def neo4j_query(query: str) -> str:
    """
    对知识图谱（Neo4j）执行只读 Cypher 查询，用于查询文档与块的关系等。

    Args:
        query: Cypher 查询字符串（仅支持只读，如 MATCH ... RETURN）

    Returns:
        查询结果摘要或错误信息
    """
    # 占位：后续接入 Neo4j 驱动执行只读查询
    return "Neo4j query not implemented yet. Configure Neo4j and implement in app.core.tools.neo4j_query."
