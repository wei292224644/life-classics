# Spec P2-01：空 parent chunk 进入 RAG 索引

## 问题现象

slice_node 输出中存在 3 个内容几乎为空的 chunk，它们只包含一个 Markdown 标题行，无任何实质内容：

| chunk index | section_path | content | char_count |
|---|---|---|---|
| [3] | `['2 技术要求']` | `# 2 技术要求\n\n` | 10 |
| [7] | `['附录 A 检验方法']` | `# 附录 A 检验方法\n\n` | 13 |
| [16] | `['附录 A 检验方法', 'A.9 残留溶剂（异丙醇、甲醇）的测定']` | `## A.9 残留溶剂（异丙醇、甲醇）的测定\n\n` | 24 |

这 3 个 chunk 经过 classify_node 后被分类为 `structure_type=header`（或旧体系的 `plain_text`），最终进入 transform_node 并写入 RAG 向量库，造成：

1. 索引中存在内容为空的 chunk，检索时可能被错误召回
2. transform_node 对这些 chunk 调用 LLM 进行无意义的转写，浪费 token
3. 增加 RAG 向量库中的噪声条目

## 根因

`slice_node.py` 中 `recursive_slice` 的拆分机制：当一个 `##` 级 block 超过 `soft_max` 时，按 `###` 标题拆分，第一个 `###` 标题之前的内容（即 `##` 标题行 + 紧随的空行）作为独立 chunk 保留。

chunk[3] 和 chunk[7] 的产生机制略有不同：它们是原文档中确实存在的纯标题节（Markdown 中 `# 2 技术要求` 后直接跟下级 `## 2.1 ...` 标题，无正文），因此在按 level 1 切分时产生了空 block。

```
# 2 技术要求           ← level 1 标题
                       ← 无正文，直接是下级标题
## 2.1 感官要求        ← 由 level 2 切分处理
```

slice_node 当前无任何过滤逻辑：只要 `block.strip()` 非空（标题行本身不为空），就会生成 chunk：

```python
# slice_node.py
for title, block in parts:
    if not block.strip() and not title:   ← 只过滤 title 和 block 均为空的情况
        continue
    path = parent_path + ([title] if title else [])
    result.append(RawChunk(content=block, ...))
```

标题行本身（如 `# 2 技术要求\n\n`）的 `strip()` 为空，但该 block 是通过 `title="2 技术要求"` 匹配到的，因此 `not title` 为 False，跳过条件不成立，chunk 仍被生成。

## 发现方式

**第一步：** 查看 slice_node 输出中 char_count 极小的 chunk：

```bash
cat tests/artifacts/parser_workflow_updates_*.jsonl | python3 -c "
import json, sys
lines = sys.stdin.read().strip().split('\n')
obj = json.loads(lines[3])  # slice_node
for i, c in enumerate(obj['node_output']['raw_chunks']):
    if c['char_count'] < 50:
        print(f'[{i}] char_count={c[\"char_count\"]} path={c[\"section_path\"]} content={repr(c[\"content\"])}')
"
```

输出：
```
[3]  char_count=10  path=['2 技术要求']              content='# 2 技术要求\n\n'
[7]  char_count=13  path=['附录 A 检验方法']          content='# 附录 A 检验方法\n\n'
[16] char_count=24  path=[..., 'A.9 残留溶剂...']    content='## A.9 残留溶剂（异丙醇、甲醇）的测定\n\n'
```

**第二步：** 查看 `slice_node.py` 第 48-57 行的过滤条件，确认缺少对"仅含标题行"的 block 的过滤。

## 方案

在 `slice_node.py` 的 `recursive_slice` 中增加过滤逻辑：**如果 block 去除 Markdown 标题行后无实质内容，则跳过该 chunk**。

```python
def _has_body_content(block: str) -> bool:
    """
    判断 block 是否有标题行以外的实质内容。
    去除所有以 # 开头的行后，检查剩余内容是否非空。
    """
    lines = block.splitlines()
    body = "\n".join(line for line in lines if not line.startswith("#"))
    return bool(body.strip())


# recursive_slice 中替换原有的追加逻辑：
for title, block in parts:
    if not block.strip() and not title:
        continue
    if not _has_body_content(block):      ← 新增：跳过纯标题 chunk
        continue
    path = parent_path + ([title] if title else [])
    result.append(RawChunk(content=block, section_path=path, char_count=len(block)))
```

**注意：** 过滤掉的空 chunk 不应影响 `section_path` 的构建。子节的 `section_path` 包含父节标题是在 `recursive_slice` 的递归调用中通过 `parent_path + [title]` 传入的，与父节 chunk 是否存在无关，因此过滤掉空父节 chunk 不影响子节的层级路径。

## 依赖关系

- 无强制前置依赖，可独立修复
- 与 P1-02（slice_node 切分粒度）在同一文件修改，建议合并实施

## 受影响文件

- `app/core/parser_workflow/nodes/slice_node.py`（新增 `_has_body_content` 函数，修改 `recursive_slice` 过滤逻辑）
- `tests/core/parser_workflow/`（切分测试中验证空 chunk 不再产生）
