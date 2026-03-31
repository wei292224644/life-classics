import pytest
from worflow_parser_kb.rules import RulesStore


@pytest.fixture
def store(tmp_path):
    """使用默认规则初始化 RulesStore（复制到 tmp_path 以避免污染）"""
    return RulesStore(str(tmp_path))


# ── structure_types ───────────────────────────────────────────────────

def test_structure_types_contains_five_types(store):
    rules = store.get_content_type_rules()
    ids = [t["id"] for t in rules["structure_types"]]
    assert set(ids) == {"paragraph", "list", "table", "formula", "header"}, f"实际：{ids}"


def test_each_structure_type_has_description_and_examples(store):
    rules = store.get_content_type_rules()
    for t in rules["structure_types"]:
        assert "description" in t, f"{t['id']} 缺 description"
        assert "examples" in t and len(t["examples"]) >= 1, f"{t['id']} 缺 examples"


# ── semantic_types ────────────────────────────────────────────────────

def test_semantic_types_contains_eight_types(store):
    rules = store.get_content_type_rules()
    ids = [t["id"] for t in rules["semantic_types"]]
    assert set(ids) == {
        "metadata", "scope", "limit", "procedure",
        "material", "calculation", "definition", "amendment",
    }, f"实际：{ids}"


def test_each_semantic_type_has_description_and_examples(store):
    rules = store.get_content_type_rules()
    for t in rules["semantic_types"]:
        assert "description" in t, f"{t['id']} 缺 description"
        assert "examples" in t and len(t["examples"]) >= 1, f"{t['id']} 缺 examples"


# ── transform.by_semantic_type ────────────────────────────────────────

def test_transform_exists_for_all_semantic_types(store):
    rules = store.get_content_type_rules()
    transform_map = rules["transform"]["by_semantic_type"]
    for t in rules["semantic_types"]:
        assert t["id"] in transform_map, f"semantic_type '{t['id']}' 缺少 transform 配置"


def test_each_transform_has_strategy_and_non_empty_prompt_template(store):
    rules = store.get_content_type_rules()
    for sem_id, cfg in rules["transform"]["by_semantic_type"].items():
        assert "strategy" in cfg, f"{sem_id} 缺 strategy"
        assert cfg.get("prompt_template", ""), f"{sem_id} prompt_template 为空"


# ── get_transform_params ──────────────────────────────────────────────

def test_get_transform_params_by_semantic_type(store):
    params = store.get_transform_params("procedure")
    assert "strategy" in params
    assert "prompt_template" in params
    assert params["prompt_template"]


def test_get_transform_params_unknown_falls_back_to_plain_embed(store):
    params = store.get_transform_params("nonexistent_type")
    assert params["strategy"] == "plain_embed"


def test_get_transform_params_calculation_uses_formula_embed(store):
    params = store.get_transform_params("calculation")
    assert params["strategy"] == "formula_embed"


def test_get_transform_params_limit_uses_table_to_text(store):
    params = store.get_transform_params("limit")
    assert params["strategy"] == "table_to_text"


def test_limit_description_excludes_method_performance_metrics(store):
    rules = store.get_content_type_rules()
    limit = next(t for t in rules["semantic_types"] if t["id"] == "limit")
    desc = limit["description"]
    assert "不包括" in desc or "排除" in desc, (
        f"limit 描述必须含排除词，当前描述：{desc}"
    )
