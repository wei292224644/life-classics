"""
Reranker：对候选文档按与 query 的相关性重排序。

使用 Qwen3-Reranker（因果语言模型），通过 yes/no token 的 logits 概率作为相关性分数。
模型名通过 settings.RERANKER_MODEL 配置，默认 Qwen/Qwen3-Reranker-0.6B。

懒加载：首次调用 get_reranker() 时才初始化模型，不在 import 时加载。
"""
from __future__ import annotations

from typing import List

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from api.config import settings

# Qwen3-Reranker 固定 prompt 格式
_PREFIX = (
    "<|im_start|>system\n"
    "根据提供的查询（Query）和指令（Instruct），判断文档（Document）是否满足要求。"
    "注意答案只能是'yes'或'no'。<|im_end|>\n"
    "<|im_start|>user\n"
)
_SUFFIX = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
_TASK = "根据网络搜索查询，检索能够回答查询的相关段落"
_MAX_LENGTH = 8192


class Reranker:
    def __init__(self) -> None:
        model_name = settings.RERANKER_MODEL
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, padding_side="left")
        self.model = AutoModelForCausalLM.from_pretrained(model_name).eval()

        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
        self.model = self.model.to(self.device)

        self._prefix_tokens = self.tokenizer.encode(_PREFIX, add_special_tokens=False)
        self._suffix_tokens = self.tokenizer.encode(_SUFFIX, add_special_tokens=False)
        self._token_false_id = self.tokenizer.convert_tokens_to_ids("no")
        self._token_true_id = self.tokenizer.convert_tokens_to_ids("yes")

    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5,
    ) -> List[tuple[int, float]]:
        """
        对文档列表按与 query 的相关性重排序。

        Args:
            query: 查询文本
            documents: 候选文档内容列表（纯文本）
            top_k: 返回条数

        Returns:
            按相关性降序排列的 (原始索引, 分数) 列表，长度为 min(top_k, len(documents))
        """
        if not documents:
            return []

        max_doc_len = _MAX_LENGTH - len(self._prefix_tokens) - len(self._suffix_tokens)
        pairs = [
            f"<Instruct>: {_TASK}\n<Query>: {query}\n<Document>: {doc}"
            for doc in documents
        ]

        inputs = self.tokenizer(
            pairs,
            padding=False,
            truncation="longest_first",
            return_attention_mask=False,
            max_length=max_doc_len,
        )
        for i, ids in enumerate(inputs["input_ids"]):
            inputs["input_ids"][i] = self._prefix_tokens + ids + self._suffix_tokens

        inputs = self.tokenizer.pad(
            inputs, padding=True, return_tensors="pt", max_length=_MAX_LENGTH
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            logits = self.model(**inputs).logits[:, -1, :]

        true_vec = logits[:, self._token_true_id]
        false_vec = logits[:, self._token_false_id]
        scores = torch.nn.functional.log_softmax(
            torch.stack([false_vec, true_vec], dim=1), dim=1
        )[:, 1].exp().tolist()

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


_reranker: Reranker | None = None


def get_reranker() -> Reranker:
    """懒加载单例，首次调用时初始化模型。"""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
