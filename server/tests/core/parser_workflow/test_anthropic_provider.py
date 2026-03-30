"""anthropic provider 单元测试。"""
from __future__ import annotations

from config import Settings


def test_anthropic_config_defaults():
    """ANTHROPIC_API_KEY 和 ANTHROPIC_BASE_URL 默认为空字符串。"""
    s = Settings()
    assert s.ANTHROPIC_API_KEY == ""
    assert s.ANTHROPIC_BASE_URL == ""
