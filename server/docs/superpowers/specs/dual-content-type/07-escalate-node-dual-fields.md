# Spec 07：escalate_node 适配双字段

## 问题现象

escalate_node 处理 `content_type == "unknown"` 的 segment 时，依赖旧的单字段体系：

1. 读取 `content_types` 列表（重构后不再存在）传给 LLM
2. 判断 `seg["content_type"] != "unknown"` 来跳过已分类的 segment
3. 构造新的 `TypedSegment` 时写入单字段 `content_type=new_ct_id`

重构后以上三处均会失效或产生运行时错误。

## 根因

`escalate_node.py` 完整地依赖旧单字段体系：

```python
# escalate_node.py

# 1. 读取旧 content_types 列表
existing_types = store.get_content_type_rules().get("content_types", [])   ← 重构后为空

# 2. 判断 unknown
if seg["content_type"] != "unknown":    ← 字段名变更后 KeyError
    continue

# 3. 写入新 TypedSegment
new_segments[j] = TypedSegment(
    content=seg["content"],
    content_type=new_ct_id,             ← 字段名变更后 TypedDict 报错
    ...
)
```

`EscalateOutput` Pydantic 模型中的 `id` 字段（代表新 content_type 的 id）也是单值设计，无法同时表达 structure_type 和 semantic_type。

## 发现方式

查看 `escalate_node.py` 第 68、72、79、84 行，再对照 `nodes/output.py` 中 `EscalateOutput` 的字段定义：

```python
class EscalateOutput(BaseModel):
    action: Literal["use_existing", "create_new"]
    id: str           ← 单值，代表 content_type_id
    description: str
    transform: TransformParams
```

`id` 字段需拆分为 `structure_type` + `semantic_type` 才能适配新体系。

## 方案

### 1. 更新 `EscalateOutput`（`nodes/output.py`）

```python
# 修改前
class EscalateOutput(BaseModel):
    action: Literal["use_existing", "create_new"]
    id: str
    description: str
    transform: TransformParams

# 修改后
class EscalateOutput(BaseModel):
    action: Literal["use_existing", "create_new"]
    structure_type: str
    semantic_type: str
    description: str
    transform: TransformParams
```

### 2. 更新 escalate_node prompt

将 prompt 中"现有 content_type 列表"改为分别展示 `structure_types` 和 `semantic_types`，要求 LLM 对 unknown segment 分别给出两个维度的判断。

### 3. 更新 unknown 判断条件

```python
# 修改前
if seg["content_type"] != "unknown":

# 修改后
if seg["semantic_type"] != "unknown":
```

### 4. 更新 TypedSegment 构造

```python
# 修改前
new_segments[j] = TypedSegment(
    content_type=new_ct_id,
    ...
)

# 修改后
new_segments[j] = TypedSegment(
    structure_type=llm_result.structure_type,
    semantic_type=llm_result.semantic_type,
    ...
)
```

### 5. `append_content_type` 处理

escalate_node 原有的 `store.append_content_type(llm_result.model_dump())` 用于动态扩展类型。重构后，`create_new` 行为改为向 `semantic_types` 列表追加新条目，`RulesStore.append_content_type` 改名为 `append_semantic_type`，只追加 semantic 维度（structure 类型固定，不允许动态扩展）。

## 依赖关系

- 前置：Spec 03（TypedSegment 字段确定）
- 前置：Spec 06（RulesStore 新 getter 方法确定）
- 同步：`EscalateOutput` 修改与 Spec 02 的 `SegmentItem` 修改在同一文件（`output.py`）

## 受影响文件

- `app/core/parser_workflow/nodes/escalate_node.py`（prompt 和字段引用更新）
- `app/core/parser_workflow/nodes/output.py`（修改 `EscalateOutput`）
- `app/core/parser_workflow/rules.py`（`append_content_type` 改为 `append_semantic_type`）
