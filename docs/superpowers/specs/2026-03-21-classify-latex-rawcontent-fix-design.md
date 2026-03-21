# classify_node LaTeX 处理 & raw_content 语义修正 设计文档

日期：2026-03-21

## 背景

parser 流水线中 `classify_node` 调用 LLM 进行语义切分与分类时，chunk 内容含有大量 LaTeX 内联公式（`$...$` / `$$...$$`）。LLM 在将这些内容原样输出到 JSON 的 `content` 字段时，反斜杠转义经常出错，导致 instructor 反复重试，最终超时。

同时，`DocumentChunk.raw_content` 当前来源为整个 `raw_chunk["content"]`，在 classify_node 将一个 chunk 切分成多个 segment 的情况下，每个 DocumentChunk 的 `raw_content` 包含了相邻 segment 的内容，与其 `content` 字段不对应，不符合 raw_content 的使用目的（检索命中后发给最终 LLM 作为上下文）。

---

## 问题总结

| # | 位置 | 问题 | 已有状态 |
|---|------|------|---------|
| 1 | `invoker.py` | 超时重试逻辑被注释掉，超时一次即崩溃 | ✅ 已修复 |
| 2 | `classify_node.py` | LaTeX 原样输出至 JSON 导致转义失败/超时 | 待实现（占位符方案） |
| 3 | `transform_node.py` | `raw_content` 范围过宽，与 `content` 不对应 | 待实现 |

---

## 设计方案

### 问题 1：重试逻辑（已完成）

在 `invoker.py` 的 `invoke_structured` 中重新启用对 `TimeoutError` / `ConnectionError` 的重试循环，最大重试次数由 `settings.PARSER_STRUCTURED_MAX_RETRIES` 控制。`PydanticValidationError` 等不可恢复错误仍直接抛出，不重试。

---

### 问题 2：classify_node LaTeX 占位符方案

#### 核心思路

LLM 不需要理解公式内容，只需要做语义切分与分类。因此在送入 LLM 前，将 LaTeX 公式替换为占位符；LLM 输出后，再将占位符还原为原始 LaTeX。

#### 占位符格式

```
[__MATH_0__]  [__MATH_1__]  [__MATH_2__]  ...
```

选用方括号 + 双下划线组合，足够特殊，LLM 不易误改。inline 和 block 公式使用相同格式，通过序号区分。

#### 数据流

```
raw_chunk["content"]（原始，含 LaTeX）
    ↓ _replace_latex_with_placeholders()
clean_text（占位符替换后）+ mapping {[__MATH_N__]: 原始LaTeX}
    ↓ LLM（看到干净文本，切分 + 分类）
segments with placeholders in content
    ↓ _restore_placeholders(seg["content"], mapping)
seg["content"]（占位符还原，内含原始 LaTeX，segment 精准）
```

#### 实现要点

**预处理函数 `_replace_latex_with_placeholders(text)`**
- 先匹配 `$$...$$`（block，跨行），再匹配 `$...$`（inline，单行），顺序不可颠倒
- 返回 `(clean_text, mapping)`，mapping 为 `dict[str, str]`

**后处理函数 `_restore_placeholders(text, mapping)`**
- 按 mapping 的插入顺序遍历（Python 3.7+ dict 有序），逐一将占位符替换回原始 LaTeX。由于占位符格式唯一且不会出现在 LaTeX 内容中，遍历顺序对结果无影响。
- 容错范围：仅处理占位符前后的多余空格（如 `[ __MATH_0__ ]`）；不处理占位符内部变体（大小写变化、下划线数量变化视为 LLM 输出错误）。
- **失败处理**：若某个占位符在 LLM 输出的 segment content 中未找到（LLM 删除或严重修改了占位符），则保留该 segment content 原样，不抛出异常——classify 阶段的主要目的是切分与分类，个别占位符丢失不应中断整个流水线。后续 transform_node 会收到含残留占位符的文本，其 `prompt_template` 会将其作为普通文本处理，不会产生错误结果，只是该公式的 `raw_content` 会含有占位符字符串而非原始 LaTeX。

**清理已有 prompt 指令**
- 删除本次对话中临时加入 classify prompt 末尾的 LaTeX 转换指令（已被占位符方案替代）

**保留 `_escape_for_json_prompt`**
- GB 标准文本中偶有带双引号的条文（如引用其他标准的名称），LaTeX 替换为占位符后这类双引号仍然存在，仍需转义。作为防御性措施保留，不会影响性能。

---

### 问题 3：raw_content 来源修正

#### 修改位置

`transform_node.py`，`apply_strategy` 函数：

```python
# 修改前
raw_content = raw_chunk["content"]

# 修改后
raw_content = seg["content"]
```

#### 效果

- `raw_content` 精准对应当前 segment，不再包含相邻 segment 内容
- `raw_content` 保留原始 LaTeX（由问题 2 的占位符还原保证）
- `content`（LLM 转写后的自然语言）与 `raw_content` 一一对应，语义一致
- transform_node 的各 `prompt_template` 已有 LaTeX → 自然语言指令，正常处理 `seg["content"]` 中的 LaTeX

---

## 完整数据流（修改后）

```
raw_chunk["content"]（原始 LaTeX，整个 chunk）
    │
    ├─ classify_node
    │   ├─ 预处理：LaTeX → [__MATH_N__]
    │   ├─ LLM：切分 + 分类
    │   └─ 后处理：[__MATH_N__] → 原始 LaTeX
    │       → seg["content"]（segment 精准，含原始 LaTeX）
    │       [失败路径] 占位符未找到时：seg["content"] 含残留占位符，流水线继续，不抛异常
    │
    └─ transform_node（依赖 classify_node 后处理已正确执行）
        ├─ raw_content = seg["content"]          → DocumentChunk.raw_content（原始 LaTeX）
        └─ LLM transform(seg["content"])         → DocumentChunk.content（自然语言，用于向量检索）
```

---

## 受影响文件

| 文件 | 改动类型 |
|------|---------|
| `server/parser/structured_llm/invoker.py` | ✅ 已完成，重启重试逻辑 |
| `server/parser/nodes/classify_node.py` | 新增预处理/后处理函数；删除临时 prompt 指令 |
| `server/parser/nodes/transform_node.py` | `raw_content` 来源改为 `seg["content"]` |

---

## 不在本次范围内

- 对 `TypedSegment` 模型增加 `raw_content` 字段（当前 `seg["content"]` 已同时承担两个角色，无需拆分）
- 修改 `slice_node` 的 chunk 粒度控制
- 修改 `transform_node` 的 LaTeX 处理 prompt（已经足够）
