"""
模型提供者工厂
统一管理 LLM 和 Embedding 提供者的创建和选择
支持在不同场景下使用不同的提供者
"""

import logging
from typing import Any, Optional, Dict, List
from app.core.config import settings
from app.core.providers.base import BaseLLMProvider, BaseEmbeddingProvider
from app.core.providers.dashscope import (
    DashScopeLLMProvider,
    DashScopeEmbeddingProvider,
)
from app.core.providers.ollama import OllamaLLMProvider, OllamaEmbeddingProvider
from app.core.providers.openrouter import (
    OpenRouterLLMProvider,
    OpenRouterEmbeddingProvider,
)

logger = logging.getLogger(__name__)


class ModelFactory:
    """模型提供者工厂类"""

    # 注册的 LLM 提供者
    _llm_providers: Dict[str, type] = {
        "dashscope": DashScopeLLMProvider,
        "ollama": OllamaLLMProvider,
        "openrouter": OpenRouterLLMProvider,
    }

    # 注册的 Embedding 提供者
    _embedding_providers: Dict[str, type] = {
        "dashscope": DashScopeEmbeddingProvider,
        "ollama": OllamaEmbeddingProvider,
        "openrouter": OpenRouterEmbeddingProvider,
    }

    # 缓存实例
    _llm_instances: Dict[str, Any] = {}
    _embedding_instances: Dict[str, Any] = {}

    @classmethod
    def register_llm_provider(cls, name: str, provider_class: type):
        """
        注册自定义 LLM 提供者

        Args:
            name: 提供者名称
            provider_class: 提供者类（继承自 BaseLLMProvider）
        """
        if not issubclass(provider_class, BaseLLMProvider):
            raise TypeError(f"提供者类必须继承自 BaseLLMProvider: {provider_class}")
        cls._llm_providers[name.lower()] = provider_class

    @classmethod
    def register_embedding_provider(cls, name: str, provider_class: type):
        """
        注册自定义 Embedding 提供者

        Args:
            name: 提供者名称
            provider_class: 提供者类（继承自 BaseEmbeddingProvider）
        """
        if not issubclass(provider_class, BaseEmbeddingProvider):
            raise TypeError(
                f"提供者类必须继承自 BaseEmbeddingProvider: {provider_class}"
            )
        cls._embedding_providers[name.lower()] = provider_class

    @classmethod
    def get_llm_provider_config(cls, provider_name: str) -> Dict:
        """
        获取指定 LLM 提供者的配置

        Args:
            provider_name: 提供者名称

        Returns:
            配置字典
        """
        provider_name = provider_name.lower()
        config = {}

        if provider_name == "dashscope":
            config = {
                "api_key": settings.DASHSCOPE_API_KEY,
                "model": settings.QWEN_MODEL,
                "temperature": 0.7,
                "max_tokens": 2048,
            }
        elif provider_name == "ollama":
            config = {
                "model": settings.OLLAMA_MODEL,
                "base_url": settings.OLLAMA_BASE_URL,
                "temperature": 0.7,
                "request_timeout": 120.0,
            }
        elif provider_name == "openrouter":
            config = {
                "api_key": settings.OPENROUTER_API_KEY,
                "model": settings.OPENROUTER_MODEL,
                "temperature": 0.7,
                "max_tokens": 2048,
            }

        return config

    @classmethod
    def get_embedding_provider_config(cls, provider_name: str) -> Dict:
        """
        获取指定 Embedding 提供者的配置

        Args:
            provider_name: 提供者名称

        Returns:
            配置字典
        """
        provider_name = provider_name.lower()
        config = {}

        if provider_name == "dashscope":
            config = {
                "api_key": settings.DASHSCOPE_API_KEY,
                "model": settings.QWEN_EMBEDDING_MODEL,
            }
        elif provider_name == "ollama":
            config = {
                "model": settings.OLLAMA_EMBEDDING_MODEL,
                "base_url": settings.OLLAMA_BASE_URL,
            }
        elif provider_name == "openrouter":
            config = {
                "api_key": settings.OPENROUTER_API_KEY,
                "model": settings.OPENROUTER_EMBEDDING_MODEL,
            }

        return config

    @classmethod
    def create_llm_provider(
        cls,
        provider_name: Optional[str] = None,
        provider_config: Optional[Dict] = None,
    ) -> BaseLLMProvider:
        """
        创建 LLM 提供者实例

        Args:
            provider_name: 提供者名称，如果为 None 则使用配置中的默认值

        Returns:
            LLM 提供者实例

        Raises:
            ValueError: 如果提供者名称不支持
            ImportError: 如果提供者依赖未安装
        """
        if provider_name is None:
            provider_name = settings.LLM_PROVIDER.lower()

        provider_name = provider_name.lower()

        if provider_name not in cls._llm_providers:
            available = ", ".join(cls._llm_providers.keys())
            raise ValueError(
                f"不支持的 LLM 提供者: {provider_name}。" f"支持的提供者: {available}"
            )

        try:
            provider_class = cls._llm_providers[provider_name]
            default_config = cls.get_llm_provider_config(provider_name)
            # 支持终端/调用方传入覆盖配置
            merged_config = {**default_config, **(provider_config or {})}
            provider = provider_class(merged_config)
            logger.info(f"成功创建 LLM 提供者: {provider_name}")
            return provider
        except ImportError as e:
            logger.error(f"创建 LLM 提供者失败 ({provider_name}): {e}")
            raise
        except Exception as e:
            logger.error(f"创建 LLM 提供者时发生错误 ({provider_name}): {e}")
            raise

    @classmethod
    def create_embedding_provider(
        cls,
        provider_name: Optional[str] = None,
        provider_config: Optional[Dict] = None,
    ) -> BaseEmbeddingProvider:
        """
        创建 Embedding 提供者实例

        Args:
            provider_name: 提供者名称，如果为 None 则使用配置中的默认值

        Returns:
            Embedding 提供者实例

        Raises:
            ValueError: 如果提供者名称不支持
            ImportError: 如果提供者依赖未安装
        """
        if provider_name is None:
            provider_name = settings.EMBEDDING_PROVIDER.lower()

        provider_name = provider_name.lower()

        if provider_name not in cls._embedding_providers:
            available = ", ".join(cls._embedding_providers.keys())
            raise ValueError(
                f"不支持的 Embedding 提供者: {provider_name}。"
                f"支持的提供者: {available}"
            )

        try:
            provider_class = cls._embedding_providers[provider_name]
            default_config = cls.get_embedding_provider_config(provider_name)
            merged_config = {**default_config, **(provider_config or {})}
            provider = provider_class(merged_config)
            logger.info(f"成功创建 Embedding 提供者: {provider_name}")
            return provider
        except ImportError as e:
            logger.error(f"创建 Embedding 提供者失败 ({provider_name}): {e}")
            raise
        except Exception as e:
            logger.error(f"创建 Embedding 提供者时发生错误 ({provider_name}): {e}")
            raise

    @classmethod
    def get_llm(
        cls,
        provider_name: Optional[str] = None,
        provider_config: Optional[Dict] = None,
    ) -> Any:
        """
        获取 LLM 实例（单例模式）

        Args:
            provider_name: 提供者名称，如果为 None 则使用配置中的默认值
            provider_config: 运行时配置覆盖，例如自定义模型名称、温度等

        Returns:
            LLM 实例（兼容 LlamaIndex）

        Raises:
            ValueError: 如果提供者名称不支持或配置无效
            ImportError: 如果提供者依赖未安装
        """
        if provider_name is None:
            provider_name = settings.LLM_PROVIDER.lower()
        else:
            provider_name = provider_name.lower()

        # 构建缓存键：如果提供了 provider_config，需要包含配置信息
        # 使用配置的哈希值作为缓存键的一部分，确保不同配置使用不同的实例
        import hashlib
        import json
        
        if provider_config:
            # 将配置字典转换为可哈希的字符串
            config_str = json.dumps(provider_config, sort_keys=True)
            config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]
            cache_key = f"{provider_name}_{config_hash}"
        else:
            cache_key = provider_name

        # 检查缓存
        if cache_key not in cls._llm_instances:
            logger.info(f"初始化 LLM 实例: {provider_name} (配置: {provider_config})")
            provider = cls.create_llm_provider(
                provider_name, provider_config=provider_config
            )
            cls._llm_instances[cache_key] = provider.get_instance()
            logger.info(f"LLM 实例已缓存: {cache_key}")
        else:
            logger.debug(f"使用缓存的 LLM 实例: {cache_key}")

        return cls._llm_instances[cache_key]

    @classmethod
    def get_embedding(
        cls,
        provider_name: Optional[str] = None,
        provider_config: Optional[Dict] = None,
    ) -> Any:
        """
        获取 Embedding 实例（单例模式）

        Args:
            provider_name: 提供者名称，如果为 None 则使用配置中的默认值

        Returns:
            Embedding 实例（兼容 LlamaIndex）

        Raises:
            ValueError: 如果提供者名称不支持或配置无效
            ImportError: 如果提供者依赖未安装
        """
        if provider_name is None:
            provider_name = settings.EMBEDDING_PROVIDER.lower()
        else:
            provider_name = provider_name.lower()

        # 使用 provider_name 作为缓存键
        if provider_name not in cls._embedding_instances:
            logger.info(f"初始化 Embedding 实例: {provider_name}")
            provider = cls.create_embedding_provider(
                provider_name, provider_config=provider_config
            )
            cls._embedding_instances[provider_name] = provider.get_instance()
            logger.info(f"Embedding 实例已缓存: {provider_name}")
        else:
            logger.debug(f"使用缓存的 Embedding 实例: {provider_name}")

        return cls._embedding_instances[provider_name]

    @classmethod
    def clear_cache(cls):
        """清除所有缓存的实例"""
        logger.info("清除所有缓存的模型实例")
        cls._llm_instances.clear()
        cls._embedding_instances.clear()

    @classmethod
    def list_available_llm_providers(cls) -> List[str]:
        """
        列出所有可用的 LLM 提供者

        Returns:
            提供者名称列表
        """
        return list(cls._llm_providers.keys())

    @classmethod
    def list_available_embedding_providers(cls) -> List[str]:
        """
        列出所有可用的 Embedding 提供者

        Returns:
            提供者名称列表
        """
        return list(cls._embedding_providers.keys())

    @classmethod
    def validate_provider_config(
        cls, provider_name: str, provider_type: str = "llm"
    ) -> bool:
        """
        验证提供者配置是否有效

        Args:
            provider_name: 提供者名称
            provider_type: 提供者类型，"llm" 或 "embedding"

        Returns:
            配置是否有效

        Raises:
            ValueError: 如果提供者名称不支持
        """
        provider_name = provider_name.lower()
        provider_type = provider_type.lower()

        try:
            if provider_type == "llm":
                if provider_name not in cls._llm_providers:
                    raise ValueError(
                        f"不支持的 LLM 提供者: {provider_name}。"
                        f"支持的提供者: {', '.join(cls._llm_providers.keys())}"
                    )
                config = cls.get_llm_provider_config(provider_name)
                provider_class = cls._llm_providers[provider_name]
                provider = provider_class(config)
                return provider.validate_config()
            elif provider_type == "embedding":
                if provider_name not in cls._embedding_providers:
                    raise ValueError(
                        f"不支持的 Embedding 提供者: {provider_name}。"
                        f"支持的提供者: {', '.join(cls._embedding_providers.keys())}"
                    )
                config = cls.get_embedding_provider_config(provider_name)
                provider_class = cls._embedding_providers[provider_name]
                provider = provider_class(config)
                return provider.validate_config()
            else:
                raise ValueError(
                    f"不支持的提供者类型: {provider_type}。支持的类型: 'llm', 'embedding'"
                )
        except Exception as e:
            logger.error(f"验证提供者配置失败 ({provider_type}/{provider_name}): {e}")
            raise
