# Spec P1-01：结果计算节中公式分类依赖 chunk 粒度，不稳定

## 问题现象

同为"结果计算"节（包含 `$$...$$` LaTeX 公式），分类结果不一致：

| chunk | 节名 | classify_node 输出 |
|---|---|---|
| chunk[10] seg[4] | A.3.4 结果计算 | `plain_text`（confidence=0.96）|
| chunk[13] seg[4] | A.6.4 结果计算 | `plain_text`（confidence=0.85）|
| chunk[14] seg[4] | A.7.4 结果计算 | `plain_text`（confidence=0.93）|
| chunk[22] | A.9.6 结果计算 | `formula`（confidence=0.98）✓ |

A.9.6 被正确分类，A.3.4 / A.6.4 / A.7.4 却被错误归为 `plain_text`。

## 根因

原因在于 **slice_node 切分粒度**决定了 classify_node 每次调用能看到的上下文范围：

- **A.9.6**：由于 A.9 整体超过 `soft_max=1500` 字符，slice_node 将其拆分为 A.9.1-A.9.6 独立 chunk。A.9.6（902 chars）是一个**独立 chunk**，LLM 看到的全部内容就是公式 + 变量说明，能准确识别为 `formula`。

- **A.3.4 / A.6.4 / A.7.4**：它们所在的 A.3（1338 chars）、A.6（629 chars）、A.7（816 chars）均未超过 soft_max，整节作为**单一 chunk** 送入 classify_node。LLM 需要在同一个 chunk 内同时处理试剂列表、仪器列表、分析步骤、结果计算多个子节，倾向于将结果计算节归为 `plain_text`（因为它夹在大量 `numbered_list` 和 `plain_text` 内容中）。

本质：**classify_node 的分类质量对 chunk 大小和内部结构敏感**。当结果计算节作为大 chunk 的最后一个子节出现时，LLM 受前面内容影响，降低了对公式的识别敏感度。

## 发现方式

**第一步：** 对比 JSONL artifacts 中 classify_node 输出的各段 content_type：

```bash
# 查看 A.3、A.6、A.7 的结果计算段
cat tests/artifacts/parser_workflow_updates_*.jsonl | python3 -c "
import json, sys
lines = sys.stdin.read().strip().split('\n')
obj = json.loads(lines[4])  # classify_node output
for chunk in obj['node_output']['classified_chunks']:
    for seg in chunk['segments']:
        if '结果计算' in seg.get('content', ''):
            print(chunk['raw_chunk']['section_path'], '->', seg['content_type'], seg['confidence'])
"
```

输出：
```
['附录 A 检验方法', 'A.3 硫酸酯...'] -> plain_text 0.96   ← 错误
['附录 A 检验方法', 'A.6 酸不溶灰分...'] -> plain_text 0.85  ← 错误
['附录 A 检验方法', 'A.7 酸不溶物...'] -> plain_text 0.93  ← 错误
['附录 A 检验方法', 'A.9 ...', 'A.9.6 结果计算'] -> formula 0.98  ← 正确
```

**第二步：** 确认根因是 chunk 粒度差异：

```bash
# 查看 A.3、A.9.6 的 char_count
cat tests/artifacts/parser_workflow_updates_*.jsonl | python3 -c "
import json, sys
lines = sys.stdin.read().strip().split('\n')
obj = json.loads(lines[3])  # slice_node output
for chunk in obj['node_output']['raw_chunks']:
    print(chunk['section_path'][-1], ':', chunk['char_count'])
"
```

A.3 = 1338 chars（低于 soft_max 1500，不拆分），A.9.6 = 902 chars（独立 chunk）。

## 方案

在 classify_node prompt 中增加一条**显式规则**：

> 若 segment 内容包含 `$$...$$` 或 `$...$` 的 LaTeX 公式块，则无论上下文如何，该 segment 的 `structure_type` 必须为 `formula`。

实现方式：在 prompt 的"保守切分原则"部分追加：

```
公式识别规则：
- 文本中出现 $$...$$ 块级公式时，该部分及其紧邻的变量说明（"式中：m1——..."格式）应作为独立 segment，structure_type=formula，semantic_type=calculation。
- 不得因上下文中存在大量列表或段落而将含公式的内容归为 plain_text。
```

此规则为**确定性规则**，不依赖 LLM 语义理解，属于 prompt 层面的强约束。

**注意：** 此问题在 Spec 01（双字段体系）实施后，通过 `semantic_type=calculation` 配合 `structure_type=formula` 能更清晰表达，但 prompt 强约束规则独立有效，应在新旧体系下均加入。

## 依赖关系

- 无强制前置依赖，可独立修复
- 与 dual-content-type Spec 05 同在 `classify_node.py` 中修改，建议合并实施

## 受影响文件

- `app/core/parser_workflow/nodes/classify_node.py`（prompt 中增加公式识别规则）
