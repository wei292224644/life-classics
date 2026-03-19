# 交叉引用增强设计文档

**日期**：2026-03-16
**状态**：待实现
**范围**：在 `app/core/parser_workflow` 中新增 `enrich_node`，处理 GB 标准 Markdown 文档中形如"见表1"、"见图A.1"、"见附录A"的交叉引用。

---

## 1. 背景与目标

### 问题

GB 标准文档经 MinerU 转换为 Markdown 后，由 `slice_node` 按标题递归切分为多个 `RawChunk`。切分后，引用所在 chunk 与被引用内容（表格、图、附录）往往分属不同 chunk，导致：

- `transform_node` 对"样品浓缩条件见表1"这类片段进行向量化时，无法感知表1的实际内容，向量语义不完整
- 检索时"样品浓缩条件"类查询无法有效命中该 chunk

### 目标

1. **内联表格引用**：在 `transform_node` 处理前，将被引用表格的内容注入到引用方的 `TypedSegment` 中，使 LLM 能生成语义完整的向量化文本
2. **记录引用元数据**：对所有类型的引用（表、图、附录、章节）在 `DocumentChunk.meta` 中记录 `cross_refs` 和 `unresolved_refs`，供下游检索系统使用

---

## 2. 设计决策

| 决策点 | 选择 | 理由 |
|---|---|---|
| 介入阶段 | escalate_node 之后、transform_node 之前 | 内联必须在向量化前完成；必须在 escalate_node 之后，因为 escalate_node 会将 unknown 段修正为 table 类型，enrich_node 需要看到最终分类结果才能建完整的表格索引 |
| 内联范围 | 仅表格引用（`见表X`） | 表格断裂是最高价值场景；图片无文本内容；章节/附录已有独立 chunk，内联反而造成重复 |
| 图/附录/章节引用 | 只记录元数据，不内联 | 通过 `cross_refs` 供下游系统跳转 |
| 未解析引用处理 | 静默跳过 + 写入 errors 警告 | 不中断流程，方便排查 |
| 表格匹配策略 | 双重匹配（正则标签 + section_path 模糊匹配） | MinerU 输出质量参差不齐，单一策略覆盖率低 |

---

## 3. 数据模型变更

### 3.1 TypedSegment 新增字段

```python
class TypedSegment(TypedDict):
    content: str
    content_type: str
    transform_params: dict
    confidence: float
    escalated: bool
    cross_refs: List[str]   # 识别到的引用标识符，如 ["表1", "附录A", "图A.1"]
    ref_context: str        # 已解析的被引用表格内容（拼接文本），未解析时为 ""
```

`cross_refs` 和 `ref_context` 在 `classify_node` 输出时默认为空值，由 `enrich_node` 填充。

### 3.2 DocumentChunk.meta 新增字段

`transform_node` 生成 `DocumentChunk` 时，将引用信息写入 `meta`：

```python
meta={
    "transform_strategy": "...",
    "segment_raw_content": "...",
    "cross_refs": ["表1", "附录A", "图A.1"],   # 所有识别到的引用标识符
    "non_table_refs": ["附录A", "图A.1"],      # 图/附录/章节引用（设计上不内联，仅供下游跳转）
    "failed_table_refs": [],                   # 尝试内联但未能找到对应内容的表格引用
}
```

区分 `non_table_refs`（设计上不处理）与 `failed_table_refs`（本应内联但解析失败），避免下游混淆。

---

## 4. enrich_node 逻辑

### 4.1 节点定位

```
parse_node → structure_node → slice_node → classify_node
    ├── (has_unknown) → escalate_node → enrich_node → transform_node
    └── (all confident) ──────────────→ enrich_node → transform_node
```

enrich_node 必须在 escalate_node **之后**运行。escalate_node 可能将 `unknown` 段修正为 `table` 类型；若 enrich_node 在此之前运行，这些被修正的表格将无法被纳入索引，导致匹配遗漏。

**输入**：`WorkflowState`（含 `raw_chunks` + `classified_chunks`，此时所有 content_type 均已确定）
**输出**：更新后的 `classified_chunks`（TypedSegment 填充 cross_refs 和 ref_context）+ 可能追加的 `errors`

**注意**：enrich_node 返回 errors 时必须追加而非覆盖：
```python
return {"classified_chunks": updated, "errors": state.get("errors", []) + new_errors}
```
LangGraph 对 `TypedDict` 状态做 merge，直接返回新列表会替换掉上游节点写入的 errors。

### 4.2 Step 1：建表格标签索引

扫描所有 `raw_chunks` 的**完整内容**，用正则查找表格标题行（形如 `表1 xxx`、`表A.1 xxx`），建立标签→内容映射：

```python
TABLE_LABEL_PATTERN = re.compile(
    r'(?:^|\n)表\s*([\dA-Z]+(?:\.\d+)*)\s+\S', re.UNICODE
)
```

索引结构：`Dict[str, str]`，key 为标准化标签（如 `"表1"`、`"表A.1"`），value 为该 raw_chunk 的完整内容。同一文档若存在同编号表格，以后出现的覆盖前者（实践中不会发生）。

### 4.3 Step 2：逐段识别引用

对每个 `TypedSegment` 的 `content`，用正则提取表格引用标识符：

```python
TABLE_REF_PATTERN = re.compile(
    r'(?:见|参见|参照)[^\n，。；]*?(表\s*[\dA-Z]+(?:\.\d+)*)', re.UNICODE
)
```

同时识别其他引用类型（只记录，不内联）：

```python
OTHER_REF_PATTERN = re.compile(
    r'(?:见|参见|参照|按照?)\s*((?:图|附录)[^\s，。；]{0,15}|第?\s*\d+[\.\d]*\s*[节章条]|\d+\.\d+[\.\d]*)',
    re.UNICODE
)
```

### 4.4 Step 3：双重匹配表格内容

对每个提取到的表格引用标识符：

1. **正则索引命中**：直接从 Step 1 的标签索引取内容
2. **正则未命中**：遍历 `classified_chunks` 中 `content_type=table` 的段，检查其所属 `raw_chunk.section_path` 中任意一段是否包含该标识符（忽略空格后子串匹配），例如：
   ```python
   label_norm = label.replace(" ", "")  # "表 1" → "表1"
   any(label_norm in seg.replace(" ", "") for seg in raw_chunk["section_path"])
   ```
3. **两步均未命中**：`ref_context` 该引用对应部分置空，写入 errors：
   ```
   WARN: unresolved cross_ref "表1" in section_path ['3', '3.1'] — no matching raw_chunk found
   ```

已解析的多张表格内容用换行拼接后赋给 `ref_context`。

### 4.5 对 transform_node 的影响

`apply_strategy` 在构造 `_call_llm_transform` 的调用时，将 `seg["ref_context"]` 传入：

```python
# apply_strategy 中
llm_text = _call_llm_transform(seg["content"], seg["transform_params"], seg.get("ref_context", ""))
```

`_call_llm_transform` 签名新增 `ref_context: str = ""` 参数，在 prompt 末尾追加：

```python
def _call_llm_transform(content: str, transform_params: dict, ref_context: str = "") -> str:
    ...
    if ref_context:
        prompt += f"\n\n以下是文中引用的表格内容，请结合该表格理解上下文：\n{ref_context}"
    ...
```

`transform_node` 其余逻辑不变，`apply_strategy` 同时负责将 `seg["cross_refs"]` 写入 `DocumentChunk.meta`。

---

## 5. Workflow 图变更

```python
# graph.py 变更
from app.core.parser_workflow.nodes.enrich_node import enrich_node

builder.add_node("enrich_node", enrich_node)
# escalate_node 和直接路径都收敛到 enrich_node，再流向 transform_node
builder.add_edge("escalate_node", "enrich_node")   # 原来是 escalate_node → transform_node
builder.add_conditional_edges("classify_node", _should_escalate)  # 条件边不变，仍从 classify_node 发出
# _should_escalate 返回 "escalate_node" 或 "enrich_node"（原来返回 "transform_node"）
builder.add_edge("enrich_node", "transform_node")  # 新增：enrich_node → transform_node
```

`_should_escalate` 判断逻辑不变，仍检查 `has_unknown`，但返回值从 `"transform_node"` 改为 `"enrich_node"`：

```python
def _should_escalate(state: WorkflowState) -> str:
    if any(c["has_unknown"] for c in state["classified_chunks"]):
        return "escalate_node"
    return "enrich_node"   # 原来返回 "transform_node"
```

---

## 6. 文件变更清单

| 文件 | 变更类型 | 说明 |
|---|---|---|
| `nodes/enrich_node.py` | 新增 | enrich_node 全部逻辑 |
| `models.py` | 修改 | TypedSegment 增加 cross_refs、ref_context 字段 |
| `nodes/transform_node.py` | 修改 | _call_llm_transform 追加 ref_context 到 prompt |
| `nodes/classify_node.py` | 修改 | 构造 TypedSegment 时补充 cross_refs=[]、ref_context="" 默认值 |
| `nodes/escalate_node.py` | 修改 | 构造 TypedSegment 时补充 cross_refs=[]、ref_context="" 默认值 |
| `graph.py` | 修改 | 插入 enrich_node；条件边仍从 classify_node 发出，但 `_should_escalate` 返回值从 `"transform_node"` 改为 `"enrich_node"`；escalate_node → enrich_node 新增边；enrich_node → transform_node 新增边 |
| `nodes/__init__.py` | 修改 | 导出 enrich_node |

---

## 7. 测试策略（TDD）

每个功能点先写测试，再写实现：

1. **标签索引构建**：给定含 `表1 xxx` 标题行的 raw_chunks，断言索引正确建立
2. **表格引用提取**：给定含"见表1"、"条件见表 A.1"的文本，断言提取到正确标识符
3. **双重匹配**：正则命中、section_path 命中、两步均未命中三种情形分别测试
4. **未解析引用写入 errors**：断言 errors 列表包含正确格式的警告
5. **ref_context 注入 prompt**：mock transform_node，断言 prompt 包含表格内容
6. **其他引用只记元数据**：给定"见图A.1"、"见附录A"，断言 cross_refs 有值但 ref_context 为空
7. **graph 集成（无 escalate）**：断言全部 confident 时，enrich_node 在 classify_node 之后、transform_node 之前执行
8. **graph 集成（有 escalate）**：断言含 unknown 时，escalate_node 执行后 enrich_node 仍能正确识别被修正为 table 类型的段，并完成表格内联
