# 设计文档：slice_node soft_max 语义修复 + 空头 chunk 过滤

**日期**：2026-03-17
**问题来源**：p1-slice-node-inconsistent-granularity.md、p2-empty-parent-chunk-filter.md
**受影响文件**：`app/core/parser_workflow/nodes/slice_node.py`

---

## 问题摘要

本文档合并修复两个相关问题，它们都在 `slice_node.py` 的 `recursive_slice` 中，建议一并实施：

**P1-02（粒度不一致）**：`recursive_slice` 将 `soft_max` 作为强制拆分阈值——任何超过 1500 chars 的 block 都会被递归拆分。导致同级章节产生粒度不一致的 chunk（A.3 = 1338 chars → 1 chunk；A.9 = 2777 chars → 7 chunks）。

**P2-01（空头 chunk）**：`recursive_slice` 缺少对"仅含标题行"的 block 的过滤。`block.strip()` 对于 `## A.9 ...\n\n` 这类 block 不为空（标题行本身非空），因此原有的 `not block.strip() and not title` 过滤条件不生效，导致空内容 chunk 进入 RAG 索引。

---

## 设计目标

1. `soft_max` 恢复"软警戒线"语义：超过时先评估是否真的需要拆分
2. 只有当拆出的子节中存在超过 `hard_max` 的节时，才触发递归拆分（仅检查一层，见下方说明）
3. 过滤"仅含标题行"的 block，不生成空内容 chunk
4. 不改变外部接口，不影响其他节点

---

## 核心逻辑变更

### 变更一：新增 `_has_body_content` 辅助函数

```python
def _has_body_content(block: str) -> bool:
    """
    判断 block 是否有标题行以外的实质内容。
    去除所有以 # 开头的行后，检查剩余内容是否非空。
    """
    lines = block.splitlines()
    body = "\n".join(line for line in lines if not line.startswith("#"))
    return bool(body.strip())
```

这是修复 P2-01 的正确方式。对于 `## A.9 残留溶剂...\n\n`，`block.strip()` 不为空，但 `_has_body_content` 返回 False，因此该 chunk 被跳过。

### 变更二：修改 `recursive_slice` 中的 block 处理逻辑

**当前逻辑（有问题）**：

```python
for title, block in parts:
    if not block.strip() and not title:
        continue
    path = parent_path + ([title] if title else [])
    char_count = len(block)
    if char_count <= soft_max or len(heading_levels) <= 1:
        result.append(RawChunk(...))
    else:
        result.extend(recursive_slice(...))  # 超过 soft_max 必然递归
```

**修改后逻辑**：

```python
for title, block in parts:
    if not block.strip() and not title:
        continue
    path = parent_path + ([title] if title else [])
    char_count = len(block)
    if char_count <= soft_max or len(heading_levels) <= 1:
        # P2-01 修复：过滤仅含标题行的 block
        if _has_body_content(block):
            result.append(RawChunk(content=block, section_path=path, char_count=len(block)))
    else:
        # P1-02 修复：soft_max 超限时，检查子节是否真的需要拆分
        # 仅检查直接子节（heading_levels[1]）一层，不递归检查孙节，
        # 因为孙节超限会在下层递归中自行处理（有意设计）
        sub_parts = _split_by_heading(block, heading_levels[1])
        # 过滤空子节（纯标题行），避免影响 any_sub_exceeds_hard 的判断
        any_sub_exceeds_hard = any(
            len(p[1]) > hard_max for p in sub_parts if p[1].strip()
        )
        if not any_sub_exceeds_hard:
            # 所有直接子节均在 hard_max 以内，整体保留
            # 注：不需要 _has_body_content 检查——block > soft_max > 1500，不可能是纯标题行
            errors.append(f"INFO: soft_max exceeded but kept as single chunk at {path}")
            result.append(RawChunk(content=block, section_path=path, char_count=len(block)))
        else:
            result.extend(
                recursive_slice(block, heading_levels[1:], path, soft_max, hard_max, errors)
            )
```

### 关于"仅检查一层"的说明

`any_sub_exceeds_hard` 只检查直接子节（`heading_levels[1]` 级），不递归检查孙节。这是有意设计：若某个直接子节本身不超 `hard_max`，但其孙节超了 `hard_max`，整体保留后孙节超限会通过 WARN 日志体现，不触发拆分。

这符合"软警戒线"的原则——只要当前切分结果中没有 chunk 超过硬限制，就不强制拆分。

---

## 预期效果

| chunk | 修改前 | 修改后 |
|---|---|---|
| chunk[3]（`# 2 技术要求\n\n`，仅标题）| 进入 RAG 索引 | 被过滤，不生成 |
| chunk[7]（`# 附录 A 检验方法\n\n`，仅标题）| 进入 RAG 索引 | 被过滤，不生成 |
| chunk[16]（`## A.9 ...\n\n`，空头）| 进入 RAG 索引 | 被过滤，不生成（P1-02 修复后本节不会再被拆分，此 chunk 不产生）|
| A.3（1338 chars）| 1 个 chunk | 1 个 chunk（不变）|
| A.9（2777 chars）| 7 个 chunk | 1 个 chunk |
| 超过 hard_max 的节 | 递归拆分 | 仍然递归拆分（行为不变）|

---

## 测试策略

新增单元测试（`tests/core/parser_workflow/test_slice_node.py`）覆盖以下场景：

1. **soft_max < block < hard_max，子节均不超 hard_max** → 整体保留为 1 个 chunk，`errors` 中含 INFO 日志
2. **soft_max < block，存在子节超 hard_max** → 触发递归拆分
3. **仅含标题行的 block**（如 `## A.9 残留溶剂...\n\n`）→ 不生成 chunk（注意：`block.strip()` 不为空，必须用 `_has_body_content` 判断）
4. **block <= soft_max，有实质内容** → 正常生成 chunk（回归测试）
5. **block <= soft_max，仅含标题行** → 不生成 chunk（P2-01 回归测试）
6. **heading_levels 只剩 1 级** → 强制整体保留（回归测试）
7. **A.9 场景模拟**：构造 `soft_max=1500` 下总长 ~2777 chars、各子节均不超 `hard_max=3000` 的文本 → 整体保留为 1 个 chunk

---

## 不在范围内

- 不修改 `CHUNK_SOFT_MAX_DEFAULT` 或 `CHUNK_HARD_MAX_DEFAULT` 的值
- 不修改 `_split_by_heading` 的逻辑
- 不涉及 `classify_node` 或其他节点

---

## 受影响文件

- `app/core/parser_workflow/nodes/slice_node.py`
  - 新增 `_has_body_content(block: str) -> bool` 函数
  - 修改 `recursive_slice` 的 block 处理逻辑
- `tests/core/parser_workflow/test_slice_node.py`（新增测试用例）
