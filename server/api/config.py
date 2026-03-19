"""
API配置模块 - 从全局config模块重新导出，保持向后兼容。
"""

from config import settings, Settings

__all__ = ["settings", "Settings"]