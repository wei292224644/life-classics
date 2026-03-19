# tests/core/parser_workflow/test_prompt_templates.py
"""验证 content_type_rules.json 中各 semantic_type 的 prompt_template 符合设计规范。

这些测试是配置驱动的：直接读取 JSON 文件，检查关键规则词是否存在。
每个测试对应设计文档中的一项关键设计决策，尤其是幻觉风险防控规则。
"""
import json
from pathlib import Path

RULES_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "app/core/parser_workflow/rules/content_type_rules.json"
)


def _load():
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def _prompt(rules: dict, semantic_type: str) -> str:
    return rules["transform"]["by_semantic_type"][semantic_type]["prompt_template"]


# ── 结构完整性 ─────────────────────────────────────────────────────────

def test_json_valid_and_has_transform_section():
    """JSON 可解析且包含 transform.by_semantic_type 节点"""
    rules = _load()
    assert "transform" in rules
    assert "by_semantic_type" in rules["transform"]


def test_all_eight_semantic_types_present():
    """8 种 semantic_type 均有对应的 transform_params"""
    rules = _load()
    by_type = rules["transform"]["by_semantic_type"]
    expected = {"metadata", "scope", "limit", "procedure", "material", "calculation", "definition", "amendment"}
    assert set(by_type.keys()) == expected


def test_all_prompts_are_non_placeholder():
    """所有 prompt_template 不再是通用占位符"""
    rules = _load()
    placeholder = "请将以下内容转化为规范化的陈述文本，保留所有原始信息："
    for stype, params in rules["transform"]["by_semantic_type"].items():
        prompt = params["prompt_template"].strip()
        assert prompt != placeholder, (
            f"{stype} 的 prompt_template 仍是占位符。实际内容：{prompt[:100]}"
        )


# ── limit：幻觉防控 ───────────────────────────────────────────────────

def test_limit_prompt_restores_html_entities():
    """limit prompt 应要求还原 HTML 实体编码（&lt; 等），防止符号失真"""
    prompt = _prompt(_load(), "limit")
    assert "&lt;" in prompt, "应包含 HTML 实体示例 &lt;"


def test_limit_prompt_category_label_only_when_explicit():
    """limit prompt 中类别标注规则应包含 fallback（无法确定时不强制添加）"""
    prompt = _prompt(_load(), "limit")
    assert "无法" in prompt or "若无法" in prompt, (
        f"类别标注应有 fallback 条件，防止 LLM 猜测指标类别。实际内容：{prompt[:100]}"
    )


def test_limit_prompt_preserves_comparison_symbols():
    """limit prompt 应明确要求保留限量符号（≤、<、≥ 等）"""
    prompt = _prompt(_load(), "limit")
    assert "≤" in prompt or "限量符号" in prompt


# ── calculation：幻觉防控 ─────────────────────────────────────────────

def test_calculation_prompt_usage_description_has_fallback():
    """calculation prompt 的用途描述规则应有 fallback（无法确定时跳过）"""
    prompt = _prompt(_load(), "calculation")
    assert "无法从原文确定" in prompt, (
        f"用途概括应有 fallback，防止 LLM 猜测被测物质名称。实际内容：{prompt[:100]}"
    )


def test_calculation_prompt_skip_produces_no_output():
    """calculation prompt 跳过步骤时不得输出任何解释性文字。
    必须明确要求'直接从第2步开始输出'且'禁止输出任何解释'，
    防止 LLM 将内部推理（如'计算对象未在原文中明确给出'）泄漏到最终 content。
    """
    prompt = _prompt(_load(), "calculation")
    assert "直接从第2步开始输出" in prompt, (
        "应包含'直接从第2步开始输出'，确保 LLM 不输出跳过说明。"
    )
    assert "禁止输出任何解释" in prompt, (
        "应包含'禁止输出任何解释'，防止推理过程泄漏到 content。"
    )


def test_calculation_prompt_preserves_latex_block():
    """calculation prompt 应要求保留原始 LaTeX 块公式不变"""
    prompt = _prompt(_load(), "calculation")
    assert "$$" in prompt and "不做任何修改" in prompt


# ── scope & amendment：标准号幻觉防控 ────────────────────────────────

def test_scope_prompt_prohibits_standard_no_guessing():
    """scope prompt 的标准号替换规则应禁止猜测"""
    prompt = _prompt(_load(), "scope")
    assert "不得猜测" in prompt or "猜测或补全" in prompt, (
        f"应禁止 LLM 猜测标准号。实际内容：{prompt[:100]}"
    )


def test_amendment_prompt_prohibits_standard_no_guessing():
    """amendment prompt 的标准号替换规则应禁止猜测（与 scope 保持一致）"""
    prompt = _prompt(_load(), "amendment")
    assert "不得猜测" in prompt or "猜测或补全" in prompt


# ── procedure：跨节引用处理 ───────────────────────────────────────────

def test_procedure_prompt_preserves_cross_ref_numbers():
    """procedure prompt 应要求保留章节编号引用，禁止展开猜测"""
    prompt = _prompt(_load(), "procedure")
    assert "引用编号" in prompt


def test_procedure_prompt_converts_inline_latex():
    """procedure prompt 应要求将 LaTeX inline 转为可读文本"""
    prompt = _prompt(_load(), "procedure")
    assert "$" in prompt and ("°C" in prompt or "mathrm" in prompt or "min" in prompt)


# ── definition：指代替换范围 ──────────────────────────────────────────

def test_definition_prompt_handles_block_formula():
    """definition prompt 应包含块公式处理规则"""
    prompt = _prompt(_load(), "definition")
    assert "块公式" in prompt or "$$" in prompt


# ── material：LaTeX inline 清洁 ──────────────────────────────────────

def test_material_prompt_converts_inline_latex():
    """material prompt 应要求将内联 LaTeX 转为可读文本"""
    prompt = _prompt(_load(), "material")
    assert "$" in prompt and ("mol/L" in prompt or "LaTeX" in prompt)


# ── amendment：破折号列表清洁 ─────────────────────────────────────────

def test_amendment_prompt_cleans_dash_list():
    """amendment prompt 应处理中文标准的 '——' 列表格式"""
    prompt = _prompt(_load(), "amendment")
    assert "——" in prompt


# ── metadata：纯标准号/纯标题行 ───────────────────────────────────────

def test_metadata_prompt_handles_pure_standard_no():
    """metadata prompt 应对纯标准号或纯标题行直接原样输出"""
    prompt = _prompt(_load(), "metadata")
    assert "原样输出" in prompt


def test_calculation_prompt_forbids_variable_description_rewrite():
    """calculation prompt 应明确包含'逐字'或'不得改写'以约束变量说明忠实性。"""
    prompt = _prompt(_load(), "calculation")
    assert "逐字" in prompt or "不得改写" in prompt, (
        f"calculation prompt 应明确禁止改写变量说明，需含'逐字'或'不得改写'。实际内容：{prompt}"
    )


def test_calculation_prompt_variable_desc_must_come_from_original():
    """calculation prompt 应明确要求变量说明文字来自原文（不得自行补全空白）。"""
    prompt = _prompt(_load(), "calculation")
    assert "原文" in prompt and "变量说明" in prompt, (
        f"calculation prompt 应包含'原文'和'变量说明'，禁止 LLM 补全空白变量。实际内容：{prompt}"
    )


def test_definition_semantic_type_must_contain_exclusion_clause():
    """definition 的语义描述必须含有明确排除词（'不包括'或'排除'），
    防止 LLM 将检测特征、光谱特性等错误匹配为术语定义。"""
    rules = _load()
    defn = next(t for t in rules["semantic_types"] if t["id"] == "definition")
    desc = defn["description"]
    assert "不包括" in desc or "排除" in desc, (
        f"definition 描述必须含排除词（'不包括'或'排除'），当前描述：{desc}"
    )


def test_definition_prompt_outputs_verbatim_for_non_definition():
    """definition prompt 对无明确"X是指Y"格式的内容应原样输出（不强套模板）。"""
    prompt = _prompt(_load(), "definition")
    assert "否则" in prompt and "原样输出" in prompt, (
        f"definition prompt 应有 else 分支：否则直接原样输出，不强套定义格式。实际内容：{prompt}"
    )


def test_amendment_prompt_renders_inline_latex():
    """amendment prompt 应包含内联 LaTeX 渲染规则，防止修改单 content 含原始 LaTeX"""
    prompt = _prompt(_load(), "amendment")
    assert ("LaTeX" in prompt or "$" in prompt) and ("转化" in prompt or "渲染" in prompt or "可读" in prompt), (
        f"amendment prompt 应包含 LaTeX inline 渲染规则。实际内容：{prompt}"
    )


def test_calculation_prompt_preserves_variable_name_before_dash():
    """formula_embed prompt 必须明确保留变量名字母/符号（X、C、m 等）在——之前"""
    prompt = _prompt(_load(), "calculation")
    assert "变量名" in prompt and "严禁丢弃" in prompt, (
        f"calculation prompt 应含'变量名'和'严禁丢弃'，当前内容：{prompt}"
    )


def test_calculation_prompt_handles_multiline_dash_format():
    """formula_embed prompt 应提到多短横线格式（LaTeX 渲染产物 X - - - - -）"""
    prompt = _prompt(_load(), "calculation")
    assert "短横线" in prompt, (
        f"calculation prompt 应提及多短横线格式，当前内容：{prompt}"
    )


def test_limit_semantic_type_excludes_method_performance():
    rules = _load()
    limit = next(t for t in rules["semantic_types"] if t["id"] == "limit")
    desc = limit["description"]
    assert ("不包括" in desc or "排除" in desc), (
        f"limit 描述必须含排除词，当前描述：{desc}"
    )
    assert "检测限" in desc or "灵敏度" in desc, (
        f"limit 描述排除词必须点名检测限/灵敏度，当前描述：{desc}"
    )


def test_definition_semantic_type_includes_method_performance():
    rules = _load()
    defn = next(t for t in rules["semantic_types"] if t["id"] == "definition")
    all_text = defn["description"] + " ".join(defn.get("examples", []))
    assert "检测限" in all_text or "灵敏度" in all_text or "定量限" in all_text, (
        f"definition 语义描述或示例中应包含检测限/定量限/灵敏度，当前：{all_text}"
    )


def test_metadata_semantic_type_covers_preface_changes():
    """metadata 的示例中应包含前言变更格式（如"——增加了"），
    以引导 LLM 将前言变更列表归为 metadata 而非 limit/procedure。"""
    rules = _load()
    meta = next(t for t in rules["semantic_types"] if t["id"] == "metadata")
    examples = " ".join(meta.get("examples", []))
    assert "增加了" in examples or "删除了" in examples or "修改了" in examples, (
        f"metadata examples 应包含前言变更示例（增加了/删除了/修改了）。当前: {examples}"
    )
