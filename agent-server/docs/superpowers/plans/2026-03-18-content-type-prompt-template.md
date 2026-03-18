# content_type_rules prompt_template 更新 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `content_type_rules.json` 中 8 种 semantic_type 的 `prompt_template` 从通用占位符升级为针对 RAG 向量检索优化的专属指令。

**Architecture:** 纯配置文件改动，不涉及代码逻辑修改。先写验证测试覆盖关键规则要求，再更新 JSON 使测试通过，最后运行完整测试套件确认无回归。

**Tech Stack:** Python/pytest（测试），JSON（配置）

> **JSON 转义注意事项**：JSON 文件中单个反斜杠必须写为 `\\`。代码块中出现的 `\\mathrm`、`\\circ` 等，在 JSON 源文件中即为两个字符（`\\`），解析后得到 `\mathrm`（有效 LaTeX）。每个 Task 末尾的 `python3 -c "import json; json.load(...)"` 验证步骤会立即暴露转义错误。

**Spec:** `agent-server/docs/superpowers/specs/2026-03-18-content-type-prompt-template-design.md`

---

## 涉及文件

| 操作 | 文件 |
|---|---|
| 新建（测试） | `tests/core/parser_workflow/test_prompt_templates.py` |
| 修改（配置） | `app/core/parser_workflow/rules/content_type_rules.json` |

---

## 背景说明

`transform_node` 通过以下方式构造 LLM prompt（`transform_node.py:25-30`）：

```python
prompt = f"""
按照以下提示词，处理原文本。
{transform_params["prompt_template"]}

原文本：
{content}
"""
```

`prompt_template` 直接拼入 LLM 调用。`transform_params` 通过 `RulesStore.get_transform_params(semantic_type)` 读取 `content_type_rules.json` 中 `transform.by_semantic_type` 节点。

---

### Task 1: 编写 prompt_template 内容验证测试

**Files:**
- Create: `tests/core/parser_workflow/test_prompt_templates.py`

- [ ] **Step 1: 编写测试文件**

```python
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
        assert params["prompt_template"].strip() != placeholder, (
            f"{stype} 的 prompt_template 仍是占位符"
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
        "类别标注应有 fallback 条件，防止 LLM 猜测指标类别"
    )


def test_limit_prompt_preserves_comparison_symbols():
    """limit prompt 应明确要求保留限量符号（≤、<、≥ 等）"""
    prompt = _prompt(_load(), "limit")
    assert "≤" in prompt or "限量符号" in prompt


# ── calculation：幻觉防控 ─────────────────────────────────────────────

def test_calculation_prompt_usage_description_has_fallback():
    """calculation prompt 的用途描述规则应有 fallback（无法确定时跳过）"""
    prompt = _prompt(_load(), "calculation")
    assert "无法从原文确定" in prompt or "跳过" in prompt, (
        "用途概括应有 fallback，防止 LLM 猜测被测物质名称"
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
        "应禁止 LLM 猜测标准号"
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
```

- [ ] **Step 2: 确认测试在当前状态下处于红色阶段**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_prompt_templates.py -v
```

期望：只有 `test_json_valid_and_has_transform_section` 和 `test_all_eight_semantic_types_present` 通过，其余（含 `test_all_prompts_are_non_placeholder`）均 FAIL。若结构性测试以外的测试全部 PASS，说明测试逻辑有误，需检查。

- [ ] **Step 3: 提交测试文件**

```bash
git add agent-server/tests/core/parser_workflow/test_prompt_templates.py
git commit -m "test: add prompt_template content validation tests for 8 semantic types"
```

---

### Task 2: 更新 `limit` 和 `calculation` 的 prompt_template（高扩展）

**Files:**
- Modify: `app/core/parser_workflow/rules/content_type_rules.json`

- [ ] **Step 1: 更新 `limit` 的 prompt_template**

将 `transform.by_semantic_type.limit.prompt_template` 改为：

```
将以下技术指标内容（HTML 表格、Markdown 表格或文字描述）转化为完整陈述文本。\n\n1. 若为表格，将每一个指标行转化为一条独立陈述句，格式为"[指标名称]的要求为[限量值或范围][单位]"；示例："铅(Pb)的重金属限量要求为 ≤5.0 mg/kg。"\n2. 若表格内容中可明确判断指标类别（如表头行含"感官要求"、"理化指标"、"微生物指标"等字样），在每条陈述后补充该类别标注；若无法从原文确定，仅输出指标陈述，不强制添加类别标注。\n3. 表格底部的脚注（a、b 等）和"注"包含重要附加条件，须以"备注："开头单独输出，不得省略。\n4. 严格保留所有数值、限量符号（≤、<、≥、~、±）、单位，禁止任何改动；HTML 实体编码（&lt; &gt; &amp;）须还原为原始符号。\n5. 若内容为文字描述，直接转化为完整独立陈述句，保留所有数值和百分比。
```

- [ ] **Step 2: 更新 `calculation` 的 prompt_template**

将 `transform.by_semantic_type.calculation.prompt_template` 改为：

```
将以下计算公式及变量说明转化为可检索的混合文本。\n\n1. 若原文或其章节标题中明确给出了计算对象（如"A.3.4 硫酸酯含量的计算"或"硫酸酯的质量分数 w₁，按式(A.1)计算"），在最前面用一句话概括计算用途，须包含被测物质名称；若无法从原文确定计算对象，跳过此步，不得猜测。\n2. 保留原始 LaTeX 块公式（$$...$$）完整，不做任何修改。\n3. 将变量说明中的内联 LaTeX（如 $m_1$、$\\mathrm{SO}_4$）转化为可读符号（m₁、SO₄），保留"——"格式的变量说明列表。\n4. 严格禁止修改公式中的任何变量名、系数、运算符或数值。
```

- [ ] **Step 3: 验证 JSON 格式有效**

```bash
cd agent-server && python3 -c "import json; json.load(open('app/core/parser_workflow/rules/content_type_rules.json'))" && echo "JSON valid"
```

期望输出：`JSON valid`

- [ ] **Step 4: 运行高扩展类型的测试**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_prompt_templates.py -v -k "limit or calculation"
```

期望：相关测试全部 PASS

- [ ] **Step 5: 提交**

```bash
git add agent-server/app/core/parser_workflow/rules/content_type_rules.json
git commit -m "feat(rules): update limit and calculation prompt_templates with RAG-optimized instructions"
```

---

### Task 3: 更新 `procedure`、`material`、`definition`、`scope` 的 prompt_template（中扩展）

**Files:**
- Modify: `app/core/parser_workflow/rules/content_type_rules.json`

- [ ] **Step 1: 更新 `procedure` 的 prompt_template**

```
将以下操作步骤转化为完整陈述文本。\n\n1. 将内联 LaTeX（$...$）中的数值和单位转化为可读文本（如 $80^{\\circ}C$ → 80°C，$15\\mathrm{min}$ → 15 min，$7.5\\mathrm{g}$ → 7.5 g）。\n2. 若步骤中出现章节编号引用（如"A.2.2.1 溶液"、"A.3.3.1 试样"），保留引用编号及其后的简要描述词不变，禁止展开或猜测被引用的具体操作内容。\n3. 保留所有操作参数（温度、时间、体积、质量、转速等）及其精确数值，禁止任何改动。\n4. 步骤编号（如 A.3.3.2）保留在句首作为定位标识。
```

- [ ] **Step 2: 更新 `material` 的 prompt_template**

```
将以下试剂、材料或仪器信息转化为完整陈述文本。\n\n1. 将内联 LaTeX（$...$）中的数值和单位转化为可读文本（如 $10\\mathrm{g}$ → 10 g，$0.2\\mathrm{mol}/\\mathrm{L}$ → 0.2 mol/L）。\n2. 每条试剂或仪器保留独立陈述，格式为"[名称]：[规格/配制方法]"，保留浓度、纯度、配比等参数。\n3. 若内容为通用规定段落（如"本标准所用试剂均指分析纯…"），直接清洁 LaTeX 后输出，不增不减。\n4. 禁止修改任何数值、浓度、单位或物质名称。
```

- [ ] **Step 3: 更新 `definition` 的 prompt_template**

```
将以下术语定义或技术特征描述转化为标准化陈述文本。\n\n1. 若包含明确术语定义，输出格式为"[术语] 是指 [定义内容]"，确保主语明确。\n2. 若当前文本中出现"本标准中 X 是指"的模式，确保主语"X"在句首明确出现；对无法在当前文本中确认指代目标的"上述"、"该"等代词，保留原词不变。\n3. 将内联 LaTeX（$...$）转化为可读符号（如 $1000\\mathrm{cm}^{-1}$ → 1000 cm⁻¹）；若出现块公式（$$...$$），转化为可读文字描述，保留数值和单位不变。\n4. 严格保留所有数值、单位、技术参数，禁止任何改动。
```

- [ ] **Step 4: 更新 `scope` 的 prompt_template**

```
将以下适用范围文本转化为自包含的陈述文本。\n\n1. 若原文中明确出现具体标准号（如"GB 15044—2016"），将"本标准"替换为该标准号；若原文中未出现标准号，保留"本标准"原词，不得猜测或补全。\n2. 将内联 LaTeX（$...$）中的物质名称或符号转化为可读文本（如 $\\lambda$ → λ）。\n3. 保留所有适用对象、原料描述、产品型号等限定信息，不得删减。\n4. 输出为一段完整独立的陈述，无需依赖外部上下文即可理解。
```

- [ ] **Step 5: 验证 JSON 格式有效**

```bash
cd agent-server && python3 -c "import json; json.load(open('app/core/parser_workflow/rules/content_type_rules.json'))" && echo "JSON valid"
```

- [ ] **Step 6: 运行中扩展类型的测试**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_prompt_templates.py -v -k "procedure or material or definition or scope"
```

期望：相关测试全部 PASS

- [ ] **Step 7: 提交**

```bash
git add agent-server/app/core/parser_workflow/rules/content_type_rules.json
git commit -m "feat(rules): update procedure/material/definition/scope prompt_templates"
```

---

### Task 4: 更新 `amendment` 和 `metadata` 的 prompt_template（低扩展）

**Files:**
- Modify: `app/core/parser_workflow/rules/content_type_rules.json`

- [ ] **Step 1: 更新 `amendment` 的 prompt_template**

```
将以下标准修改记录转化为完整陈述文本。\n\n1. 将"——"开头的列表项逐条转化为独立陈述句，去除"——"符号。\n2. 若原文中明确出现具体标准号（如"GB 15044—2016"），将"本标准"替换为该标准号；若原文中未出现标准号，保留"本标准"原词，不得猜测或补全。\n3. 严格保留所有修改描述的原文措辞（增加了/删除了/修改了的具体内容），禁止概括或改写。\n4. 禁止修改任何指标名称、数值或标准编号。
```

- [ ] **Step 2: 更新 `metadata` 的 prompt_template**

```
将以下章节标题或文档标识信息转化为简洁陈述句。\n- 去除 Markdown 标题符号（#、##、###）和多余空格；\n- 将发布/实施日期转化为"于[日期]发布，[日期]实施"的格式；\n- 若内容为纯标准号（如"GB 1886.169—2016"）或纯章节编号标题，直接原样输出，不添加任何解释或扩展。
```

- [ ] **Step 3: 验证 JSON 格式有效**

```bash
cd agent-server && python3 -c "import json; json.load(open('app/core/parser_workflow/rules/content_type_rules.json'))" && echo "JSON valid"
```

- [ ] **Step 4: 运行全部 prompt_template 测试**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/test_prompt_templates.py -v
```

期望：全部 PASS

- [ ] **Step 5: 提交**

```bash
git add agent-server/app/core/parser_workflow/rules/content_type_rules.json
git commit -m "feat(rules): update amendment and metadata prompt_templates"
```

---

### Task 5: 运行完整测试套件，确认无回归

**Files:**
- 无修改

- [ ] **Step 1: 运行 parser_workflow 全部单元测试**

```bash
cd agent-server && uv run pytest tests/core/parser_workflow/ -v --ignore=tests/core/parser_workflow/test_classify_node_real_llm.py --ignore=tests/core/parser_workflow/test_transform_node_real_llm.py --ignore=tests/core/parser_workflow/test_escalate_node_real_llm.py --ignore=tests/core/parser_workflow/test_parse_node_real.py --ignore=tests/core/parser_workflow/test_slice_node_real.py --ignore=tests/core/parser_workflow/test_structure_node_real_llm.py
```

期望：全部 PASS，无回归

- [ ] **Step 2: 提交收尾 commit（如有遗留改动）**

若 Step 1 全部通过，且无未提交改动，则此步跳过。

---

## 验收标准

1. `test_prompt_templates.py` 全部测试通过
2. `content_type_rules.json` JSON 格式有效
3. 全部单元测试无回归
4. 8 种 semantic_type 均有专属 prompt，不再使用通用占位符
