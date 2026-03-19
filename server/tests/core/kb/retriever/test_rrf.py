import pytest
from kb.retriever.rrf import merge


class TestMergeBasic:
    def test_both_empty(self):
        """两路都为空时返回空列表"""
        result = merge([], [])
        assert result == []

    def test_vector_empty(self):
        """向量结果为空时，BM25 结果按排名返回"""
        bm25 = [("a", 10.0), ("b", 8.0), ("c", 5.0)]
        result = merge([], bm25)
        # bm25 ranks: a=1, b=2, c=3; vector penalty = 0+1=1
        # a: 1/(60+1) + 1/(60+1) = 2/61
        # b: 1/(60+1) + 1/(60+2) = 1/61 + 1/62
        # c: 1/(60+1) + 1/(60+3) = 1/61 + 1/63
        # a > b > c
        assert result == ["a", "b", "c"]

    def test_bm25_empty(self):
        """BM25 结果为空时，向量结果按排名返回"""
        vector = [("x", 0.1), ("y", 0.2), ("z", 0.3)]
        result = merge(vector, [])
        # vector ranks: x=1, y=2, z=3; bm25 penalty = 0+1=1
        # x: 1/(60+1) + 1/(60+1) = 2/61
        # y: 1/(60+2) + 1/(60+1) = 1/62 + 1/61
        # z: 1/(60+3) + 1/(60+1) = 1/63 + 1/61
        # x > y > z
        assert result == ["x", "y", "z"]

    def test_normal_merge(self):
        """两路都有结果时正常合并"""
        vector = [("a", 0.1), ("b", 0.2), ("c", 0.3)]
        bm25 = [("b", 10.0), ("a", 8.0), ("d", 5.0)]
        result = merge(vector, bm25)

        # vector ranks: a=1, b=2, c=3
        # bm25 ranks: b=1, a=2, d=3
        # "a": 1/(60+1) + 1/(60+2) ≈ 0.01639 + 0.01613 = 0.03252
        # "b": 1/(60+2) + 1/(60+1) ≈ 0.01613 + 0.01639 = 0.03252
        # "c": 1/(60+3) + 1/(60+4) ≈ 0.01587 + 0.01563 = 0.03150  bm25 rank = 3+1=4
        # "d": 1/(60+4) + 1/(60+3) ≈ 0.01563 + 0.01587 = 0.03150  vector rank = 3+1=4

        # a 和 b 分数相同（对称），c 和 d 分数相同
        assert set(result[:2]) == {"a", "b"}
        assert set(result[2:4]) == {"c", "d"}
        assert len(result) == 4

    def test_deduplication(self):
        """同一 chunk_id 在两路都出现时只在结果中出现一次"""
        vector = [("a", 0.1), ("b", 0.2)]
        bm25 = [("a", 9.0), ("b", 7.0)]
        result = merge(vector, bm25)
        # 结果中 a 和 b 各只出现一次
        assert len(result) == 2
        assert result.count("a") == 1
        assert result.count("b") == 1

    def test_max_results(self):
        """max_results 限制返回数量"""
        vector = [(f"v{i}", float(i)) for i in range(20)]
        bm25 = [(f"b{i}", float(20 - i)) for i in range(20)]
        result = merge(vector, bm25, max_results=10)
        assert len(result) == 10

    def test_max_results_default(self):
        """默认 max_results=40"""
        vector = [(f"v{i}", float(i)) for i in range(30)]
        bm25 = [(f"b{i}", float(30 - i)) for i in range(30)]
        result = merge(vector, bm25)
        assert len(result) == 40

    def test_returns_list_of_strings(self):
        """返回值类型正确"""
        vector = [("a", 0.1)]
        bm25 = [("b", 5.0)]
        result = merge(vector, bm25)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)


class TestMergeRankCalculation:
    def test_penalty_rank_for_missing_vector(self):
        """只在 BM25 出现的 chunk，vector rank = len(vector_results) + 1"""
        vector = [("a", 0.1), ("b", 0.2)]  # len=2, vector_penalty=3
        bm25 = [("c", 10.0)]               # c 不在 vector 中；len=1, bm25_penalty=2

        result = merge(vector, bm25)

        # vector ranks: a=1, b=2
        # bm25 ranks: c=1
        # a: vector=1, bm25=penalty=1+1=2  → 1/(60+1) + 1/(60+2) ≈ 0.03252
        # b: vector=2, bm25=penalty=1+1=2  → 1/(60+2) + 1/(60+2) ≈ 0.03226
        # c: vector=penalty=2+1=3, bm25=1  → 1/(60+3) + 1/(60+1) ≈ 0.03243
        # order: a > c > b
        assert result[0] == "a"
        assert result[1] == "c"
        assert result[2] == "b"

    def test_penalty_rank_for_missing_bm25(self):
        """只在向量结果出现的 chunk，bm25 rank = len(bm25_results) + 1"""
        vector = [("c", 0.1)]               # c 不在 bm25 中；len=1, vector_penalty=2
        bm25 = [("a", 10.0), ("b", 8.0)]   # len=2, bm25_penalty=3

        result = merge(vector, bm25)

        # vector ranks: c=1
        # bm25 ranks: a=1, b=2
        # a: vector=penalty=1+1=2, bm25=1  → 1/(60+2) + 1/(60+1) ≈ 0.03252
        # b: vector=penalty=1+1=2, bm25=2  → 1/(60+2) + 1/(60+2) ≈ 0.03226
        # c: vector=1, bm25=penalty=2+1=3  → 1/(60+1) + 1/(60+3) ≈ 0.03243
        # order: a > c > b
        assert result[0] == "a"
        assert result[1] == "c"
        assert result[2] == "b"

    def test_custom_k(self):
        """自定义 k 值"""
        vector = [("a", 0.1)]
        bm25 = [("a", 5.0)]
        result = merge(vector, bm25, k=10)
        # a: 1/(10+1) + 1/(10+1) = 2/11 ≈ 0.182
        assert result == ["a"]

    def test_rrf_scores_symmetric(self):
        """当两个 chunk 在两路的排名互换时，RRF 分应相同"""
        vector = [("a", 0.1), ("b", 0.2)]
        bm25 = [("b", 10.0), ("a", 8.0)]
        result = merge(vector, bm25)
        # a: vector=1, bm25=2 → 1/61 + 1/62
        # b: vector=2, bm25=1 → 1/62 + 1/61
        # 分数相同，两个都应该在结果中
        assert set(result) == {"a", "b"}

    def test_single_chunk_in_both(self):
        """单个 chunk 同时在两路出现"""
        vector = [("a", 0.5)]
        bm25 = [("a", 3.0)]
        result = merge(vector, bm25)
        assert result == ["a"]

    def test_vector_unsorted_input(self):
        """即使 vector_results 输入不是按 distance 排序的，也能正确处理"""
        # distance 越小越好，所以 b(0.1) < a(0.5)
        vector = [("a", 0.5), ("b", 0.1)]  # 故意乱序
        bm25 = []
        result = merge(vector, bm25)
        # b distance=0.1 → rank=1, a distance=0.5 → rank=2
        # bm25 penalty = 0+1 = 1
        # b: 1/(60+1) + 1/(60+1) = 2/61
        # a: 1/(60+2) + 1/(60+1) = 1/62 + 1/61
        # b > a
        assert result[0] == "b"
        assert result[1] == "a"
