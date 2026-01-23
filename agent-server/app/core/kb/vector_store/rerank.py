"""
重排序（Rerank）模块
对从知识库检索到的内容进行重新排序，输出最相关的几条 chunk
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from langchain_core.documents import Document


@dataclass
class RerankedChunk:
    """重排序后的 chunk"""

    document: Document
    relevance_score: float
    relevance_reason: str


class Reranker:
    """
    重排序器
    使用 transformers 模型对检索结果进行相关性评分和重排序
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3-Reranker-0.6B",
        device: Optional[str] = None,
        max_length: int = 8192,
        task: str = "根据网络搜索查询，检索能够回答查询的相关段落",
    ):
        """
        初始化重排序器

        Args:
            model_name: transformers 模型名称或路径
            device: 设备（None 表示自动选择）
            max_length: 最大序列长度
            task: 重排序任务描述
        """
        self.model_name = model_name
        self.max_length = max_length
        self.task = task

        # 加载 tokenizer 和 model
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, padding_side="left"
        )
        self.model = AutoModelForCausalLM.from_pretrained(model_name).eval()

        # 设置设备
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        if self.device == "cuda":
            self.model = self.model.cuda()

        # 获取特殊 token ID
        self.token_false_id = self.tokenizer.convert_tokens_to_ids("no")
        self.token_true_id = self.tokenizer.convert_tokens_to_ids("yes")

        # 构建 prefix 和 suffix
        prefix = '<|im_start|>system\n根据提供的查询（Query）和指令（Instruct），判断文档（Document）是否满足要求。注意答案只能是"yes"或"no"。<|im_end|>\n<|im_start|>user\n'
        suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        self.prefix_tokens = self.tokenizer.encode(prefix, add_special_tokens=False)
        self.suffix_tokens = self.tokenizer.encode(suffix, add_special_tokens=False)

    def _format_instruction(self, instruction: str, query: str, doc: str) -> str:
        """
        格式化输入指令

        Args:
            instruction: 任务指令
            query: 查询文本
            doc: 文档文本

        Returns:
            格式化后的文本
        """
        return f"<Instruct>: {instruction}\n<Query>: {query}\n<Document>: {doc}"

    def _process_inputs(self, pairs: List[str]) -> Dict[str, torch.Tensor]:
        """
        处理输入文本对

        Args:
            pairs: 文本对列表

        Returns:
            处理后的输入字典
        """
        inputs = self.tokenizer(
            pairs,
            padding=False,
            truncation="longest_first",
            return_attention_mask=False,
            max_length=self.max_length
            - len(self.prefix_tokens)
            - len(self.suffix_tokens),
        )

        # 添加 prefix 和 suffix tokens
        for i, ele in enumerate(inputs["input_ids"]):
            inputs["input_ids"][i] = (
                self.prefix_tokens + ele + self.suffix_tokens
            )

        # 填充到相同长度
        inputs = self.tokenizer.pad(
            inputs, padding=True, return_tensors="pt", max_length=self.max_length
        )

        # 移动到设备
        for key in inputs:
            inputs[key] = inputs[key].to(self.model.device)

        return inputs

    @torch.no_grad()
    def _compute_logits(self, inputs: Dict[str, torch.Tensor]) -> List[float]:
        """
        计算相关性分数

        Args:
            inputs: 处理后的输入

        Returns:
            相关性分数列表
        """
        batch_scores = self.model(**inputs).logits[:, -1, :]
        true_vector = batch_scores[:, self.token_true_id]
        false_vector = batch_scores[:, self.token_false_id]
        batch_scores = torch.stack([false_vector, true_vector], dim=1)
        batch_scores = torch.nn.functional.log_softmax(batch_scores, dim=1)
        scores = batch_scores[:, 1].exp().tolist()
        return scores

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5,
    ) -> List[RerankedChunk]:
        """
        对检索结果进行重排序

        Args:
            query: 用户查询
            documents: 检索到的文档列表
            top_k: 返回前 k 个最相关的结果

        Returns:
            重排序后的 chunk 列表，按相关性从高到低排序
        """
        if not documents:
            return []

        try:
            # 提取文档内容
            doc_texts = []
            for doc in documents:
                content = doc.page_content
                # 限制长度避免 token 过多
                if len(content) > 2000:
                    content = content[:2000]
                doc_texts.append(content)

            # 格式化输入
            pairs = [
                self._format_instruction(self.task, query, doc_text)
                for doc_text in doc_texts
            ]

            # 处理输入
            inputs = self._process_inputs(pairs)

            # 计算分数
            scores = self._compute_logits(inputs)

            # 构建重排序结果
            reranked_chunks = []
            for doc, score in zip(documents, scores):
                reranked_chunks.append(
                    RerankedChunk(
                        document=doc,
                        relevance_score=float(score),
                        relevance_reason=f"模型评分: {score:.4f}",
                    )
                )

            # 按相关性分数排序（从高到低）
            reranked_chunks.sort(key=lambda x: x.relevance_score, reverse=True)

            # 返回前 top_k 个结果
            return reranked_chunks[:top_k]

        except Exception as e:
            # 如果模型评分失败，抛出异常
            print(f"模型重排序失败: {e}")
            raise


# 初始化全局 reranker 实例
reranker = Reranker()


def rerank_documents(
    query: str,
    documents: List[Document],
    top_k: int = 5,
) -> List[RerankedChunk]:
    """
    对检索到的文档进行重排序（便捷函数）

    Args:
        query: 用户查询
        documents: 检索到的文档列表
        top_k: 返回前 k 个最相关的结果

    Returns:
        重排序后的 chunk 列表，按相关性从高到低排序

    Example:
        >>> from app.core.kb.vector_store.vector_store import VectorStore
        >>> from app.core.kb.vector_store.rerank import rerank_documents
        >>>
        >>> vector_store = VectorStore()
        >>> documents = vector_store.search("β-胡萝卜素含量", top_k=10)
        >>> reranked = rerank_documents("β-胡萝卜素含量", documents, top_k=5)
        >>> for chunk in reranked:
        ...     print(f"分数: {chunk.relevance_score:.2f} - {chunk.document.page_content[:100]}")
    """
    return reranker.rerank(query, documents, top_k)


# ============================================================================
# 测试 Demo
# ============================================================================
if __name__ == "__main__":
    """
    测试重排序功能
    运行方式: python -m app.core.kb.vector_store.rerank
    """

    print("=" * 80)
    print("重排序模块测试 Demo")
    print("=" * 80)

    # 测试查询 1：关于β-胡萝卜素
    query1 = "β-胡萝卜素含量"
    documents1 = [
        Document(
            page_content="β-胡萝卜素是一种重要的维生素A前体，广泛存在于胡萝卜、南瓜、红薯等橙色蔬菜中。它在人体内可以转化为维生素A，对视力保护和免疫系统功能有重要作用。",
            metadata={"content_type": "definition"},
        ),
        Document(
            page_content="胡萝卜是一种根茎类蔬菜，含有丰富的β-胡萝卜素。每100克胡萝卜中约含有8-10毫克的β-胡萝卜素。胡萝卜可以生吃、煮熟或榨汁食用。",
            metadata={"content_type": "specification_table"},
        ),
        Document(
            page_content="今天天气很好，适合外出散步。公园里的花都开了，空气中弥漫着花香。",
            metadata={"content_type": "note"},
        ),
        Document(
            page_content="β-胡萝卜素在食品工业中常用作天然着色剂，其E编号为E160a。它不仅可以提供橙黄色，还具有一定的营养价值。在食品标签上，β-胡萝卜素通常被标注为天然色素。",
            metadata={"content_type": "scope"},
        ),
        Document(
            page_content="苹果是一种常见的水果，含有丰富的维生素C和膳食纤维。每天吃一个苹果有助于保持健康。",
            metadata={"content_type": "note"},
        ),
    ]

    print("\n" + "=" * 80)
    print("测试 1: β-胡萝卜素含量查询")
    print("=" * 80)
    print(f"\n查询: {query1}")
    print(f"\n原始文档数量: {len(documents1)}")

    # 使用模型进行重排序
    print("\n使用 transformers 模型进行重排序...")
    reranked1 = rerank_documents(
        query=query1,
        documents=documents1,
        top_k=5,
    )

    print(f"\n重排序结果（按相关性从高到低）:")
    print("-" * 80)
    for i, chunk in enumerate(reranked1, 1):
        print(f"\n{i}. 分数: {chunk.relevance_score:.4f}")
        print(f"   理由: {chunk.relevance_reason}")
        print(f"   内容类型: {chunk.document.metadata.get('content_type', 'unknown')}")
        print(f"   文档: {chunk.document.page_content[:100]}...")

    # 测试查询 2：关于人工智能
    query2 = "人工智能如何改进搜索结果？"
    documents2 = [
        Document(
            page_content="人工智能可用于从候选文本中重排序最相关内容。通过机器学习算法，搜索引擎可以理解用户意图，提供更准确的搜索结果。",
            metadata={"content_type": "definition"},
        ),
        Document(
            page_content="今天的天气很不错！适合外出散步和运动。",
            metadata={"content_type": "note"},
        ),
        Document(
            page_content="搜索引擎使用机器学习来提高相关性。深度学习模型可以分析查询和文档的语义相似度，从而改进搜索质量。",
            metadata={"content_type": "scope"},
        ),
        Document(
            page_content="人工智能技术在自然语言处理领域取得了重大突破，包括机器翻译、文本生成和情感分析等应用。",
            metadata={"content_type": "definition"},
        ),
    ]

    print("\n" + "=" * 80)
    print("测试 2: 人工智能搜索查询")
    print("=" * 80)
    print(f"\n查询: {query2}")
    print(f"\n原始文档数量: {len(documents2)}")

    # 使用模型进行重排序
    print("\n使用 transformers 模型进行重排序...")
    reranked2 = rerank_documents(
        query=query2,
        documents=documents2,
        top_k=3,
    )

    print(f"\n重排序结果（按相关性从高到低）:")
    print("-" * 80)
    for i, chunk in enumerate(reranked2, 1):
        print(f"\n{i}. 分数: {chunk.relevance_score:.4f}")
        print(f"   理由: {chunk.relevance_reason}")
        print(f"   内容类型: {chunk.document.metadata.get('content_type', 'unknown')}")
        print(f"   文档: {chunk.document.page_content[:100]}...")

    print("\n" + "=" * 80)
    print("✓ 所有测试完成！")
    print("=" * 80)
