# PDF 解析重构设计：递归切分 + Neo4j 职责重定位

**日期：** 2026-03-12
**范围：** Phase 2（递归标题切分）、Phase 3（Neo4j 职责）
**与现有计划的关系：** 本文档是对 `docs/plans/2026-03-02-full-refactor-implementation-plan.md` 中 Phase 2 和 Phase 3 的**设计补充和澄清**，两份文档有冲突时以本文档为准。

---

## 背景

现有重构计划中：

- **Phase 2** 实现了按标题切分，但切分规则不够精确——只是简单地在每个标题处截断，未考虑 chunk 大小控制。
- **Phase 3** 将 Document/Chunk 写入 Neo4j，但这个结构目前没有实际用途，增加了导入复杂度和对 Neo4j 的强依赖。

本文档明确这两个 Phase 的设计决策。

---

## Phase 2：递归标题切分

### 目标

将 MinerU 输出的 Markdown 按标题层级递归切分为 `DocumentChunk` 列表，每块不超过 1500 字符。若递归至最深可用标题层级后内容仍超限，保留整块不强制截断。

### 数据结构

`_Block` 定义在 `heading_strategy.py` 内部（私有，不对外暴露）：

```python
@dataclass
class _Block:
    level: int            # 标题层级，1-6；前言块（首个标题前内容）为 0
    section_path: List[str]  # 当前完整路径，如 ["第三章", "3.4 检验方法"]
    content: str          # 包含当前标题行（若有）及其后全部内容
```

### 算法

**函数签名**（对外接口保持向后兼容）：

```python
def split_heading_from_markdown(
    markdown_content: str,
    doc_id: str,
    doc_title: str,
    source: str,
    markdown_id: Optional[str] = None,  # 透传到每个 DocumentChunk.markdown_id
    max_chars: int = 1500,              # Python str.__len__，即 Unicode 码点数
) -> List[DocumentChunk]
```

> `max_chars` 选 1500 的依据：GB 标准内容以中文为主，中文 1 字符 ≈ 1 token（BPE），1500 字符约等于 1500 token，在常用 embedding 模型（text-embedding-v2、qwen3-embedding）的有效区间内。

**处理流程：**

**第一步：按 L1 切分，得到 `_Block` 列表**

- 识别所有 `^#\s+` 行作为 L1 边界
- 若第一个 L1 标题之前有内容：生成 `_Block(level=0, section_path=[], content=前言文本)`
- 每个 L1 标题开始一个 `_Block`：
  - `level=1`
  - `section_path=[去除前导 `#` 和空格后的标题文本]`
  - `content` = 该标题行 + 直到下一个 L1 标题（不含）前的所有行

**第二步：递归函数 `_try_split`**

```python
def _try_split(block: _Block, next_level: int, ...) -> List[DocumentChunk]:
    if len(block.content) <= max_chars:
        return [make_chunk(block)]   # 直接产出

    if next_level > 6:
        return [make_chunk(block)]   # 已无更深层级，保留整块（允许超限）

    # 在 block.content 内搜索 next_level 级标题
    sub_blocks = split_by_level(block.content, next_level, parent_path=block.section_path)

    if len(sub_blocks) <= 1:
        # 当前层级无法切分（无此层级标题，或内容全在该标题之前）
        # 尝试下一个层级，而非直接放弃
        return _try_split(block, next_level + 1, ...)

    # 对每个子块递归
    result = []
    for sub in sub_blocks:
        result.extend(_try_split(sub, next_level + 1, ...))
    return result
```

> **关键设计**：当 `next_level` 无标题可切时，**不立即保留整块，而是尝试 `next_level + 1`**，直到 level > 6 才放弃。这确保「L1 有内容但无 L2，却有 L3」的情形仍可被 L3 正确切分。

**`split_by_level` 子函数行为：**

- 在 `content` 文本中找 `^#{next_level}\s+` 行
- 将文本切成子块，**每个子块的 `content` 包含该级标题行及其后内容**（不包含父级标题行，父级标题信息已通过 `section_path` 保留）
- 子块 `section_path = parent_path + [子标题文本]`，子标题文本取法：去除前导 `#` 和空格（适用于所有层级，L2、L3 … 规则相同）

**边界行为：**

| 场景 | 处理方式 |
|------|---------|
| 块 ≤ 1500 字符 | 直接产出，不递归 |
| 块 > 1500，当前层级有标题 | 切分后对子块递归 |
| 块 > 1500，当前层级无标题，更深层有标题 | 跳过当前层级，递归尝试更深层 |
| 块 > 1500，所有更深层均无标题（`next_level > 6`） | 保留整块，允许超限 |
| 首个 L1 标题前有内容（前言） | 产出 `section_path=[]` 的前言 chunk；若前言超限，同样递归尝试 L2…L6 |
| 空内容块或仅含空白的块 | **丢弃**，不产出 chunk（避免向向量库写入空内容） |
| Markdown 无任何标题 | 整个内容作为 `section_path=[]` 的单一 chunk |

**chunk 内容说明：**

- 每个 chunk 的 `content` 包含**当前级别的标题行**（保留可读性），但**不包含祖先标题行**——祖先信息已在 `section_path` 中。
- `markdown_id` 透传至每个产出的 `DocumentChunk.markdown_id`。

**配置参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_chars` | `1500` | 单块最大 Unicode 码点数 |

### 涉及文件

- **修改**：`app/core/kb/strategy/heading_strategy.py`（私有 `_Block` dataclass，`_try_split` / `split_by_level` 辅助函数，改造 `split_heading_from_markdown`）
- **修改**：`tests/core/kb/strategy/test_heading_strategy.py`（覆盖递归切分、跳层级、前言块、空块丢弃、无标题文档、超限保留场景）

### 数据迁移

本次变更改变了切分边界，**已导入的文档不会自动重新切分**。如需新规则生效，需手动删除并重新导入对应文档。

---

## Phase 3：Neo4j 职责重定位

### 决策

**从 PDF 导入流程中移除 Document/Chunk 写入 Neo4j**，理由：

- 该结构（`Document -[:CONTAINS]-> Chunk`）当前无实际查询用途
- 增加对 Neo4j 可用性的依赖，导入时引入额外噪音
- GB2760 业务图谱（已有 schema + 清洗好的数据）将单独导入，不经过 `import_pdf_via_mineru`

### 变更内容

**`app/core/kb/__init__.py`** 中的 `import_pdf_via_mineru`，删除以下代码：

```python
try:
    from app.core.kg.neo4j_store import write_document_chunks_safe
    write_document_chunks_safe(doc_id, doc_title, chunks, source=source)
except Exception:
    pass
```

**`app/core/kg/neo4j_store.py`**：保留文件，在文件顶部注释中明确：此模块用于 GB2760 业务图谱，**不由 PDF 导入流程自动调用**。逻辑不变。

### Neo4j 职责重定位后的角色

| 职责 | 状态 |
|------|------|
| 通用 Document/Chunk 镜像（随 PDF 导入自动写入） | **移除** |
| GB2760 业务图谱（Chemical / FoodCategory / 限量关系等） | **保留**，数据单独导入 |
| Agent `neo4j_query` Tool 查询 GB2760 图谱 | **不受影响** |
| 未来：普通国标实体抽取与 GB2760 联动 | 待后续设计 |

### 涉及文件

- **修改**：`app/core/kb/__init__.py`（删除 3 行调用）
- **修改**：`app/core/kg/neo4j_store.py`（顶部注释，逻辑不变）

---

## 不在本次范围内

- GB2760 数据导入脚本
- `neo4j_query` Tool 的查询逻辑优化
- 其他 Phase（1、4、5、6、7）的变更

---

## 验收标准

1. `split_heading_from_markdown` 对 > 1500 字符的 L1 块按 L2 递归切分；L2 仍超限则按 L3，依此类推
2. 当某层级无标题但更深层有标题时，自动跳过该层级继续递归（不提前保留整块）
3. `section_path` 正确继承父级路径；各层级标题文本均去除前导 `#` 和空格
4. 递归穷尽所有层级（L2–L6）后仍超限的块保留完整，不截断
5. 首个 L1 标题前的前言内容产出 `section_path=[]` 的 chunk（超限时同样递归处理）；空内容块被丢弃
6. `import_pdf_via_mineru` 中不存在对 `write_document_chunks_safe` 的任何调用（单元测试 mock 断言验证）
7. 新增测试用例覆盖：递归路径、跳层级（L1→L3）、前言块、空块丢弃、无标题文档、超限保留；原有小于阈值的简单测试仍通过
