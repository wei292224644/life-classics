"""
SkillLoader 单元测试：从目录加载 .md 文件并按文件名排序拼接。
"""
import os
import tempfile

import pytest

from agent.skill_loader import load_skills


def test_load_skills_returns_concatenated_content(tmp_path):
    """按文件名排序拼接所有 .md 文件内容"""
    (tmp_path / "02_routing.md").write_text("routing content", encoding="utf-8")
    (tmp_path / "01_role.md").write_text("role content", encoding="utf-8")
    (tmp_path / "03_format.md").write_text("format content", encoding="utf-8")

    result = load_skills(str(tmp_path))

    assert "role content" in result
    assert "routing content" in result
    assert "format content" in result
    # 顺序：01 -> 02 -> 03
    assert result.index("role content") < result.index("routing content")
    assert result.index("routing content") < result.index("format content")


def test_load_skills_ignores_non_md_files(tmp_path):
    """非 .md 文件应被忽略"""
    (tmp_path / "01_role.md").write_text("role content", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("should be ignored", encoding="utf-8")

    result = load_skills(str(tmp_path))

    assert "role content" in result
    assert "should be ignored" not in result


def test_load_skills_empty_dir_returns_empty_string(tmp_path):
    """空目录返回空字符串"""
    result = load_skills(str(tmp_path))
    assert result == ""


def test_load_skills_default_dir_exists():
    """DEFAULT_SKILLS_DIR 常量存在且包含 food-safety"""
    from agent.skill_loader import DEFAULT_SKILLS_DIR
    assert isinstance(DEFAULT_SKILLS_DIR, str)
    assert "food-safety" in DEFAULT_SKILLS_DIR