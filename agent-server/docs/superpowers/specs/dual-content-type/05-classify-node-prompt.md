# Spec 05：classify_node prompt 重写

## 问题现象

classify_node 的 LLM prompt 存在以下问题：

1. `format_example` 中只有 `content_type` 单字段，LLM 无法返回双字段
2. 类型列表来自 `content_type_rules.json` 的旧 `content_types` 数组，重构后该数组不再存在
3. prompt 中唯一的 GB 标准示例只针对前言（preface），其余章节无任何领域示例，导致分类依赖 LLM 通用理解而非 GB 标准结构知识
4. 置信度 `0.0-1.0的浮点数` 的描述过于宽泛，没有给出判断标准

## 根因

当前 prompt 构建逻辑（`classify_node.py` 中 `_call_classify_llm`）：

```python
type_descriptions = "\n".join(
    f"- {ct['id']}: {ct['description']}" for ct in content_types
)
prompt = f"""请将以下文本拆分为语义独立的片段，并分析每个片段的 content_type 和置信度（0-1）。

可用的 content_type：
{type_descriptions}
...
文本内容：
{chunk_content}
"""
```

整个 prompt 以单维度思维设计，类型列表是平铺的，没有结构/语义的区分引导，LLM 需要同时做"切分"和"分类"两件事，互相干扰。

## 发现方式

查看 `classify_node.py` 第 20-55 行的 `_call_classify_llm` 函数，分析：

1. `content_types` 从 `ct_rules.get("content_types", [])` 取得，重构后该 key 不再存在，将返回空列表
2. `format_example` 中的 `"content_type": "content_type_id"` 与新 schema 不匹配
3. 运行测试观察实际分类结果（见 JSONL artifacts）：A.3.1 试剂和材料 → `numbered_list`，A.3.3 分析步骤 → `numbered_list`，两者无法区分

## 方案

重写 `_call_classify_llm`，改为**两步独立推断**：

```
步骤1：判断呈现形式（structure_type）
  → 只看内容的视觉形态，不考虑用途
  → 可选值：paragraph | list | table | formula | header

步骤2：判断用途（semantic_type）
  → 只考虑"用户会为了什么目的查这段内容"
  → 可选值：metadata | scope | limit | procedure | material | calculation | definition | amendment
```

prompt 结构调整为：

1. 分段切分指令（不变）
2. 结构类型列表（来自 `structure_types`，含 id + description + examples）
3. 语义类型列表（来自 `semantic_types`，含 id + description + examples）
4. 两步推断说明：明确两个维度独立判断，互不干扰
5. format_example 更新为双字段

```python
format_example = """{
    "segments": [
        {
            "content": "片段文本内容",
            "structure_type": "list",
            "semantic_type": "material",
            "confidence": 0.95
        }
    ]
}"""
```

`confidence` 的含义调整为：**对 semantic_type 判断的把握程度**（structure_type 通常可确定，语义判断更易出现不确定）。

## 依赖关系

- 前置：Spec 01（类型列表确定）
- 前置：Spec 02（SegmentItem 字段确定，prompt format_example 需与之一致）
- 同步：`classify_node.py` 中读取 rules 的方式需从 `ct_rules.get("content_types", [])` 改为分别读取 `structure_types` 和 `semantic_types`

## 受影响文件

- `app/core/parser_workflow/nodes/classify_node.py`（重写 `_call_classify_llm`，更新 `classify_raw_chunk` 中的 rules 读取逻辑）
