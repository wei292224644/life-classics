# Spec 08：enrich_node / transform_node 适配双字段

## 问题现象

enrich_node 和 transform_node 是 parser_workflow 流水线中读取 `TypedSegment.content_type` 并写入 `DocumentChunk.content_type` 的节点。字段重命名后两个节点均会在运行时抛 KeyError。

## 根因

### enrich_node（两处引用）

```python
# enrich_node.py 第92行：判断 segment 是否含表格
if not any(seg["content_type"] == "table" for seg in cc["segments"]):
    continue

# enrich_node.py 第146行：构造 TypedSegment 时透传 content_type
TypedSegment(
    ...
    content_type=seg["content_type"],
    ...
)
```

第 92 行的判断逻辑依赖 structure 信息（`"table"` 是结构类型），重构后应改用 `structure_type`。
第 146 行是在 enrich_node 内部重建 segment（内联表格引用后），需同步传递两个字段。

### transform_node（一处引用）

```python
# transform_node.py 第78行：构造最终 DocumentChunk
DocumentChunk(
    ...
    content_type=seg["content_type"],
    ...
)
```

此处将 segment 的分类写入最终产出，字段重命名后须同步更新。

## 发现方式

```bash
grep -n "content_type" app/core/parser_workflow/nodes/enrich_node.py
grep -n "content_type" app/core/parser_workflow/nodes/transform_node.py
```

输出共 3 处，全部为字段读取或赋值，无复杂逻辑。

## 方案

### enrich_node 第92行

```python
# 修改前
if not any(seg["content_type"] == "table" for seg in cc["segments"]):

# 修改后
if not any(seg["structure_type"] == "table" for seg in cc["segments"]):
```

### enrich_node 第146行（TypedSegment 重建）

```python
# 修改前
TypedSegment(
    content_type=seg["content_type"],
    ...
)

# 修改后
TypedSegment(
    structure_type=seg["structure_type"],
    semantic_type=seg["semantic_type"],
    ...
)
```

### transform_node 第78行（DocumentChunk 构造）

```python
# 修改前
DocumentChunk(
    ...
    content_type=seg["content_type"],
    ...
)

# 修改后
DocumentChunk(
    ...
    structure_type=seg["structure_type"],
    semantic_type=seg["semantic_type"],
    ...
)
```

## 依赖关系

- 前置：Spec 03（TypedSegment 双字段）
- 前置：Spec 04（DocumentChunk 双字段）
- 无后续依赖，本 spec 是流水线字段传播链的末端

## 受影响文件

- `app/core/parser_workflow/nodes/enrich_node.py`（2处）
- `app/core/parser_workflow/nodes/transform_node.py`（1处）
