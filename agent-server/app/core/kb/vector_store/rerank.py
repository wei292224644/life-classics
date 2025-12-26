"""
重排序（Rerank）模块
对从知识库检索到的内容进行重新排序，输出最相关的几条 chunk
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from langchain_core.documents import Document

from app.core.llm import chat
from app.core.config import settings
from langchain_core.messages import HumanMessage, SystemMessage


@dataclass
class RerankedChunk:
    """重排序后的 chunk"""
    document: Document
    relevance_score: float
    relevance_reason: str


class Reranker:
    """
    重排序器
    使用 LLM 对检索结果进行相关性评分和重排序
    """

    def __init__(
        self,
        provider_name: str = "dashscope",
        provider_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化重排序器

        Args:
            provider_name: LLM 提供者名称
            provider_config: LLM 配置
        """
        self.provider_name = provider_name
        self.provider_config = provider_config or {"model": settings.DASHSCOPE_MODEL}

    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5,
        use_llm: bool = True,
    ) -> List[RerankedChunk]:
        """
        对检索结果进行重排序

        Args:
            query: 用户查询
            documents: 检索到的文档列表
            top_k: 返回前 k 个最相关的结果
            use_llm: 是否使用 LLM 进行重排序（True）或使用简单方法（False）

        Returns:
            重排序后的 chunk 列表，按相关性从高到低排序
        """
        if not documents:
            return []

        if use_llm:
            return self._rerank_with_llm(query, documents, top_k)
        else:
            return self._rerank_simple(query, documents, top_k)

    def _rerank_with_llm(
        self, query: str, documents: List[Document], top_k: int
    ) -> List[RerankedChunk]:
        """
        使用 LLM 进行重排序

        Args:
            query: 用户查询
            documents: 检索到的文档列表
            top_k: 返回前 k 个结果

        Returns:
            重排序后的 chunk 列表
        """
        # 如果文档数量较少，直接返回
        if len(documents) <= top_k:
            return [
                RerankedChunk(
                    document=doc,
                    relevance_score=1.0 - (i / len(documents)),
                    relevance_reason="检索结果",
                )
                for i, doc in enumerate(documents)
            ]

        # 构建文档列表用于 LLM 评分
        doc_list = []
        for i, doc in enumerate(documents):
            # 提取文档内容
            content = doc.page_content[:1000]  # 限制长度避免 token 过多
            metadata = doc.metadata or {}
            
            # 构建文档描述
            section_path = metadata.get("section_path", [])
            section_path_str = " > ".join(section_path) if section_path else "根目录"
            content_type = metadata.get("content_type", "unknown")
            
            doc_info = {
                "index": i,
                "section_path": section_path_str,
                "content_type": str(content_type),
                "content_preview": content[:500],  # 预览前500字符
            }
            doc_list.append(doc_info)

        # 构建 LLM prompt
        system_prompt = """你是一个专业的文档相关性评估专家。你的任务是根据用户查询，对检索到的文档进行相关性评分。

评分标准：
- 1.0: 完全相关，直接回答用户问题
- 0.8-0.9: 高度相关，包含重要信息
- 0.6-0.7: 中等相关，部分相关
- 0.4-0.5: 低相关，间接相关
- 0.0-0.3: 不相关

请为每个文档评分，并简要说明评分理由。"""

        user_prompt = f"""用户查询：{query}

检索到的文档列表：
{json.dumps(doc_list, ensure_ascii=False, indent=2)}

请为每个文档进行相关性评分（0.0-1.0），并返回 JSON 格式的结果：
{{
  "scores": [
    {{"index": 0, "score": 0.9, "reason": "评分理由"}},
    {{"index": 1, "score": 0.7, "reason": "评分理由"}},
    ...
  ]
}}

只返回 JSON，不要其他内容。"""

        try:
            # 调用 LLM 进行评分
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
            
            response = chat(
                messages=messages,
                provider_name=self.provider_name,
                provider_config=self.provider_config,
            )

            # 解析 LLM 返回的评分结果
            scores_dict = self._parse_llm_response(response, len(documents))
            
            # 构建重排序结果
            reranked_chunks = []
            for i, doc in enumerate(documents):
                score_info = scores_dict.get(i, {"score": 0.0, "reason": "未评分"})
                reranked_chunks.append(
                    RerankedChunk(
                        document=doc,
                        relevance_score=score_info["score"],
                        relevance_reason=score_info["reason"],
                    )
                )

            # 按相关性分数排序（从高到低）
            reranked_chunks.sort(key=lambda x: x.relevance_score, reverse=True)

            # 返回前 top_k 个结果
            return reranked_chunks[:top_k]

        except Exception as e:
            # 如果 LLM 评分失败，回退到简单方法
            print(f"LLM 重排序失败，使用简单方法: {e}")
            return self._rerank_simple(query, documents, top_k)

    def _parse_llm_response(
        self, response: str, num_docs: int
    ) -> Dict[int, Dict[str, Any]]:
        """
        解析 LLM 返回的评分结果

        Args:
            response: LLM 返回的文本
            num_docs: 文档数量

        Returns:
            评分字典，key 为文档索引，value 为 {"score": float, "reason": str}
        """
        scores_dict = {}
        
        try:
            # 尝试提取 JSON
            # 移除可能的 markdown 代码块标记
            response = response.strip()
            if response.startswith("```"):
                # 移除代码块标记
                lines = response.split("\n")
                response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
            
            # 解析 JSON
            result = json.loads(response)
            
            if "scores" in result:
                for score_item in result["scores"]:
                    index = score_item.get("index", -1)
                    if 0 <= index < num_docs:
                        scores_dict[index] = {
                            "score": float(score_item.get("score", 0.0)),
                            "reason": score_item.get("reason", "无理由"),
                        }
        except Exception as e:
            print(f"解析 LLM 响应失败: {e}")
            # 如果解析失败，为所有文档设置默认分数
            for i in range(num_docs):
                scores_dict[i] = {"score": 0.5, "reason": "解析失败，使用默认分数"}

        # 确保所有文档都有分数
        for i in range(num_docs):
            if i not in scores_dict:
                scores_dict[i] = {"score": 0.0, "reason": "未评分"}

        return scores_dict

    def _rerank_simple(
        self, query: str, documents: List[Document], top_k: int
    ) -> List[RerankedChunk]:
        """
        使用简单方法进行重排序（基于关键词匹配和元数据）

        Args:
            query: 用户查询
            documents: 检索到的文档列表
            top_k: 返回前 k 个结果

        Returns:
            重排序后的 chunk 列表
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_chunks = []

        for doc in documents:
            content = doc.page_content.lower()
            metadata = doc.metadata or {}
            
            # 计算关键词匹配分数
            content_words = set(content.split())
            matched_words = query_words.intersection(content_words)
            keyword_score = len(matched_words) / max(len(query_words), 1)

            # 内容类型权重（某些类型可能更重要）
            content_type = metadata.get("content_type", "")
            type_weight = 1.0
            if content_type in ["scope", "definition", "specification_table"]:
                type_weight = 1.2
            elif content_type in ["note", "metadata"]:
                type_weight = 0.8

            # 综合分数
            relevance_score = min(keyword_score * type_weight, 1.0)

            scored_chunks.append(
                RerankedChunk(
                    document=doc,
                    relevance_score=relevance_score,
                    relevance_reason=f"关键词匹配: {len(matched_words)}/{len(query_words)}",
                )
            )

        # 按分数排序
        scored_chunks.sort(key=lambda x: x.relevance_score, reverse=True)

        return scored_chunks[:top_k]


def rerank_documents(
    query: str,
    documents: List[Document],
    top_k: int = 5,
    use_llm: bool = True,
    provider_name: str = "dashscope",
    provider_config: Optional[Dict[str, Any]] = None,
) -> List[RerankedChunk]:
    """
    对检索到的文档进行重排序（便捷函数）

    Args:
        query: 用户查询
        documents: 检索到的文档列表
        top_k: 返回前 k 个最相关的结果
        use_llm: 是否使用 LLM 进行重排序
        provider_name: LLM 提供者名称
        provider_config: LLM 配置

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
    reranker = Reranker(provider_name=provider_name, provider_config=provider_config)
    return reranker.rerank(query, documents, top_k, use_llm=use_llm)

