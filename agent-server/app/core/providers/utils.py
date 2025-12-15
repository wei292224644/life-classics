"""
模型提供者工具函数
提供便捷的验证、测试和管理功能
"""

import logging
from typing import Dict, List, Optional, Tuple
from app.core.config import settings
from app.core.providers.factory import ModelFactory

logger = logging.getLogger(__name__)


def check_provider_availability(
    provider_name: str,
    provider_type: str = "llm",
    provider_config: Optional[Dict] = None,
) -> Tuple[bool, str]:
    """
    检查提供者是否可用（包括依赖和配置）

    Args:
        provider_name: 提供者名称
        provider_type: 提供者类型，"llm" 或 "embedding"

    Returns:
        (是否可用, 消息)
    """
    provider_name = provider_name.lower()
    provider_type = provider_type.lower()

    try:
        # 检查提供者是否注册
        if provider_type == "llm":
            available = ModelFactory.list_available_llm_providers()
            if provider_name not in available:
                return False, f"提供者 '{provider_name}' 未注册。可用提供者: {', '.join(available)}"
        elif provider_type == "embedding":
            available = ModelFactory.list_available_embedding_providers()
            if provider_name not in available:
                return False, f"提供者 '{provider_name}' 未注册。可用提供者: {', '.join(available)}"
        else:
            return False, f"不支持的提供者类型: {provider_type}"

        # 验证配置
        ModelFactory.validate_provider_config(provider_name, provider_type)
        return True, f"提供者 '{provider_name}' ({provider_type}) 配置有效且可用"

    except ImportError as e:
        return False, f"提供者依赖未安装: {e}"
    except ValueError as e:
        return False, f"配置错误: {e}"
    except Exception as e:
        return False, f"检查失败: {e}"


def test_provider(
    provider_name: str,
    provider_type: str = "llm",
    provider_config: Optional[Dict] = None,
) -> Tuple[bool, str]:
    """
    测试提供者是否能正常工作

    Args:
        provider_name: 提供者名称
        provider_type: 提供者类型，"llm" 或 "embedding"

    Returns:
        (是否成功, 消息)
    """
    try:
        if provider_type == "llm":
            llm = ModelFactory.get_llm(provider_name, provider_config=provider_config)
            # 简单的测试调用（如果支持）
            logger.info(f"LLM 提供者 '{provider_name}' 实例创建成功")
            return True, f"LLM 提供者 '{provider_name}' 测试通过"
        elif provider_type == "embedding":
            embedding = ModelFactory.get_embedding(
                provider_name, provider_config=provider_config
            )
            logger.info(f"Embedding 提供者 '{provider_name}' 实例创建成功")
            return True, f"Embedding 提供者 '{provider_name}' 测试通过"
        else:
            return False, f"不支持的提供者类型: {provider_type}"
    except Exception as e:
        logger.error(f"测试提供者失败 ({provider_type}/{provider_name}): {e}")
        return False, f"测试失败: {e}"


def get_current_providers() -> Dict[str, str]:
    """
    获取当前配置的提供者

    Returns:
        包含当前 LLM 和 Embedding 提供者的字典
    """
    return {
        "llm": settings.LLM_PROVIDER.lower(),
        "embedding": settings.EMBEDDING_PROVIDER.lower(),
    }


def list_all_providers() -> Dict[str, List[str]]:
    """
    列出所有可用的提供者

    Returns:
        包含所有可用 LLM 和 Embedding 提供者的字典
    """
    return {
        "llm": ModelFactory.list_available_llm_providers(),
        "embedding": ModelFactory.list_available_embedding_providers(),
    }


def validate_all_providers() -> Dict[str, Dict[str, Tuple[bool, str]]]:
    """
    验证所有配置的提供者

    Returns:
        验证结果字典，格式: {provider_type: {provider_name: (is_valid, message)}}
    """
    results = {
        "llm": {},
        "embedding": {},
    }

    # 验证当前配置的提供者
    current_llm = settings.LLM_PROVIDER.lower()
    current_embedding = settings.EMBEDDING_PROVIDER.lower()

    results["llm"][current_llm] = check_provider_availability(current_llm, "llm")
    results["embedding"][current_embedding] = check_provider_availability(
        current_embedding, "embedding"
    )

    return results


def print_provider_status():
    """打印当前提供者状态（用于调试）"""
    print("\n" + "=" * 60)
    print("模型提供者状态")
    print("=" * 60)

    current = get_current_providers()
    print(f"\n当前配置:")
    print(f"  LLM: {current['llm']}")
    print(f"  Embedding: {current['embedding']}")

    print(f"\n可用提供者:")
    all_providers = list_all_providers()
    print(f"  LLM: {', '.join(all_providers['llm'])}")
    print(f"  Embedding: {', '.join(all_providers['embedding'])}")

    print(f"\n配置验证:")
    validation_results = validate_all_providers()
    for provider_type, providers in validation_results.items():
        for provider_name, (is_valid, message) in providers.items():
            status = "✓" if is_valid else "✗"
            print(f"  {status} {provider_type}/{provider_name}: {message}")

    print("=" * 60 + "\n")
