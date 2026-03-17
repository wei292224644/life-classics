# 双维度 content_type 体系设计

**日期**：2026-03-17
**范围**：parser_workflow classify_node 及相关数据模型重构

---

## 背景与动机

当前 `content_type_rules.json` 只定义了 6 个通用类型（`plain_text`、`numbered_list`、`table`、`formula`、`standard_header`、`preface`），无法区分 GB 标准中语义差异显著的章节（如"试剂和材料"与"分析步骤"都被归为 `numbered_list`），导致下游 RAG 检索无法按内容用途过滤。

同时，原 `DocumentChunk` 的 `ContentType` 枚举（16个专业类型）与 classify_node 实际输出完全脱节，两套体系形同虚设。

本次重构用**两字段双维度体系**替换单字段设计，从根本上解决该问题。

---

## 设计目标

- `structure_type`：描述内容的**呈现形式**（原子、通用）
- `semantic_type`：描述内容对读者的**用途**（原子、通用，不绑定具体领域术语）
- 两个维度独立分类，LLM 分别推断，降低混淆
- 对下游 RAG 检索、transform 策略选择友好

---

## 类型定义

### structure_type（5种）

| id | 含义 | 典型形态 |
|---|---|---|
| `paragraph` | 叙述性段落 | 连续文字说明 |
| `list` | 编号或条目列表 | `A.3.1.1 xxx`、`——增加了...` |
| `table` | 表格数据 | HTML `<table>` 或 Markdown `\|` |
| `formula` | 数学或化学公式 | LaTeX `$$...$$` 或行内 `$...$` |
| `header` | 纯标题、无实质内容的章节头 | 仅有 `## 2 技术要求` 无后续内容 |

### semantic_type（8种）

| id | 用户会怎么查 | GB 标准中的典型位置 |
|---|---|---|
| `metadata` | 这是哪个标准、何时发布 | 文档头部、标准号、发布/实施日期 |
| `scope` | 这个标准适用于什么 | `1 范围` 章节 |
| `limit` | 某指标的限量或要求值是多少 | `2.1 感官要求`、`2.2 理化指标`、`2.3 微生物指标` |
| `procedure` | 怎么操作或测定 | `分析步骤`、`A.X.X 测定` |
| `material` | 需要哪些试剂或仪器 | `试剂和材料`、`仪器和设备` |
| `calculation` | 结果怎么计算，公式含义是什么 | `结果计算` 节（含公式、变量说明） |
| `definition` | 某术语或概念的含义 | `术语和定义` 章节 |
| `amendment` | 该标准历史上改过什么 | `第X号修改单` 条目 |

---

## 数据模型变更

### `TypedSegment`（`models.py`）

```python
# 修改前
class TypedSegment(TypedDict):
    content: str
    content_type: str          # 单字段
    transform_params: dict
    confidence: float
    ...

# 修改后
class TypedSegment(TypedDict):
    content: str
    structure_type: str        # 结构维度
    semantic_type: str         # 语义维度
    transform_params: dict
    confidence: float
    ...
```

### `DocumentChunk`（`models.py`）

```python
# 修改前
class DocumentChunk(TypedDict):
    ...
    content_type: str

# 修改后
class DocumentChunk(TypedDict):
    ...
    structure_type: str
    semantic_type: str
```

`document_chunk.py` 的处理方式：**仅在枚举定义上方添加 `# DEPRECATED` 注释**，不修改枚举本身及旧 `DocumentChunk` class。原因：旧 `DocumentChunk` class（带 `to_documents()` 方法）属于 kb/strategy 老流水线，与 parser_workflow 无关，不在本次范围内修改；强行删除枚举会导致旧 class 的 `content_type: ContentType` 类型注解失效并造成运行时错误。以 `models.py` 的 `DocumentChunk` TypedDict 为 parser_workflow 数据模型。

### `SegmentItem`（`nodes/output.py`）

```python
# 修改前
class SegmentItem(BaseModel):
    content: str
    content_type: str
    confidence: float

# 修改后
class SegmentItem(BaseModel):
    content: str
    structure_type: str
    semantic_type: str
    confidence: float
```

---

## `content_type_rules.json` 结构变更

```json
{
  "confidence_threshold": 0.7,
  "structure_types": [
    {
      "id": "paragraph",
      "description": "叙述性段落，连续文字说明",
      "examples": ["本标准适用于...", "本方法按照..."]
    },
    {
      "id": "list",
      "description": "编号或条目列表，包含 GB 标准中的条款项或操作步骤",
      "examples": ["A.3.1.1 异丙醇溶液：60%", "——增加了酸不溶物指标"]
    },
    {
      "id": "table",
      "description": "表格数据，HTML <table> 或 Markdown | 格式",
      "examples": ["表1 感官要求", "表2 理化指标"]
    },
    {
      "id": "formula",
      "description": "数学或化学公式，含 LaTeX 语法",
      "examples": ["$$w_1 = \\frac{...}{m} \\times 100\\%$$"]
    },
    {
      "id": "header",
      "description": "纯章节标题，无实质内容",
      "examples": ["## 2 技术要求（后无内容）", "# 附录 A 检验方法（后无内容）"]
    }
  ],
  "semantic_types": [
    {
      "id": "metadata",
      "description": "文档身份信息：标准号、发布机构、发布/实施日期",
      "examples": ["GB 1886.169—2016", "2016-08-31 发布", "2017-01-01 实施"]
    },
    {
      "id": "scope",
      "description": "标准的适用范围与对象",
      "examples": ["1 范围", "本标准适用于以红藻类植物为原料..."]
    },
    {
      "id": "limit",
      "description": "技术指标、限量值或感官/微生物要求",
      "examples": ["感官要求", "理化指标", "微生物指标", "铅(Pb)/(mg/kg) ≤ 5.0"]
    },
    {
      "id": "procedure",
      "description": "操作步骤或测定方法的具体过程",
      "examples": ["分析步骤", "A.3.3 分析步骤", "称取试样...置于..."]
    },
    {
      "id": "material",
      "description": "操作前需要准备的试剂或仪器设备",
      "examples": ["试剂和材料", "仪器和设备", "A.9.1 试剂和材料", "A.3.2 仪器和设备"]
    },
    {
      "id": "calculation",
      "description": "计算公式及其变量说明，用于从测量值推导结果",
      "examples": ["结果计算", "A.3.4 结果计算", "式中 m1——坩埚加残渣质量"]
    },
    {
      "id": "definition",
      "description": "术语、概念或常数的定义",
      "examples": ["术语和定义", "卡拉胶是指..."]
    },
    {
      "id": "amendment",
      "description": "对原标准的修改记录",
      "examples": ["第1号修改单", "将'...'修改为'...'"]
    }
  ],
  "transform": {
    "by_semantic_type": {
      "metadata":    { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "scope":       { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "limit":       { "strategy": "table_to_text", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "procedure":   { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "material":    { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "calculation": { "strategy": "formula_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "definition":  { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" },
      "amendment":   { "strategy": "plain_embed", "prompt_template": "请将以下内容转化为规范化的陈述文本，保留所有原始信息：\n" }
    }
  }
}
```

---

## `classify_node.py` prompt 变更

**实现方式：单次 LLM 调用**（`invoke_structured` 仍只调用一次），prompt 内引导模型先后独立推断两个维度，输出含 `structure_type` + `semantic_type` 的 JSON。

Prompt 结构：
```
[结构类型定义 + examples]
[语义类型定义 + examples]

对每个切分后的片段，请分两步独立判断：
步骤1 - 结构判断：这段内容的呈现形式是什么？（paragraph / list / table / formula / header）
步骤2 - 语义判断：这段内容对读者的用途是什么？（metadata / scope / limit / procedure / material / calculation / definition / amendment）

注意：两步相互独立，不要用语义推测结构，也不要用结构推测语义。
```

`ClassifyOutput.segments` 中每个 `SegmentItem` 输出形如：
```json
{"content": "...", "structure_type": "list", "semantic_type": "material", "confidence": 0.9}
```

---

## `RulesStore`（`rules.py`）变更

| 方法 | 变更 |
|---|---|
| `get_content_type_rules()` | 不变（返回整个 dict） |
| `get_transform_params(content_type_id)` | 改为 `get_transform_params(semantic_type: str)`，从 `transform.by_semantic_type` 查找 |
| `append_content_type(entry)` | **本次不修改**——escalate 路径不在本次范围内，保持现有接口不变。注意：escalate 写入的旧格式条目（`content_types[].transform`）与重构后的 `transform.by_semantic_type` 路径不兼容，会静默失效，这是已知的技术债，留待 escalate 重构时一并处理 |

---

## `has_unknown` 逻辑

当 `confidence < threshold` 时，两个字段均设为 `"unknown"`，下游行为不变。

---

## 不在本次范围内

- 空 parent chunk 过滤
- 修改单与原文章节的交叉引用
- slice_node 切分粒度统一
- enrich_node、transform_node 的 prompt_template 内容更新（结构调整即可，内容另起一轮）

---

## 受影响文件清单

| 文件 | 变更类型 |
|---|---|
| `app/core/parser_workflow/rules/content_type_rules.json` | 重写 |
| `app/core/parser_workflow/models.py` | 字段替换 |
| `app/core/parser_workflow/nodes/output.py` | 字段替换 |
| `app/core/parser_workflow/nodes/classify_node.py` | prompt 重写；低置信度路径 `content_type="unknown"` → `structure_type="unknown", semantic_type="unknown"`；规则读取从 `ct_rules.get("content_types", [])` 改为分别读取 `ct_rules.get("structure_types", [])` 和 `ct_rules.get("semantic_types", [])` |
| `app/core/parser_workflow/rules.py` | `get_transform_params` 签名变更 |
| `app/core/document_chunk.py` | 添加 `# DEPRECATED` 注释（仅注释，不删除） |
| `app/core/parser_workflow/nodes/transform_node.py` | `DocumentChunk(content_type=...)` → `DocumentChunk(structure_type=..., semantic_type=...)` |
| `tests/core/parser_workflow/test_classify_node_real_llm.py` | 断言更新 |
| `tests/core/parser_workflow/test_workflow.py` | 断言更新 |
