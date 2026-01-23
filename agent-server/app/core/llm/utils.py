"""
模型提供者缓存工具
只负责缓存管理，不负责创建实例
"""

import hashlib
import json
from typing import Any, Optional, Dict

# 统一缓存字典
_cache: Dict[str, Any] = {}


def get_cache_key(provider_name: str, config: Optional[Dict] = None) -> str:
    """
    生成缓存键

    Args:
        provider_name: 提供者名称
        config: 配置字典

    Returns:
        缓存键字符串
    """
    config = config or {}
    config_str = json.dumps(config, sort_keys=True)
    config_hash = hashlib.md5(config_str.encode()).hexdigest()[:8]
    return f"{provider_name}_{config_hash}"


def get_cache(cache_key: str) -> Optional[Any]:
    """
    获取缓存的实例

    Args:
        cache_key: 缓存键

    Returns:
        缓存的实例，如果不存在则返回 None
    """
    return _cache.get(cache_key)


def set_cache(cache_key: str, instance: Any):
    """
    设置缓存的实例

    Args:
        cache_key: 缓存键
        instance: 要缓存的实例
    """
    _cache[cache_key] = instance


def clear_cache():
    """清除所有缓存的实例"""
    _cache.clear()
