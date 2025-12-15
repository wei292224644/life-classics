"""
模型提供者抽象基类
定义 LLM 和 Embedding 提供者的标准接口
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseLLMProvider(ABC):
    """LLM 提供者抽象基类"""

    def __init__(self, config: dict):
        """
        初始化 LLM 提供者
        
        Args:
            config: 提供者配置字典
        """
        self.config = config
        self._instance: Optional[Any] = None

    @abstractmethod
    def create_instance(self) -> Any:
        """
        创建 LLM 实例
        
        Returns:
            LLM 实例（兼容 LlamaIndex）
        """
        pass

    def get_instance(self) -> Any:
        """
        获取 LLM 实例（单例模式）
        
        Returns:
            LLM 实例
        """
        if self._instance is None:
            self._instance = self.create_instance()
        return self._instance

    @abstractmethod
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            配置是否有效
        """
        pass


class BaseEmbeddingProvider(ABC):
    """Embedding 提供者抽象基类"""

    def __init__(self, config: dict):
        """
        初始化 Embedding 提供者
        
        Args:
            config: 提供者配置字典
        """
        self.config = config
        self._instance: Optional[Any] = None

    @abstractmethod
    def create_instance(self) -> Any:
        """
        创建 Embedding 实例
        
        Returns:
            Embedding 实例（兼容 LlamaIndex）
        """
        pass

    def get_instance(self) -> Any:
        """
        获取 Embedding 实例（单例模式）
        
        Returns:
            Embedding 实例
        """
        if self._instance is None:
            self._instance = self.create_instance()
        return self._instance

    @abstractmethod
    def validate_config(self) -> bool:
        """
        验证配置是否有效
        
        Returns:
            配置是否有效
        """
        pass
