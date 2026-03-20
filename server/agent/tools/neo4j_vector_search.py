"""
Neo4j 向量搜索工具：对 GB2760_2024 图谱节点进行语义搜索，将模糊表达解析为精确实体。
"""

import json

import requests

from config import settings
from agent.tools.neo4j_client import get_driver, get_database


# 节点标签 → 向量索引名映射
INDEX_MAP: dict[str, str] = {
    "Chemical": "chemical_embedding",
    "Function": "function_embedding",
    "FoodCategory": "foodcategory_embedding",
    "Flavoring": "flavoring_embedding",
    "ProcessingAid": "processingaid_embedding",
    "Enzyme": "enzyme_embedding",
    "Organism": "organism_embedding",
}

# 节点标签 → 需要提取的属性字段
RETURN_FIELDS: dict[str, list[str]] = {
    "Chemical": ["id", "name_zh", "name_en"],
    "FoodCategory": ["code", "name"],
    "Function": ["name"],
    "Flavoring": ["code", "name_zh", "name_en"],
    "ProcessingAid": ["code", "name_zh"],
    "Enzyme": ["code", "name_zh"],
    "Organism": ["name_zh", "name_en"],
}


def _get_embedding(text: str) -> list[float]:
    """
    调用 Ollama /api/embed 将文本转为向量。

    Args:
        text: 要嵌入的文本

    Returns:
        float 列表

    Raises:
        RuntimeError: 请求失败时抛出
    """
    url = f"{settings.OLLAMA_BASE_URL}/api/embed"
    try:
        r = requests.post(url, json={"model": "qwen3-embedding:4b", "input": text}, timeout=30)
        r.raise_for_status()
        return r.json()["embeddings"][0]
    except Exception as e:
        raise RuntimeError(f"Ollama 嵌入请求失败：{e}") from e


async def neo4j_vector_search(text: str, node_label: str, top_k: int = 5) -> str:
    """
    语义搜索 GB2760_2024 图谱节点，将模糊表达解析为精确实体。

    Args:
        text:       搜索文本（如"菜罐头"）
        node_label: 节点类型，支持：Chemical / Function / FoodCategory /
                    Flavoring / ProcessingAid / Enzyme / Organism
        top_k:      返回节点数，默认 5

    Returns:
        成功：JSON 字符串 {"node_label": ..., "results": [{...,"score":0.92},...], "count": N}
        失败：可读错误字符串
    """
    # 1. 校验 node_label
    if node_label not in INDEX_MAP:
        supported = "、".join(INDEX_MAP.keys())
        return f"不支持的节点类型：{node_label}。支持的节点类型为：{supported}"

    # 2. 获取嵌入向量
    try:
        embedding = _get_embedding(text)
    except RuntimeError as e:
        return str(e)

    # 3. 执行向量查询
    try:
        index_name = INDEX_MAP[node_label]
        fields = RETURN_FIELDS[node_label]

        driver = get_driver()
        with driver.session(database=get_database()) as session:
            def _query(tx):
                result = tx.run(
                    "CALL db.index.vector.queryNodes($index_name, $top_k, $embedding) "
                    "YIELD node, score "
                    "RETURN node, score",
                    index_name=index_name,
                    top_k=top_k,
                    embedding=embedding,
                )
                return list(result)

            records = session.execute_read(_query)

        # 4. 提取字段，组装结果列表
        results = []
        for record in records:
            node = record["node"]
            score = record["score"]
            item = {field: node[field] for field in fields if node[field] is not None}
            item["score"] = score
            results.append(item)

        return json.dumps(
            {"node_label": node_label, "results": results, "count": len(results)},
            ensure_ascii=False,
        )

    except Exception as e:
        return f"Neo4j 向量搜索失败：{e}"
