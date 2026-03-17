# Spec 02：SegmentItem / ClassifyOutput 双字段替换

## 问题现象

classify_node 调用 LLM 时，要求返回的 Pydantic 模型 `SegmentItem` 只有一个 `content_type: str` 字段。LLM 被迫将结构和语义信息压缩进同一个值，结果要么偏向形式（`numbered_list`）要么偏向语义（`preface`），两个维度无法同时表达。

## 根因

`SegmentItem` 定义于 `nodes/output.py`，是 classify_node LLM 调用的**输出 schema**（由 `invoke_structured` 强制约束 LLM 返回格式）：

```python
# nodes/output.py
class SegmentItem(BaseModel):
    content: str
    content_type: str     # 单字段，无法同时表达结构和语义
    confidence: float
```

该 schema 直接决定了 LLM 能返回什么结构，是 Spec 01 类型体系变更后必须同步更新的**输出契约**。

## 发现方式

查看 `nodes/output.py` 中 `SegmentItem` 的字段定义，再对照 classify_node prompt 中的 `format_example`：

```python
# nodes/classify_node.py
format_example = """{
    "segments": [
        {
            "content": "片段文本内容",
            "content_type": "content_type_id",   ← 单字段
            "confidence": 0.0-1.0的浮点数
        }
    ]
}"""
```

LLM 的 JSON 输出被 `ClassifyOutput` 解析，`ClassifyOutput.segments` 是 `List[SegmentItem]`，单字段 schema 不允许 LLM 返回两个维度的值。

## 方案

将 `SegmentItem` 的 `content_type` 替换为两个字段：

```python
# 修改前
class SegmentItem(BaseModel):
    content: str
    content_type: str
    confidence: float = Field(default=0.8, ge=0, le=1)

# 修改后
class SegmentItem(BaseModel):
    content: str
    structure_type: str
    semantic_type: str
    confidence: float = Field(default=0.8, ge=0, le=1)
```

`ClassifyOutput` 无需变更（仍为 `segments: List[SegmentItem]`）。

`EscalateOutput` 中也有 `id: str`（对应 content_type_id），其处理方式见 Spec 07，本 spec 不涉及。

## 依赖关系

- 前置：Spec 01（content_type_rules.json 新结构需先确定，SegmentItem 字段名与其对应）
- 后置：Spec 03（TypedSegment 从 SegmentItem 读取数据，需同步更新）
- 后置：Spec 05（classify_node prompt 中 format_example 需与新字段一致）

## 受影响文件

- `app/core/parser_workflow/nodes/output.py`（直接修改 `SegmentItem`）
