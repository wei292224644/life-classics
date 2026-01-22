"""
Embedding 增强模块
在录入和检索时介入，提升向量检索的质量
"""

from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from app.core.config import settings
from app.core.llm import chat
from langchain_core.messages import HumanMessage, SystemMessage


class EmbeddingEnhancer:
    """
    Embedding 增强器
    在录入和检索时对内容进行预处理和增强
    """

    def __init__(
        self,
        enable_document_enhancement: bool = True,
        enable_query_enhancement: bool = True,
        provider_name: str = "dashscope",
        provider_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化 Embedding 增强器

        Args:
            enable_document_enhancement: 是否启用文档增强（录入时）
            enable_query_enhancement: 是否启用查询增强（检索时）
            provider_name: LLM 提供者名称
            provider_config: LLM 配置
        """
        self.enable_document_enhancement = enable_document_enhancement
        self.enable_query_enhancement = enable_query_enhancement
        self.provider_name = provider_name
        self.provider_config = provider_config or {"model": settings.QWEN_MODEL}

    def enhance_document(self, document: Document) -> Document:
        """
        增强文档内容（录入时调用）

        对文档内容进行预处理，添加关键词、同义词、上下文信息等，
        以提高向量检索的准确性

        Args:
            document: 原始文档

        Returns:
            增强后的文档
        """
        if not self.enable_document_enhancement:
            return document

        try:
            content = document.page_content
            metadata = document.metadata or {}

            # 提取关键信息
            content_type = metadata.get("content_type", "unknown")
            section_path = metadata.get("section_path", [])
            doc_title = metadata.get("doc_title", "")

            # 构建增强提示
            system_prompt = """你是一个文档内容增强专家。你的任务是为文档内容添加关键词和上下文信息，以提高向量检索的准确性。

要求：
1. 提取文档中的关键术语、概念、实体
2. 添加同义词和相关的表达方式
3. 保留原始内容不变
4. 以简洁的方式添加补充信息

输出格式：
原始内容

[关键词: 关键词1, 关键词2, ...]
[同义词: 同义词1, 同义词2, ...]
[上下文: 简要的上下文说明]
"""

            human_prompt = f"""文档类型: {content_type}
章节路径: {' > '.join(section_path) if section_path else '根目录'}
文档标题: {doc_title}

原始内容:
{content[:2000]}  # 限制长度避免 token 过多

请为这段内容添加关键词和上下文信息。"""

            enhanced_content = chat(
                messages=[
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_prompt),
                ],
                provider_name=self.provider_name,
                provider_config=self.provider_config,
            )

            # 将增强内容追加到原始内容
            final_content = f"{content}\n\n[增强信息]\n{enhanced_content}"

            # 创建增强后的文档
            enhanced_doc = Document(
                page_content=final_content,
                metadata=metadata,
            )

            return enhanced_doc

        except Exception as e:
            # 如果增强失败，返回原始文档
            print(f"警告: 文档增强失败: {e}，使用原始文档")
            return document

    def enhance_query(self, query: str) -> str:
        """
        增强查询内容（检索时调用）

        对用户查询进行扩展和重写，添加同义词、相关术语等，
        以提高检索的召回率和准确性

        Args:
            query: 原始查询

        Returns:
            增强后的查询
        """
        if not self.enable_query_enhancement:
            return query

        try:
            system_prompt = """你是一个查询增强专家。你的任务是为用户查询添加相关的关键词、同义词和表达方式，以提高向量检索的效果。

要求：
1. 识别查询中的核心概念和关键词
2. 添加同义词和相关表达
3. 保持查询的原始意图
4. 输出增强后的查询，格式简洁

输出格式：
增强后的查询（包含原始查询和补充的关键词、同义词）
"""

            human_prompt = f"""用户查询: {query}

请为这个查询添加相关的关键词和同义词，以提高检索效果。直接输出增强后的查询，不要添加解释。"""

            enhanced_query = chat(
                messages=[
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_prompt),
                ],
                provider_name=self.provider_name,
                provider_config=self.provider_config,
            )

            # 如果增强失败或返回空，使用原始查询
            if not enhanced_query or len(enhanced_query.strip()) < len(query):
                return query

            return enhanced_query.strip()

        except Exception as e:
            # 如果增强失败，返回原始查询
            print(f"警告: 查询增强失败: {e}，使用原始查询")
            return query

    def enhance_documents(self, documents: List[Document]) -> List[Document]:
        """
        批量增强文档列表

        Args:
            documents: 原始文档列表

        Returns:
            增强后的文档列表
        """
        if not self.enable_document_enhancement:
            return documents

        enhanced_docs = []
        for doc in documents:
            enhanced_doc = self.enhance_document(doc)
            enhanced_docs.append(enhanced_doc)

        return enhanced_docs


# 全局增强器实例
_enhancer: Optional[EmbeddingEnhancer] = None


def get_enhancer() -> EmbeddingEnhancer:
    """获取全局 Embedding 增强器实例"""
    global _enhancer
    if _enhancer is None:
        _enhancer = EmbeddingEnhancer(
            enable_document_enhancement=settings.ENABLE_DOCUMENT_ENHANCEMENT,
            enable_query_enhancement=settings.ENABLE_QUERY_ENHANCEMENT,
            provider_name=settings.EMBEDDING_ENHANCEMENT_PROVIDER,
            provider_config={
                "model": settings.EMBEDDING_ENHANCEMENT_MODEL,
                "temperature": settings.EMBEDDING_ENHANCEMENT_TEMPERATURE,
            },
        )
    return _enhancer


def enhance_document(document: Document) -> Document:
    """
    增强文档内容（便捷函数）

    Args:
        document: 原始文档

    Returns:
        增强后的文档
    """
    enhancer = get_enhancer()
    return enhancer.enhance_document(document)


def enhance_query(query: str) -> str:
    """
    增强查询内容（便捷函数）

    Args:
        query: 原始查询

    Returns:
        增强后的查询
    """
    enhancer = get_enhancer()
    return enhancer.enhance_query(query)


def enhance_documents(documents: List[Document]) -> List[Document]:
    """
    批量增强文档列表（便捷函数）

    Args:
        documents: 原始文档列表

    Returns:
        增强后的文档列表
    """
    enhancer = get_enhancer()
    return enhancer.enhance_documents(documents)
