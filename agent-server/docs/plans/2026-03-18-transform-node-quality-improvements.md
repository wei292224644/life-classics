# Transform Node 输出质量整改方案

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 transform_node 输出中发现的 7 类质量问题，提升 RAG 检索精度与 chunk 内容准确性。

**Architecture:** 问题分布在三个层次：(1) slice_node 的 section_path 文本处理；(2) classify_node 的语义分类规则（content_type_rules.json）；(3) transform_node 的 prompt_template 幻觉防控。大多数修改在 `content_type_rules.json` 配置中完成，代码修改仅 slice_node 一处。

**Tech Stack:** Python 3.10+, uv, pytest。规则文件：`app/core/parser_workflow/rules/content_type_rules.json`，核心节点：`slice_node.py`、`classify_node.py`、`transform_node.py`。

---

## 问题清单与根因映射

| # | 问题描述 | 根因定位 | 优先级 |
|---|---------|---------|--------|
| P1 | `section_path` 中含未渲染 LaTeX（如 `$\mathrm{SO}_4$`） | `slice_node.py` 直接用 heading 原文构建 section_path | **高** |
| P2 | `formula` chunk 变量说明 LLM 幻觉（变量含义写错） | `calculation` prompt_template 缺乏忠实性约束 | **高** |
| P3 | `A.2 鉴别试验`末句被误分类为 `definition` | `definition` semantic_type 描述过宽，未排除检测特征描述 | **高** |
| P4 | `amendment` content 中内联 LaTeX 未渲染 | `amendment` prompt_template 缺少 LaTeX 渲染规则 | **中** |
| P5 | 前言变更列表 semantic_type 分类不一致（limit/procedure/metadata混杂） | `metadata`/`limit`/`procedure` 语义描述与示例未覆盖前言变更场景 | **中** |
| P6 | `2 技术要求`下存在包含三张表内容的超大合并 paragraph chunk | classify_node 对整节 raw_chunk 的"保守切分"产生冗余汇总段 | **低** |
| P7 | 不同节层级的 section_path 深度不一致（2.x 只有1层 vs 附录A有2层） | slice_node 按 soft_max 保留整块时，子节路径丢失——属于已知设计权衡 | **暂不处理** |

> **P7 说明：** 当 "2 技术要求" 整节在 soft_max 内时，slice_node 有意将其保留为一个 raw_chunk，section_path 只记录顶层节名。这与附录A按 `##` 分节的行为差异源于文档结构本身，代价可接受，本次不做修改。

---

## 文件变更地图

| 文件 | 类型 | 修改内容 |
|------|------|---------|
| `app/core/parser_workflow/nodes/slice_node.py` | **Modify** | 新增 `_clean_section_path_text()` 函数，在 `recursive_slice` 构建 `path` 时对 heading title 做 LaTeX-to-Unicode 清洗 |
| `app/core/parser_workflow/rules/content_type_rules.json` | **Modify** | 更新 `definition` 语义描述；强化 `calculation` prompt；添加 LaTeX 规则到 `amendment` prompt；完善 `metadata`/`limit`/`procedure` 示例 |
| `tests/core/parser_workflow/test_slice_node.py` | **Modify** | 新增 section_path LaTeX 清洗测试 |
| `tests/core/parser_workflow/test_prompt_templates.py` | **Modify** | 新增 calculation 忠实性约束测试、amendment LaTeX 渲染测试、definition 排除检测特征测试 |

---

## Task 1：slice_node — section_path LaTeX 清洗

**根因：** `recursive_slice` 中 `path = parent_path + ([title] if title else [])` 直接使用 markdown heading 的原始文本，不处理其中的 LaTeX。

**文件：**
- Modify: `app/core/parser_workflow/nodes/slice_node.py`
- Modify: `tests/core/parser_workflow/test_slice_node.py`

- [ ] **Step 1.1：写失败测试**

在 `test_slice_node.py` 中新增：

```python
def test_section_path_latex_is_normalized():
    """heading 中的 LaTeX 符号在 section_path 中应被渲染为 Unicode"""
    md = "## A.3 硫酸酯（以 $\\mathrm{SO}_4$ 计）的测定\n\n正文内容。"
    result = recursive_slice(md, [2], [], soft_max=5000, hard_max=10000, errors=[])
    assert len(result) == 1
    path = result[0]["section_path"]
    assert "$" not in path[0], f"section_path 中不应含 LaTeX: {path}"
    assert "SO₄" in path[0] or "SO4" in path[0], f"应含渲染后的化学式: {path}"


def test_section_path_mathbf_ph_normalized():
    """$\\mathbf{pH}$ 应在 section_path 中渲染为 pH"""
    md = "## A.8 $\\mathbf{pH}$ 的测定\n\n正文内容。"
    result = recursive_slice(md, [2], [], soft_max=5000, hard_max=10000, errors=[])
    path = result[0]["section_path"]
    assert "$" not in path[0]
    assert "pH" in path[0]
```

- [ ] **Step 1.2：运行测试，确认失败**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_slice_node.py::test_section_path_latex_is_normalized tests/core/parser_workflow/test_slice_node.py::test_section_path_mathbf_ph_normalized -v
```

期望：FAILED（KeyError 或 assert "$" not in path 失败）

- [ ] **Step 1.3：在 slice_node.py 中实现 `_clean_section_path_text()`**

在文件顶部 `import` 区域添加（`re` 已引入），在 `_heading_pattern` 函数前插入：

```python
def _clean_section_path_text(title: str) -> str:
    """
    将 heading 标题中常见的 LaTeX inline 语法转化为可读 Unicode，
    避免 section_path 中出现原始 LaTeX 字符串。
    仅处理 GB 标准文档中实际出现的模式，不追求完整覆盖。
    """
    # $\mathrm{X_Y}$ / $\mathrm{XY}$ → XY（下标转数字）
    title = re.sub(r'\$\\mathrm\{([^}]+)\}\$', lambda m: m.group(1).replace('_', ''), title)
    # $\mathbf{X}$ → X
    title = re.sub(r'\$\\mathbf\{([^}]+)\}\$', r'\1', title)
    # $\lambda$ → λ
    title = title.replace(r'$\lambda$', 'λ').replace(r'$\\lambda$', 'λ')
    # 兜底：去除残余 $...$ inline LaTeX
    title = re.sub(r'\$[^$\n]{1,60}\$', '', title)
    # 清理多余空格
    title = re.sub(r' {2,}', ' ', title).strip()
    return title
```

然后在 `recursive_slice` 中修改 path 构建行（约第 81 行）：

```python
# 原代码
path = parent_path + ([title] if title else [])

# 改为
path = parent_path + ([_clean_section_path_text(title)] if title else [])
```

- [ ] **Step 1.4：运行测试，确认通过**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_slice_node.py::test_section_path_latex_is_normalized tests/core/parser_workflow/test_slice_node.py::test_section_path_mathbf_ph_normalized -v
```

期望：PASSED

- [ ] **Step 1.5：运行完整 slice_node 测试集，确认无回归**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_slice_node.py -v
```

期望：全部 PASSED

- [ ] **Step 1.6：Commit**

```bash
git add agent-server/app/core/parser_workflow/nodes/slice_node.py \
        agent-server/tests/core/parser_workflow/test_slice_node.py
git commit -m "fix(slice_node): normalize LaTeX in section_path heading titles"
```

---

## Task 2：calculation prompt — 变量说明忠实性约束

**根因：** `calculation` prompt_template 只要求"转化为可读符号"，未明确禁止 LLM 改写变量含义，导致公式变量说明出现幻觉（如 `m₁ → 样品质量` 而非 `坩埚加残渣的质量`）。

**文件：**
- Modify: `app/core/parser_workflow/rules/content_type_rules.json`
- Modify: `tests/core/parser_workflow/test_prompt_templates.py`

- [ ] **Step 2.1：写失败测试**

在 `test_prompt_templates.py` 末尾新增：

```python
def test_calculation_prompt_forbids_variable_description_rewrite():
    """calculation prompt 应明确包含'逐字'或'不得改写'以约束变量说明忠实性。
    注意：当前 prompt 含有"不得猜测"（针对用途描述），但不含"逐字"/"不得改写"
    （针对变量说明），因此此测试应在修改前失败。"""
    prompt = _prompt(_load(), "calculation")
    assert "逐字" in prompt or "不得改写" in prompt, (
        f"calculation prompt 应明确禁止改写变量说明，需含'逐字'或'不得改写'。实际内容：{prompt}"
    )


def test_calculation_prompt_variable_desc_must_come_from_original():
    """calculation prompt 应明确要求变量说明文字来自原文（不得自行补全空白）。
    当前 prompt 不含"原文"二字，此测试应在修改前失败。"""
    prompt = _prompt(_load(), "calculation")
    assert "原文" in prompt and "变量说明" in prompt, (
        f"calculation prompt 应包含'原文'和'变量说明'，禁止 LLM 补全空白变量。实际内容：{prompt}"
    )
```

- [ ] **Step 2.2：运行测试，确认失败**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_prompt_templates.py::test_calculation_prompt_forbids_variable_description_rewrite tests/core/parser_workflow/test_prompt_templates.py::test_calculation_prompt_variable_desc_must_come_from_original -v
```

期望：FAILED（两个测试均报 AssertionError）

- [ ] **Step 2.3：更新 content_type_rules.json 中 calculation 的 prompt_template**

将 `calculation` 的 `prompt_template` 替换为：

```
将以下计算公式及变量说明转化为可检索的混合文本。

1. 若原文或其章节标题中明确给出了计算对象（如"A.3.4 硫酸酯含量的计算"或"硫酸酯的质量分数 w₁，按式(A.1)计算"），在最前面用一句话概括计算用途，须包含被测物质名称；若无法从原文确定计算对象，跳过此步，不得猜测。
2. 保留原始 LaTeX 块公式（$$...$$）完整，不做任何修改。
3. 将变量说明中的内联 LaTeX（如 $m_1$、$\mathrm{SO}_4$）转化为可读符号（m₁、SO₄），保留"——"格式的变量说明列表。
4. **变量说明的文字描述必须严格来自原文，逐字保留，不得改写、概括或补全。若原文某变量说明为"——坩埚加残渣的质量"，则输出必须为"——坩埚加残渣的质量"，不得改为"——样品质量"或任何其他表述。**
5. 若原文变量说明为空（如仅有符号无文字），则变量说明行留空，不得猜测填充含义。
6. 严格禁止修改公式中的任何变量名、系数、运算符或数值。
```

- [ ] **Step 2.4：运行测试，确认通过**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_prompt_templates.py -v
```

期望：全部 PASSED（包含原有测试无回归）

- [ ] **Step 2.5：Commit**

```bash
git add agent-server/app/core/parser_workflow/rules/content_type_rules.json \
        agent-server/tests/core/parser_workflow/test_prompt_templates.py
git commit -m "fix(rules): strengthen calculation prompt to prevent variable description hallucination"
```

---

## Task 3：definition 语义类型 — 排除检测特征描述

**根因：** `definition` 的描述为"术语、概念或常数的定义"，示例中出现"卡拉胶是指..."，导致 LLM 将"卡拉胶有一切多糖具有的典型的强、宽谱段，范围是 1000 cm⁻¹～1100 cm⁻¹"（IR鉴别特征）也匹配为 `definition`，并套用"X 是指 Y"模板，产生错误的 content 和错误的 semantic_type。

**文件：**
- Modify: `app/core/parser_workflow/rules/content_type_rules.json`
- Modify: `tests/core/parser_workflow/test_prompt_templates.py`

- [ ] **Step 3.1：写失败测试**

在 `test_prompt_templates.py` 末尾新增：

```python
def test_definition_semantic_type_must_contain_exclusion_clause():
    """definition 的语义描述必须含有明确排除词（'不包括'或'排除'），
    防止 LLM 将检测特征、光谱特性等错误匹配为术语定义。
    当前描述为'术语、概念或常数的定义'，不含排除词，此测试应在修改前失败。"""
    rules = _load()
    defn = next(t for t in rules["semantic_types"] if t["id"] == "definition")
    desc = defn["description"]
    assert "不包括" in desc or "排除" in desc, (
        f"definition 描述必须含排除词（'不包括'或'排除'），当前描述：{desc}"
    )


def test_definition_prompt_outputs_verbatim_for_non_definition():
    """definition prompt 对无明确"X是指Y"格式的内容应原样输出（不强套模板）。
    当前 prompt 有'若包含明确术语定义'但无'否则...原样输出'分支，此测试应在修改前失败。"""
    prompt = _prompt(_load(), "definition")
    assert "否则" in prompt and "原样输出" in prompt, (
        f"definition prompt 应有 else 分支：否则直接原样输出，不强套定义格式。实际内容：{prompt}"
    )
```

- [ ] **Step 3.2：运行测试，确认两个测试均失败**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_prompt_templates.py::test_definition_semantic_type_must_contain_exclusion_clause tests/core/parser_workflow/test_prompt_templates.py::test_definition_prompt_outputs_verbatim_for_non_definition -v
```

- [ ] **Step 3.3：更新 content_type_rules.json 中 definition 的 semantic_types 描述与 prompt**

1. 更新 `semantic_types` 中 `definition` 的 `description` 和 `examples`：

```json
{
  "id": "definition",
  "description": "对术语或概念给出明确定义的文本（格式通常为"X是指Y"或"X定义为Y"）。不包括：检测特性描述（如光谱范围、鉴别特征）、技术指标（应归为 limit）、操作步骤（应归为 procedure）。",
  "examples": [
    "3.1 卡拉胶是指以红藻类植物为原料制成的...",
    "术语和定义（后接术语正文）",
    "本标准中，X 是指..."
  ]
}
```

2. 更新 `definition` 的 `prompt_template`，强化条件判断：

```
将以下术语定义或技术特征描述转化为标准化陈述文本。

1. 若包含明确术语定义（原文存在"X是指Y"或"X定义为Y"的格式），输出格式为"[术语] 是指 [定义内容]"，确保主语明确；否则直接清洁 LaTeX 后原样输出，不强套定义格式。
2. 若当前文本中出现"本标准中 X 是指"的模式，确保主语"X"在句首明确出现；对无法在当前文本中确认指代目标的"上述"、"该"等代词，保留原词不变。
3. 将内联 LaTeX（$...$）转化为可读符号（如 $1000\mathrm{cm}^{-1}$ → 1000 cm⁻¹）；若出现块公式（$$...$$），转化为可读文字描述，保留数值和单位不变。
4. 严格保留所有数值、单位、技术参数，禁止任何改动。
```

- [ ] **Step 3.4：运行全部 prompt_templates 测试，确认通过**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_prompt_templates.py -v
```

期望：全部 PASSED

- [ ] **Step 3.5：Commit**

```bash
git add agent-server/app/core/parser_workflow/rules/content_type_rules.json \
        agent-server/tests/core/parser_workflow/test_prompt_templates.py
git commit -m "fix(rules): narrow definition semantic_type to exclude detection characteristics"
```

---

## Task 4：amendment prompt — 添加 LaTeX 渲染规则

**根因：** `amendment` prompt_template 未包含内联 LaTeX 渲染指令，导致修改单内容中的 `$\lambda$`、`$\mathrm{CFU/g}$` 等未被转为 Unicode。

**文件：**
- Modify: `app/core/parser_workflow/rules/content_type_rules.json`
- Modify: `tests/core/parser_workflow/test_prompt_templates.py`

- [ ] **Step 4.1：写失败测试**

在 `test_prompt_templates.py` 末尾新增：

```python
def test_amendment_prompt_renders_inline_latex():
    """amendment prompt 应包含内联 LaTeX 渲染规则，防止修改单 content 含原始 LaTeX"""
    prompt = _prompt(_load(), "amendment")
    assert ("LaTeX" in prompt or "$" in prompt) and ("转化" in prompt or "渲染" in prompt or "可读" in prompt), (
        f"amendment prompt 应包含 LaTeX inline 渲染规则。实际内容：{prompt}"
    )
```

- [ ] **Step 4.2：运行测试，确认失败**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_prompt_templates.py::test_amendment_prompt_renders_inline_latex -v
```

- [ ] **Step 4.3：更新 amendment 的 prompt_template**

将 `amendment` 的 `prompt_template` 替换为：

```
将以下标准修改记录转化为完整陈述文本。

1. 将"——"开头的列表项逐条转化为独立陈述句，去除"——"符号。
2. 若原文中明确出现具体标准号（如"GB 15044—2016"），将"本标准"替换为该标准号；若原文中未出现标准号，保留"本标准"原词，不得猜测或补全。
3. 严格保留所有修改描述的原文措辞（增加了/删除了/修改了的具体内容），禁止概括或改写。
4. 将内联 LaTeX（$...$）转化为可读符号（如 $\lambda$ → λ，$\mathrm{CFU/g}$ → CFU/g，$\mathrm{SO}_4$ → SO₄）；禁止在输出中保留原始 LaTeX 语法。
5. 禁止修改任何指标名称、数值或标准编号。
```

- [ ] **Step 4.4：运行全部 prompt_templates 测试，确认通过**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_prompt_templates.py -v
```

期望：全部 PASSED

- [ ] **Step 4.5：Commit**

```bash
git add agent-server/app/core/parser_workflow/rules/content_type_rules.json \
        agent-server/tests/core/parser_workflow/test_prompt_templates.py
git commit -m "fix(rules): add inline LaTeX rendering rule to amendment prompt_template"
```

---

## Task 5：semantic_type 分类规则 — 前言变更场景消歧

**根因：** 前言中描述标准版本变化的列表项（"增加了/删除了/修改了..."）被分类为 `limit`、`procedure` 或 `metadata`，缺乏统一。这类内容属于文档变更历史，应归为 `metadata`（而非 `amendment`，后者专指修改单正文）。

**文件：**
- Modify: `app/core/parser_workflow/rules/content_type_rules.json`
- Modify: `tests/core/parser_workflow/test_prompt_templates.py`

- [ ] **Step 5.1：写失败测试**

```python
def test_metadata_semantic_type_covers_preface_changes():
    """metadata 的示例中应包含前言变更格式（如"——增加了"），
    以引导 LLM 将前言变更列表归为 metadata 而非 limit/procedure。
    当前示例不含此类条目，此测试应在修改前失败。"""
    rules = _load()
    meta = next(t for t in rules["semantic_types"] if t["id"] == "metadata")
    examples = " ".join(meta.get("examples", []))
    assert "增加了" in examples or "删除了" in examples or "修改了" in examples, (
        f"metadata examples 应包含前言变更示例（增加了/删除了/修改了）。当前: {examples}"
    )
```

- [ ] **Step 5.2：运行测试，确认失败**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_prompt_templates.py::test_metadata_semantic_type_covers_preface_changes -v
```

- [ ] **Step 5.3：更新 content_type_rules.json 中 metadata 的描述与示例**

将 `semantic_types` 中 `metadata` 条目更新为：

```json
{
  "id": "metadata",
  "description": "文档的组织性信息，包括：(1) 标准号、发布机构、日期等文件身份信息；(2) 各级章节标题行；(3) 前言中描述版本变化的说明列表（如"增加了X指标"、"删除了Y要求"、"修改了Z方法"——这些是文档变更历史，不是技术指标）。注意：描述具体技术指标限量的内容应归为 limit，操作步骤应归为 procedure。",
  "examples": [
    "GB 1886.169—2016",
    "2016-08-31 发布",
    "2017-01-01 实施",
    "## A.3 硫酸酯的测定",
    "# 附录 A 检验方法",
    "——增加了酸不溶物的指标要求及检验方法",
    "——删除了大肠菌群的指标要求",
    "——部分检验方法的引用标准调整为最新发布的版本"
  ]
}
```

- [ ] **Step 5.4：运行全部 prompt_templates 测试，确认通过**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_prompt_templates.py -v
```

期望：全部 PASSED

- [ ] **Step 5.5：Commit**

```bash
git add agent-server/app/core/parser_workflow/rules/content_type_rules.json \
        agent-server/tests/core/parser_workflow/test_prompt_templates.py
git commit -m "fix(rules): clarify metadata covers preface change lists to reduce misclassification"
```

---

## Task 6：回归验证（端到端）

在所有规则和代码修改完成后，运行完整测试套件确认无回归。

- [ ] **Step 6.1：运行非 real_llm 的全量测试**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/ -v -m "not real_llm"
```

期望：全部 PASSED

- [ ] **Step 6.2：确认 prompt_templates 测试全绿**

```bash
cd agent-server
uv run pytest tests/core/parser_workflow/test_prompt_templates.py -v
```

期望：全部 PASSED，数量应比修改前增加 7 个测试（Task1×2 + Task2×2 + Task3×2 + Task4×1 + Task5×1 = 8，其中 Task1 在 test_slice_node.py）

- [ ] **Step 6.3：最终 Commit**

```bash
# 不使用 git add -A，明确列出修改文件
git status  # 确认无意外文件
git add agent-server/app/core/parser_workflow/nodes/slice_node.py \
        agent-server/app/core/parser_workflow/rules/content_type_rules.json \
        agent-server/tests/core/parser_workflow/test_slice_node.py \
        agent-server/tests/core/parser_workflow/test_prompt_templates.py
git commit -m "test: verify all transform-node quality fix tests pass"
```

---

## 验收标准

| 验收项 | 通过条件 |
|--------|---------|
| section_path 无 LaTeX | `test_section_path_latex_is_normalized` 通过 |
| 变量说明忠实 | `test_calculation_prompt_forbids_variable_description_rewrite` 通过 |
| definition 描述含排除词 | `test_definition_semantic_type_must_contain_exclusion_clause` 通过 |
| definition prompt 含 else 分支 | `test_definition_prompt_outputs_verbatim_for_non_definition` 通过 |
| amendment 渲染 LaTeX | `test_amendment_prompt_renders_inline_latex` 通过 |
| 前言变更归为 metadata | `test_metadata_semantic_type_covers_preface_changes` 通过 |
| 全量测试无回归 | `pytest -m "not real_llm"` 全部 PASSED |

---

## 不在本次整改范围内的问题

- **P6（超大合并 paragraph chunk）**：需要修改 classify_node 的 prompt 中"保守切分"策略，影响范围较大，建议单独立项评估。
- **P7（section_path 层级不一致）**：属于 slice_node 的已知设计权衡（soft_max 内保整块），不做修改。
