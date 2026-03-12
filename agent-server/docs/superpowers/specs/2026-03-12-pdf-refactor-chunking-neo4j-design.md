# PDF 解析重构设计：递归切分 + Neo4j 职责重定位

**日期：** 2026-03-12
**范围：** Phase 2（递归标题切分）、Phase 3（Neo4j 职责）

---

## 背景

现有重构计划（`docs/plans/2026-03-02-full-refactor-implementation-plan.md`）中：

- **Phase 2** 实现了按标题切分，但切分规则不够精确——只是简单地在每个标题处截断，未考虑 chunk 大小控制。
- **Phase 3** 将 Document/Chunk 写入 Neo4j，但这个结构目前没有实际用途，增加了导入复杂度和对 Neo4j 的强依赖。

本文档明确这两个 Phase 的设计决策。

---

## Phase 2：递归标题切分

### 目标

将 MinerU 输出的 Markdown 按标题层级递归切分为 `DocumentChunk` 列表，每块不超过 1500 字符。若最深标题层的内容仍超限，保留整块不强制截断。

### 算法

**函数签名**（对外接口保持向后兼容）：

```python
def split_heading_from_markdown(
    markdown_content: str,
    doc_id: str,
    doc_title: str,
    source: str,
    markdown_id: Optional[str] = None,
    max_chars: int = 1500,
) -> List[DocumentChunk]
```

**处理流程：**

1. **第一遍扫描**：按所有标题（`^#{1,6}\s+`）将 Markdown 切成原始块列表，每块记录 `(level, section_path, content_lines)`。
2. **递归函数** `_try_split(block, current_level)`：
   - 若 `len(content) <= max_chars`：直接产出 `DocumentChunk`
   - 否则：在 `content` 内寻找 `current_level + 1` 级标题
     - 找到 → 将内容按该级标题切分，对每个子块递归调用 `_try_split`
     - 找不到（已是最深层）→ 保留整块，产出 `DocumentChunk`（允许超限）
3. 对所有 L1 原始块调用递归函数，合并结果。

**section_path 继承规则：**

子块的 `section_path` 在父块路径基础上追加子标题：

```
父块: ["第三章 食品添加剂的使用规定"]
子块: ["第三章 食品添加剂的使用规定", "3.4 检验方法"]
```

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_chars` | `1500` | 单块最大字符数，可按文档类型调整 |

**边界行为：**

| 场景 | 处理方式 |
|------|---------|
| 块 ≤ 1500 字符 | 直接产出，不递归 |
| 块 > 1500，有下级标题 | 递归切分 |
| 块 > 1500，无下级标题（最深层） | 保留整块，允许超限 |
| Markdown 无任何标题 | 整个内容作为一个 chunk |

### 涉及文件

- **修改**：`app/core/kb/strategy/heading_strategy.py`（改造 `split_heading_from_markdown` 内部实现）
- **修改**：`tests/core/kb/strategy/test_heading_strategy.py`（补充递归切分测试用例）

---

## Phase 3：Neo4j 职责重定位

### 决策

**从 PDF 导入流程中移除 Document/Chunk 写入 Neo4j**，理由：

- 该结构（`Document -[:CONTAINS]-> Chunk`）当前无实际查询用途
- 增加对 Neo4j 可用性的依赖，导入失败时引入额外噪音
- GB2760 业务图谱（已有 schema + 清洗好的数据）将单独导入，不经过 `import_pdf_via_mineru`

### 变更内容

**`app/core/kb/__init__.py`** 中的 `import_pdf_via_mineru`，删除以下代码：

```python
# 删除此段
try:
    from app.core.kg.neo4j_store import write_document_chunks_safe
    write_document_chunks_safe(doc_id, doc_title, chunks, source=source)
except Exception:
    pass
```

**`app/core/kg/neo4j_store.py`**：保留文件，不做修改。

### Neo4j 职责重定位后的角色

| 职责 | 状态 |
|------|------|
| 通用 Document/Chunk 镜像（随 PDF 导入自动写入） | **移除** |
| GB2760 业务图谱（Chemical / FoodCategory / 限量关系等） | **保留**，数据单独导入 |
| Agent `neo4j_query` Tool 查询 GB2760 图谱 | **不受影响** |
| 未来：普通国标实体抽取与 GB2760 联动 | 待后续设计 |

### 涉及文件

- **修改**：`app/core/kb/__init__.py`（删除 3 行调用）
- **不变**：`app/core/kg/neo4j_store.py`

---

## 不在本次范围内

- GB2760 数据导入脚本（数据已清洗，单独处理）
- `neo4j_query` Tool 的查询逻辑优化
- 其他 Phase（1、4、5、6、7）的变更

---

## 验收标准

1. `split_heading_from_markdown` 对超过 1500 字符的块递归按子标题切分
2. `section_path` 正确继承父级路径
3. 最深层超限块保留完整，不截断
4. PDF 导入流程不再写入 Neo4j，Neo4j 不可用时不影响导入
5. 现有测试全部通过
