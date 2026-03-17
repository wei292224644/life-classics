# parser_workflow 问题列表

来源：对 `tests/artifacts/parser_workflow_nodes_20260317_215214/` 中间数据的人工审查（04_classify_node.json、05_enrich_node.json）。

---

## ISSUE-01：enrich_node 漏匹配 GB 标准最常见表格引用模式

**严重性：高**
**文件：** `app/core/parser_workflow/nodes/enrich_node.py`

### 现象

enrich_node 对整篇 GB1886.47 文档未产出任何富化，所有 segments 的 `cross_refs`、`ref_context`、`failed_table_refs` 均为空。

### 根因

`_TABLE_REF_PATTERN` 只匹配 `见/参见/参照` 前缀：

```python
_TABLE_REF_PATTERN = re.compile(
    r'(?:见|参见|参照)[^\n，。；]*?表\s*([\dA-Z]+(?:\.\d+)*)',
)
```

GB 标准中实际出现的引用写法是：

```
感官要求应符合表 1 的规定。
理化指标应符合表 2 的规定。
微生物指标应符合表 3 的规定。
```

`应符合表X` 不在正则覆盖范围内，导致 enrich_node 对 GB 标准几乎全部失效。

### 预期修复

在 `_TABLE_REF_PATTERN` 中增加 `应符合` 等 GB 常用前缀，参考模式：

```
(?:见|参见|参照|应符合)[^\n，。；]*?表\s*([\dA-Z]+(?:\.\d+)*)
```

并补充对应的单元测试。

---

## ISSUE-02：classify_node 中 HTML 表格属性被 LLM 篡改

**严重性：高**
**文件：** `app/core/parser_workflow/nodes/classify_node.py`

### 现象

raw_chunk 原文：
```html
<td rowspan="2">取适量试样置于清洁、干燥的白瓷盘中，在自然光线下观察其色泽和状态</td>
```

classify_node 输出的 segment content：
```html
<td> rowspan="2">取适量试样置于清洁、干燥的白瓷盘中，在自然光线下观察其色泽和状态</td>
```

`rowspan` 属性被从标签内挤出，HTML 结构损坏。

### 根因

LLM 生成 JSON 时，content 中的 ASCII 双引号（HTML 属性值的 `"`）导致 JSON 字符串提前截断，LLM 为了"自救"篡改了内容。

### 修复状态

已在 `_call_classify_llm` 中引入 `_escape_for_json_prompt(chunk_content)`，在 content 嵌入 prompt 前将 ASCII 双引号转义为 `\"`（commit: 当前工作区）。

需补充回归测试，验证含 HTML 属性的 chunk 经 classify 后 content 保持原文。

---

## ISSUE-03：header segment 的 semantic_type 偶发 definition/metadata 不一致

**严重性：低**
**文件：** `app/core/parser_workflow/nodes/classify_node.py`（prompt 层面）

### 现象

大多数方法节 header（如 `## A.3 硫酸酯的测定`）被打为 `semantic_type: "metadata"`，但 A.5、A.6 节的 header 被打为 `"definition"`：

```
## A.5 总灰分的测定  →  structure_type: header, semantic_type: definition
## A.6 酸不溶灰分的测定  →  structure_type: header, semantic_type: definition
```

### 根因

LLM 对"测定方法节标题"的 semantic_type 判断不稳定，`definition` 和 `metadata` 均可被视为合理，但整篇文档应保持一致。

### 预期修复

在 classify_node 的 prompt 分类规则中补充约束：**纯标题行（仅包含编号 + 标题文字、无正文）一律归为 `metadata`**，无论其所属章节语义如何。
或在 post-processing 阶段对 `structure_type == "header"` 的 segment 强制覆写 `semantic_type = "metadata"`。
