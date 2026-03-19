from typing import List


def merge(
    vector_results: List[tuple[str, float]],  # (chunk_id, distance)，distance 越小越好
    bm25_results: List[tuple[str, float]],    # (chunk_id, bm25_score)，越大越好
    k: int = 60,
    max_results: int = 40,
) -> List[str]:
    """
    使用 RRF（Reciprocal Rank Fusion）合并向量检索和 BM25 检索结果。

    - vector_results 按 distance 升序排名（distance 越小 rank 越小）
    - bm25_results 按 score 降序排名（score 越大 rank 越小）
    - RRF score = 1/(k + rank_vector) + 1/(k + rank_bm25)
    - 只在一路出现的 chunk，另一路 rank 视为 len(该路结果) + 1（惩罚）
    - 返回按 RRF 分降序的 chunk_id 列表，最多 max_results 条
    """
    if not vector_results and not bm25_results:
        return []

    # 构建 rank 映射（rank 从 1 开始）
    # vector_results 已按 distance 升序，排名越小越好
    vector_sorted = sorted(vector_results, key=lambda x: x[1])
    vector_rank: dict[str, int] = {
        chunk_id: rank + 1
        for rank, (chunk_id, _) in enumerate(vector_sorted)
    }

    # bm25_results 按 score 降序
    bm25_sorted = sorted(bm25_results, key=lambda x: x[1], reverse=True)
    bm25_rank: dict[str, int] = {
        chunk_id: rank + 1
        for rank, (chunk_id, _) in enumerate(bm25_sorted)
    }

    # 惩罚值：某路缺失时使用该路结果数量 + 1
    vector_penalty = len(vector_results) + 1
    bm25_penalty = len(bm25_results) + 1

    # 收集所有唯一 chunk_id
    all_chunk_ids = set(vector_rank.keys()) | set(bm25_rank.keys())

    # 计算 RRF 分
    rrf_scores: list[tuple[str, float]] = []
    for chunk_id in all_chunk_ids:
        rv = vector_rank.get(chunk_id, vector_penalty)
        rb = bm25_rank.get(chunk_id, bm25_penalty)
        score = 1.0 / (k + rv) + 1.0 / (k + rb)
        rrf_scores.append((chunk_id, score))

    # 按 RRF 分降序，取前 max_results
    rrf_scores.sort(key=lambda x: x[1], reverse=True)
    return [chunk_id for chunk_id, _ in rrf_scores[:max_results]]
