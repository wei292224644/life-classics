import os

import pytest

from app.core.parser_workflow.rules import RulesStore


@pytest.fixture
def rules_dir(tmp_path):
    return str(tmp_path)


def test_loads_defaults_when_files_missing(rules_dir):
    store = RulesStore(rules_dir)
    ct = store.get_content_type_rules()
    dt = store.get_doc_type_rules()
    assert len(ct["content_types"]) >= 4
    assert any(c["id"] == "table" for c in ct["content_types"])
    assert len(dt["doc_types"]) >= 3
    assert any(d["id"] == "single_additive" for d in dt["doc_types"])


def test_creates_files_on_disk_after_init(rules_dir):
    RulesStore(rules_dir)
    assert os.path.exists(os.path.join(rules_dir, "content_type_rules.json"))
    assert os.path.exists(os.path.join(rules_dir, "doc_type_rules.json"))


def test_append_new_content_type(rules_dir):
    store = RulesStore(rules_dir)
    new_type = {
        "id": "image_caption",
        "description": "图片说明文字",
        "transform": {"strategy": "preserve_as_is"},
    }
    store.append_content_type(new_type)
    store2 = RulesStore(rules_dir)
    ids = [c["id"] for c in store2.get_content_type_rules()["content_types"]]
    assert "image_caption" in ids


def test_append_new_doc_type(rules_dir):
    store = RulesStore(rules_dir)
    new_doc = {
        "id": "safety_assessment",
        "description": "食品安全风险评估报告",
        "detect_keywords": ["风险评估", "暴露量"],
        "detect_heading_patterns": ["风险特征描述"],
        "source": "llm",
    }
    store.append_doc_type(new_doc)
    store2 = RulesStore(rules_dir)
    ids = [d["id"] for d in store2.get_doc_type_rules()["doc_types"]]
    assert "safety_assessment" in ids


def test_reload_reflects_appended_rules(rules_dir):
    store = RulesStore(rules_dir)
    store.append_content_type(
        {
            "id": "code_block",
            "description": "代码块",
            "transform": {"strategy": "preserve_as_is"},
        }
    )
    store.reload()
    ids = [c["id"] for c in store.get_content_type_rules()["content_types"]]
    assert "code_block" in ids


def test_get_confidence_threshold_default(rules_dir):
    store = RulesStore(rules_dir)
    assert store.get_confidence_threshold() == 0.7


def test_get_transform_params_for_known_type(rules_dir):
    store = RulesStore(rules_dir)
    params = store.get_transform_params("table")
    assert params["strategy"] == "split_rows"


def test_get_transform_params_for_unknown_type_returns_plain(rules_dir):
    store = RulesStore(rules_dir)
    params = store.get_transform_params("nonexistent_type")
    assert params["strategy"] == "plain_embed"

