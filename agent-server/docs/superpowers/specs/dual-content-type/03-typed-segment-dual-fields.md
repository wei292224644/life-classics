# Spec 03：TypedSegment 双字段替换

## 问题现象

classify_node 将 LLM 输出的 `SegmentItem` 转换为 `TypedSegment` 存入流水线 state，但 `TypedSegment` 同样只有单字段 `content_type`，导致双维度信息无法在流水线内部传递。

## 根因

`TypedSegment` 定义于 `models.py`，是 parser_workflow 内部各节点之间传递 segment 数据的 TypedDict：

```python
# models.py
class TypedSegment(TypedDict):
    content: str
    content_type: str    # 单字段
    transform_params: dict
    confidence: float
    escalated: bool
    cross_refs: List[str]
    ref_context: str
    failed_table_refs: List[str]
```

classify_node 在构造 `TypedSegment` 时直接将 `item.content_type` 写入：

```python
# classify_node.py
seg = TypedSegment(
    content=item.content,
    content_type=ct_id,       ← 单字段赋值
    transform_params=transform_params,
    ...
)
```

该字段随后被 enrich_node、transform_node 读取。

## 发现方式

在 `models.py` 中搜索 `TypedSegment`，查看字段定义：

```
app/core/parser_workflow/models.py 第17行：content_type: str
```

再搜索所有引用 `content_type` 字段的地方（读取 TypedSegment 的节点）：

```bash
grep -n 'content_type' app/core/parser_workflow/nodes/*.py
```

输出：
- `classify_node.py:82` — 写入 `content_type="unknown"`
- `classify_node.py:99` — 写入 `content_type=ct_id`
- `enrich_node.py:92` — 读取 `seg["content_type"] == "table"`
- `enrich_node.py:146` — 读取 `content_type=seg["content_type"]`
- `transform_node.py:78` — 读取 `content_type=seg["content_type"]`
- `escalate_node.py:72` — 读取 `seg["content_type"] != "unknown"`
- `escalate_node.py:84` — 写入 `content_type=new_ct_id`

## 方案

将 `TypedSegment` 的 `content_type` 替换为两个字段：

```python
# 修改前
class TypedSegment(TypedDict):
    content: str
    content_type: str
    ...

# 修改后
class TypedSegment(TypedDict):
    content: str
    structure_type: str
    semantic_type: str
    ...
```

**涉及所有写入点的更新：**

| 位置 | 旧写法 | 新写法 |
|---|---|---|
| `classify_node.py:82` | `content_type="unknown"` | `structure_type="unknown", semantic_type="unknown"` |
| `classify_node.py:99` | `content_type=ct_id` | `structure_type=item.structure_type, semantic_type=item.semantic_type` |
| `escalate_node.py:84` | `content_type=new_ct_id` | 见 Spec 07 |

**涉及所有读取点的更新：**

| 位置 | 说明 |
|---|---|
| `enrich_node.py:92` | 判断是否含表格，改用 `structure_type == "table"` |
| `enrich_node.py:146` | 传递给 DocumentChunk，见 Spec 08 |
| `transform_node.py:78` | 传递给 DocumentChunk，见 Spec 08 |
| `escalate_node.py:72` | 判断 unknown，改用 `seg["semantic_type"] != "unknown"` |

## 依赖关系

- 前置：Spec 02（TypedSegment 从 SegmentItem 读取字段，字段名需一致）
- 后置：Spec 05（classify_node 写入 TypedSegment 的逻辑需同步）
- 后置：Spec 07（escalate_node 读写 TypedSegment 需同步）
- 后置：Spec 08（enrich_node、transform_node 读取 TypedSegment 需同步）

## 受影响文件

- `app/core/parser_workflow/models.py`（修改 `TypedSegment`）
