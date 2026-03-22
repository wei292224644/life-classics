# parse_node standard_no 提取优先级修复

**日期：** 2026-03-22
**状态：** 已批准

## 问题

90% 的入库文档 `standard_no` 不正确：
- 要么是 UUID（原代码 fallback 为 `doc_id`，注：原注释称"文件名去扩展名"有误，实为 UUID）
- 要么是文档内容中引用的其他 GB 标准编号，而非本文档自身的编号

**根因：** `parse_node` 在提取 `standard_no` 时，直接用正则搜索整个 `md_content`，匹配到文档正文中**第一个出现的 GB 编号**（可能是被引用的其他标准），而非文档自身的标准编号。如果正则未匹配，则 fallback 成 UUID（无业务意义）。

文档 title（由上传文件名去扩展名得到，如 `"GB 29701-2013 鸡可食性组织..."`）才是最可靠的标准编号来源。

## 设计

### 改动范围

仅修改 `server/parser/nodes/parse_node.py`，调整 `standard_no` 的提取优先级。

### 新提取逻辑

parse_node 函数内部，title 填充（从 `# 标题` 提取）发生在 standard_no 提取之前，两者均在同一节点内按顺序执行。

```
1. meta["standard_no"] 已有非空值 → 跳过（空字符串视为无值，继续提取）
2. 从 meta["title"] 提取正则，取第一个匹配 → 命中则使用
3. title 未命中 → 从 md_content 全文提取正则，取第一个匹配 → 命中则使用
4. 均未命中 → 记录 WARNING，不向 meta 写入 standard_no key（key 不存在）
```

**title 来源说明：**
- 若调用方传入文件名（如 `"GB 29701-2013 鸡可食性组织..."`），title 即含标准编号 → 步骤 2 命中
- 若 title 由 parse_node 从正文第一个 `# 标题` 行填充（如 `"食品安全国家标准 鸡可食性组织..."`），通常不含 GB 编号 → 步骤 2 静默失败，降级到步骤 3

**去除 UUID fallback：** 原代码在正则未命中时将 `doc_id`（UUID）赋给 `standard_no`，没有业务意义，改为记录 WARNING 并不写入该 key。同步修正原代码中的误导性注释（原注释称 doc_id 为"文件名去扩展名"，实为 UUID）。

### 正则（不变）

```
GB[\s_]?\d+(?:[.\d]*)?(?:\.\d+)?-\d{4}
```

**格式说明：**
- 当前数据集文件名均为 `GB XXXXX-YYYY` 格式（纯 GB，无 GB/T）
- GB/T 类编号（含斜杠）不在本次修复范围内，如后续有需要可单独扩展正则

**验证示例：** `"GB 29701-2013 鸡可食性组织..."` → 匹配 `"GB 29701-2013"`，符合预期。

### 受影响的文件

| 文件 | 改动类型 |
|------|----------|
| `server/parser/nodes/parse_node.py` | 修改提取优先级，去除 UUID fallback，修正误导性注释 |
| `server/tests/core/parser_workflow/test_parse_node_real.py` | 替换全部注释代码，改用内联 fixture（不依赖 test_utils），新增 title 优先提取场景 |

### 不改动

- `server/parser/graph.py` — 无需在 workflow 入口预提取
- `server/scripts/batch_upload.py` — 无需改动
- 其他 parser 节点

## 测试策略

新测试用例均使用内联 fixture（不依赖 `test_utils`），原注释代码全部替换。

| # | 场景 | 输入 | 预期结果 |
|---|------|------|----------|
| 1 | **title 有效，content 含其他 GB 编号** | title=`"GB 29701-2013 ..."`, content 含 `"GB 1234-2020"` | `standard_no = "GB 29701-2013"`（title 优先） |
| 2 | **title 无效，content 有效** | title=`"食品安全国家标准 ..."`, content 含 `"GB 29701-2013"` | `standard_no = "GB 29701-2013"` |
| 3 | **title 由 `# 标题` 填充（不含 GB 编号），content 有效** | meta 无 title，正文首行 `# 食品安全国家标准 鸡可食性组织`, content 含 `"GB 29701-2013"` | parse_node 先将 title 补全为 `"食品安全国家标准 鸡可食性组织"`，步骤 2 对 title 的正则未命中，降级到步骤 3，最终 `standard_no = "GB 29701-2013"` |
| 4 | **均无效** | title 无 GB 编号，content 也无 GB 编号 | `standard_no` key 不存在，`errors` 含 `"WARNING: doc_metadata missing 'standard_no'"` |
| 5 | **已有非空值** | meta 已含 `standard_no: "GB 29701-2013"` | 不覆盖 |
| 6 | **空字符串值** | meta 含 `standard_no: ""` | 视为无值，继续提取 |
| 7 | **title 含多个 GB 编号** | title=`"GB 29701-2013 关于 GB 1234-2020 的引用"` | 取第一个：`"GB 29701-2013"` |

## 修复方式

1. 先清空知识库（`DELETE /api/kb`）
2. 重新上传所有文档（不需要回填已有数据，清空后重跑 parser 即可）
