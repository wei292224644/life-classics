"""
知识库切分策略模块
支持多种切分策略：text、table、heading、structured、parent_child

使用工厂模式统一调度各种切分策略
"""

from typing import List, Dict, Callable, Optional

from .text_strategy import split_text
from .table_strategy import split_table
from .heading_strategy import split_heading
from .structured_strategy import split_structured
from .parent_child_strategy import split_parent_child
from app.core.document_chunk import DocumentChunk


class SplitStrategyFactory:
    """切分策略工厂类 - 统一调度各种切分策略"""

    # 策略注册表：策略名称 -> 策略函数
    _strategies: Dict[str, Callable] = {
        "text": split_text,
        "table": split_table,
        "heading": split_heading,
        "structured": split_structured,
        "parent_child": split_parent_child,
    }

    @classmethod
    def register_strategy(cls, name: str, strategy_func: Callable) -> None:
        """
        注册新的切分策略

        Args:
            name: 策略名称
            strategy_func: 策略函数，必须接受 documents 和 **kwargs 参数
        """
        cls._strategies[name] = strategy_func

    @classmethod
    def get_strategy(cls, name: str) -> Optional[Callable]:
        """
        获取指定的策略函数

        Args:
            name: 策略名称

        Returns:
            策略函数，如果不存在则返回 None
        """
        return cls._strategies.get(name)

    @classmethod
    def list_strategies(cls) -> List[str]:
        """
        列出所有已注册的策略名称

        Returns:
            策略名称列表
        """
        return list(cls._strategies.keys())

    @classmethod
    def split(
        cls, strategy_name: str, documents: List[DocumentChunk], **kwargs
    ) -> List[DocumentChunk]:
        """
        统一的策略调度方法

        Args:
            strategy_name: 策略名称（text、table、heading、structured、parent_child）
            documents: 待切分的 DocumentChunk 列表
            **kwargs: 传递给策略函数的其他参数

        Returns:
            切分后的 DocumentChunk 列表

        Raises:
            ValueError: 如果策略名称不存在
            TypeError: 如果文档类型不是 DocumentChunk
        """
        # 获取策略函数
        strategy_func = cls._strategies.get(strategy_name)
        if strategy_func is None:
            available_strategies = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"未知的策略名称 '{strategy_name}'。"
                f"可用的策略: {available_strategies}"
            )

        # 检查文档类型
        if not documents:
            return documents

        # 验证所有文档都是 DocumentChunk 类型
        if not isinstance(documents[0], DocumentChunk):
            raise TypeError(
                f"策略 '{strategy_name}' 需要 DocumentChunk 类型，"
                f"但收到 {type(documents[0]).__name__}"
            )

        result = strategy_func(documents, **kwargs)
        return result


def split_documents(
    strategy_name: str, documents: List[DocumentChunk], **kwargs
) -> List[DocumentChunk]:
    """
    统一的文档切分接口（便捷函数）

    Args:
        strategy_name: 策略名称（text、table、heading、structured、parent_child）
        documents: 待切分的 DocumentChunk 列表
        **kwargs: 传递给策略函数的其他参数

    Returns:
        切分后的 DocumentChunk 列表

    Example:
        >>> from app.core.kb.strategy import split_documents
        >>> chunks = split_documents("text", document_chunks, chunk_size=1024)
        >>> chunks = split_documents("structured", document_chunks)
    """
    return SplitStrategyFactory.split(strategy_name, documents, **kwargs)


# 导出所有策略函数和工厂类
__all__ = [
    "split_text",
    "split_table",
    "split_heading",
    "split_structured",
    "split_parent_child",
    "SplitStrategyFactory",
    "split_documents",
]
