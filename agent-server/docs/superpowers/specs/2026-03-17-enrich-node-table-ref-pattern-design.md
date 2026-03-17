# Design: enrich_node 表格引用正则扩展（ISSUE-01）

**日期：** 2026-03-17
**文件：** `app/core/parser_workflow/nodes/enrich_node.py`
**测试：** `tests/core/parser_workflow/test_enrich_node.py`

---

## 背景

`_TABLE_REF_PATTERN` 仅覆盖 `见/参见/参照` 三个前缀，导致 GB 标准中最常见的 `应符合表X的规定` 等写法完全无法匹配，enrich_node 对大多数 GB 文档实际失效。

---

## 解决方案

### 1. 正则扩展（召回层）

将 `_TABLE_REF_PATTERN` 扩展为覆盖所有 GB 常见前缀：

```python
_TABLE_REF_PATTERN = re.compile(
    r'(?:见|参见|参照|应符合|符合|按照?|不[应得]超过|不[应得]低于)'
    r'[^\n，。；]*?表\s*([\dA-Z]+(?:\.\d+)*)',
    re.UNICODE,
)
```

新增覆盖的前缀：
- `应符合` — 最常见，如"感官要求应符合表1的规定"
- `符合` — 无"应"字变体
- `按` / `按照` — 如"按表3进行检验"
- `不[应得]超过` — 如"污染物限量不得超过表4的规定"
- `不[应得]低于` — 如"检出限不应低于表B.1的要求"

### 2. 后验过滤层（扩展口）

新增 `_filter_table_refs` 函数，当前直接透传，为后期误报过滤预留接口：

```python
def _filter_table_refs(refs: list[str]) -> list[str]:
    """
    后验过滤：对召回的表格引用标签做二次验证。
    当前直接透传；后期如需排除误报可在此添加规则。

    TODO: 如召回率提高后误报增多，在此添加过滤逻辑，
          例如排除标题行自身、排除特定 section_path 下的引用等。
    """
    return refs
```

`extract_table_refs` 末尾接入过滤层：

```python
def extract_table_refs(text: str) -> list[str]:
    raw = ["表" + _normalize_label(m.group(1)) for m in _TABLE_REF_PATTERN.finditer(text)]
    return _filter_table_refs(raw)
```

---

## 测试设计

只运行 `tests/core/parser_workflow/test_enrich_node.py`，不跑全量测试。

### 新增单元测试（`extract_table_refs` 区块）

| 测试函数 | 输入 | 期望 |
|---------|------|------|
| `test_extract_table_refs_yingfuhe` | `感官要求应符合表1的规定。` | `["表1"]` |
| `test_extract_table_refs_fuhe` | `理化指标符合表2的规定。` | `["表2"]` |
| `test_extract_table_refs_an` | `按表3进行检验。` | `["表3"]` |
| `test_extract_table_refs_anzhao` | `按照表A.1操作。` | `["表A.1"]` |
| `test_extract_table_refs_bu_chao` | `污染物限量不得超过表4的规定。` | `["表4"]` |
| `test_extract_table_refs_bu_di` | `检出限不应低于表B.1的要求。` | `["表B.1"]` |

### 新增集成测试（`enrich_node` 区块）

`test_enrich_node_gb_style_multiple_refs`：用 GB1886 风格段落（含 `应符合表1`、`符合表2`、`按照表3`）构造 state，验证三个表格均被内联到 `ref_context`。

---

## 变更范围

- **修改**：`app/core/parser_workflow/nodes/enrich_node.py`
  - `_TABLE_REF_PATTERN` 正则扩展
  - 新增 `_filter_table_refs` 函数
  - `extract_table_refs` 接入过滤层
- **修改**：`tests/core/parser_workflow/test_enrich_node.py`
  - 新增 6 个单元测试 + 1 个集成测试
