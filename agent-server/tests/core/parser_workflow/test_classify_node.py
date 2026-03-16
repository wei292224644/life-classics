from __future__ import annotations

import pytest

from app.core.parser_workflow.rules import RulesStore, RULES_DIR


@pytest.fixture
def store(tmp_path):
    """使用默认规则初始化 RulesStore（复制到 tmp_path 以避免污染）"""
    return RulesStore(str(tmp_path))


# ── standard_header 规则 ──────────────────────────────────────────────


def test_standard_header_description_excludes_preface(store):
    """standard_header 的 description 不应包含"前言"字样"""
    rules = store.get_content_type_rules()
    ct_map = {ct["id"]: ct for ct in rules["content_types"]}
    assert "standard_header" in ct_map
    desc = ct_map["standard_header"]["description"]
    assert "前言" not in desc, f"standard_header description 不应含'前言'，实际：{desc!r}"


def test_standard_header_has_no_action_field(store):
    """standard_header 条目不应有多余的 action 字段"""
    rules = store.get_content_type_rules()
    ct_map = {ct["id"]: ct for ct in rules["content_types"]}
    assert "action" not in ct_map["standard_header"], "standard_header 不应有 action 字段"


def test_standard_header_prompt_template_is_complete(store):
    """standard_header 的 prompt_template 不应是截断的字符串"""
    rules = store.get_content_type_rules()
    ct_map = {ct["id"]: ct for ct in rules["content_types"]}
    pt = ct_map["standard_header"]["transform"]["prompt_template"]
    # 合法的 prompt_template 应以换行符结束（约定）
    assert pt.endswith("\n"), f"prompt_template 疑似截断，结尾：{pt[-20:]!r}"


# ── preface 规则 ──────────────────────────────────────────────────────


def test_preface_content_type_exists(store):
    """content_type_rules.json 中应存在 preface 类型"""
    rules = store.get_content_type_rules()
    ids = [ct["id"] for ct in rules["content_types"]]
    assert "preface" in ids, f"未找到 preface 类型，现有：{ids}"


def test_preface_transform_params_use_plain_embed(store):
    """preface 的 transform strategy 应为 plain_embed"""
    params = store.get_transform_params("preface")
    assert params["strategy"] == "plain_embed", f"实际 strategy：{params['strategy']!r}"


def test_preface_description_mentions_no_split(store):
    """preface 的 description 应说明内部列表不拆分"""
    rules = store.get_content_type_rules()
    ct_map = {ct["id"]: ct for ct in rules["content_types"]}
    desc = ct_map["preface"]["description"]
    assert "不拆分" in desc, f"description 未说明不拆分，实际：{desc!r}"
