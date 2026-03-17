# Spec 09：测试断言更新

## 问题现象

现有测试中断言 `content_type` 字段的存在和具体值，字段重命名后测试将失败，且旧断言无法验证双字段体系是否正确工作。

## 根因

两个测试文件中存在对 `content_type` 的断言：

```
tests/core/parser_workflow/test_classify_node_real_llm.py
tests/core/parser_workflow/test_workflow.py
```

典型断言模式：
```python
assert seg["content_type"] in valid_types
assert chunk["content_type"] == "table"
```

这些断言在字段重命名后会抛 KeyError（TypedDict 访问不存在的 key）或 AssertionError。

## 发现方式

```bash
grep -n "content_type" tests/core/parser_workflow/test_classify_node_real_llm.py
grep -n "content_type" tests/core/parser_workflow/test_workflow.py
```

## 方案

### 断言替换原则

| 旧断言 | 新断言 |
|---|---|
| `seg["content_type"] in valid_types` | `seg["structure_type"] in VALID_STRUCTURE_TYPES` 且 `seg["semantic_type"] in VALID_SEMANTIC_TYPES` |
| `chunk["content_type"] == "table"` | `chunk["structure_type"] == "table"` |
| `seg["content_type"] == "unknown"` | `seg["structure_type"] == "unknown" and seg["semantic_type"] == "unknown"` |

### 新增验证点

测试应额外验证：
1. 对于 GB 标准"1 范围"章节，`semantic_type == "scope"`
2. 对于"试剂和材料"节，`semantic_type == "material"`
3. 对于"分析步骤"节，`semantic_type == "procedure"`
4. 对于含 `$$...$$` 的结果计算节，`structure_type == "formula"` 或 `semantic_type == "calculation"`

这些验证点直接对应 Spec 01 中识别出的旧体系分类错误，是回归测试的核心。

### 有效值常量

在测试文件顶部定义：

```python
VALID_STRUCTURE_TYPES = {"paragraph", "list", "table", "formula", "header"}
VALID_SEMANTIC_TYPES = {"metadata", "scope", "limit", "procedure", "material", "calculation", "definition", "amendment"}
```

## 依赖关系

- 前置：Spec 01-08 全部完成后执行
- 本 spec 是验收步骤，无后续依赖

## 受影响文件

- `tests/core/parser_workflow/test_classify_node_real_llm.py`
- `tests/core/parser_workflow/test_workflow.py`
