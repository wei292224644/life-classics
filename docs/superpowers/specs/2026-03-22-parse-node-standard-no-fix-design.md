# parse_node standard_no 提取优先级修复

**日期：** 2026-03-22
**状态：** 已批准

## 问题

90% 的入库文档 `standard_no` 不正确：
- 要么是 UUID（`doc_id` 的 fallback）
- 要么是文档内容中引用的其他 GB 标准编号，而非本文档自身的编号

**根因：** `parse_node` 在提取 `standard_no` 时，直接用正则搜索整个 `md_content`，匹配到文档正文中**第一个出现的 GB 编号**（可能是被引用的其他标准），而非文档自身的标准编号。如果正则未匹配，则 fallback 成 UUID。

文档 title（由上传文件名去扩展名得到，如 `"GB 29701-2013 鸡可食性组织..."`）才是最可靠的标准编号来源。

## 设计

### 改动范围

仅修改 `server/parser/nodes/parse_node.py`，调整 `standard_no` 的提取优先级。

### 新提取逻辑

```
1. meta["standard_no"] 已有值 → 跳过
2. 从 meta["title"] 提取正则匹配 → 命中则使用
3. title 未命中 → 从 md_content 全文提取正则匹配 → 命中则使用
4. 均未命中 → 记录 WARNING，standard_no 不设值（不再 fallback 成 doc_id）
```

**去除 UUID fallback：** 原代码在正则未命中时将 `doc_id`（UUID）赋给 `standard_no`，这没有业务意义，改为记录警告并留空。

### 正则（不变）

```
GB[\s_]?\d+(?:[.\d]*)?(?:\.\d+)?-\d{4}
```

### 受影响的文件

| 文件 | 改动类型 |
|------|----------|
| `server/parser/nodes/parse_node.py` | 修改提取优先级，去除 UUID fallback |
| `server/tests/core/parser_workflow/test_parse_node_real.py` | 补充 title 优先提取的测试用例（如有该文件） |

### 不改动

- `server/parser/graph.py` — 无需在 workflow 入口预提取
- `server/scripts/batch_upload.py` — 无需改动
- 其他 parser 节点

## 测试策略

1. **title 有效**：title 含 GB 编号，content 也含其他 GB 编号 → 应取 title 的
2. **title 无效，content 有效**：title 无 GB 编号，content 有 → 应取 content 的
3. **均无效**：title 和 content 均无 GB 编号 → standard_no 为空，errors 含 WARNING
4. **已有值**：meta 已含 standard_no → 不覆盖

## 修复方式

重新上传所有文档（不需要回填已有数据）。
