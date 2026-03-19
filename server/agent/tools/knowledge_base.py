"""
知识库检索工具：供 Agent 基于混合检索（向量 + BM25 + Rerank）查询国家标准等内容。
"""

from langchain_core.tools import tool

from kb.retriever import search


@tool
async def knowledge_base(query: str, top_k: int = 5) -> str:
    """
    从知识库中检索与查询最相关的文档片段（国家标准等）。适合回答与已入库文档相关的问题。

    Args:
        query: 检索查询文本
        top_k: 返回条数，默认 5

    Returns:
        格式化后的检索结果文本，包含内容与来源信息
    """
    try:
        results = await search(query, top_k=top_k)
    except Exception as e:
        return f"知识库检索失败: {e!s}"

    if not results:
        return "未检索到相关文档。"

    lines = []
    for i, r in enumerate(results, 1):
        part = f"[{i}] 标准号: {r['standard_no']}\n内容: {r['raw_content']}\n相关度: {r['score']:.2f}"
        lines.append(part)

    return "\n\n".join(lines)
