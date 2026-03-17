# Spec P1-02：slice_node 切分粒度不一致（A.9 与 A.2-A.8 不对等）

## 问题现象

附录 A 中的同级 `##` 标题节（A.2-A.9），切分结果粒度不一致：

| 节 | char_count | 切分结果 |
|---|---|---|
| A.2 鉴别试验 | 1343 | 1 个 chunk，内含 A.2.1-A.2.2 子节 |
| A.3 硫酸酯测定 | 1338 | 1 个 chunk，内含 A.3.1-A.3.4 子节 |
| A.4 黏度测定 | 734 | 1 个 chunk |
| A.5-A.8 | 89~816 | 各 1 个 chunk |
| **A.9 残留溶剂测定** | **24（头）+ 子节** | **7 个 chunk**（空头 + A.9.1-A.9.6）|

A.9 被拆分为 7 个 chunk，而结构完全相同的 A.3（同样有四级子节）却作为整体保留，造成：

1. A.9 子节（如 A.9.6 结果计算）被独立分类，结果准确；A.3 子节混入大 chunk，分类质量下降（见 P1-01 Spec）
2. A.9 产生一个只含标题的空 chunk（chunk[16]，char_count=24），无实质内容
3. 同级章节的 RAG 检索粒度不对等，影响召回质量

## 根因

`slice_node.py` 的 `recursive_slice` 逻辑：

```python
# slice_node.py
if char_count <= soft_max or len(heading_levels) <= 1:
    # 保持为单一 chunk
    result.append(RawChunk(...))
else:
    # 超出 soft_max，递归拆分为下级标题
    result.extend(recursive_slice(block, heading_levels[1:], path, ...))
```

`CHUNK_SOFT_MAX_DEFAULT = 1500`。

**A.9 为何被拆分？**

slice_node 按 `## ` 标题切分时，"A.9 残留溶剂测定"的 block 包含从 `## A.9` 到文档末尾的全部内容（含 A.9.1-A.9.6 所有子节），总字符数约为 **2777 chars**，超过 soft_max=1500，触发递归拆分。

**A.3 为何不被拆分？**

A.3 的 block 共 1338 chars，低于 soft_max=1500，直接作为单一 chunk 保留，内部的 A.3.1-A.3.4 子节不再拆分。

**空 chunk 的产生机制：**

recursive_slice 对 A.9 按 `### ` 标题拆分时，`## A.9 残留溶剂（异丙醇、甲醇）的测定\n\n` 这部分（标题行 + 空行，24 chars）被作为"第一个 `###` 标题前的内容"保留为独立 chunk，形成空头 chunk。

## 发现方式

**第一步：** 查看 slice_node 输出的 char_count 分布：

```bash
cat tests/artifacts/parser_workflow_updates_*.jsonl | python3 -c "
import json, sys
lines = sys.stdin.read().strip().split('\n')
obj = json.loads(lines[3])  # slice_node
for c in obj['node_output']['raw_chunks']:
    print(c['char_count'], c['section_path'])
"
```

确认 A.9 系列是 7 个 chunk，A.3 是 1 个 chunk。

**第二步：** 阅读 `slice_node.py` 第 52-59 行，确认 soft_max 触发逻辑：

```python
if char_count <= soft_max or len(heading_levels) <= 1:
    result.append(RawChunk(...))
else:
    result.extend(recursive_slice(...))
```

**第三步：** 计算 A.9 完整内容的字符数：

A.9.1(132) + A.9.2(50) + A.9.3(507) + A.9.4(152) + A.9.5(1010) + A.9.6(902) + 标题头(24) ≈ 2777 chars > soft_max(1500)。

## 方案

本问题有两个修复思路，需权衡：

### 方案 A：提高 soft_max（最简单）

将 `CHUNK_SOFT_MAX_DEFAULT` 从 1500 提升到 3000（与 `CHUNK_HARD_MAX_DEFAULT` 对齐）。

A.9 总长约 2777 chars，低于新 soft_max，不再拆分，与 A.2-A.8 保持一致。

**优点**：一行改动，立竿见影。
**缺点**：掩盖了 soft_max 设计意图，未来更长的章节仍会出现不一致。

### 方案 B：在 soft_max 超限时保留整节，仅记录警告（推荐）

修改 `recursive_slice`：当某节超出 soft_max 时，**优先检查是否所有子节都超出 hard_max**，若否则整体保留（不拆分），仅追加 WARN。

```python
if char_count <= soft_max or len(heading_levels) <= 1:
    result.append(RawChunk(...))
    if char_count > hard_max:
        errors.append(f"WARN: ...")
else:
    # 修改：检查子节是否真的需要拆分
    sub_parts = _split_by_heading(block, heading_levels[1])
    # 如果子节中没有单节超过 hard_max，保留整节
    if all(len(p[1]) <= hard_max for p in sub_parts):
        result.append(RawChunk(content=block, section_path=path, char_count=char_count))
        errors.append(f"INFO: soft_max exceeded but kept as single chunk at {path}")
    else:
        result.extend(recursive_slice(block, heading_levels[1:], path, ...))
```

**优点**：语义完整的章节不会因为略超 soft_max 而被拆分；只有真正过长（接近 hard_max）的子节才拆分。
**缺点**：逻辑稍复杂，需要更新测试。

**推荐方案 B**。soft_max 的本意是"软警戒线，超过才考虑拆分"，而不是"必须拆分线"。当前实现将 soft_max 作为了强制拆分阈值。

## 依赖关系

- 无强制前置依赖，可独立修复
- 修复后 P1-01（公式分类不稳定）问题会部分缓解（A.9.6 不再是独立 chunk，但 classify_node prompt 规则仍应保留）

## 受影响文件

- `app/core/parser_workflow/nodes/slice_node.py`（修改 `recursive_slice` 逻辑）
- `app/core/parser_workflow/config.py`（若选方案 A，调整 `CHUNK_SOFT_MAX_DEFAULT`）
- `tests/core/parser_workflow/`（相关切分测试断言更新）
