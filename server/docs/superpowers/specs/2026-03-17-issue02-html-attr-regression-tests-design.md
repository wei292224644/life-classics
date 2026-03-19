# ISSUE-02 回归测试设计：classify_node HTML 属性保留验证

**日期：** 2026-03-17
**关联 Issue：** `docs/issues/parser_workflow_issues_20260317.md` ISSUE-02

---

## 背景

classify_node 已修复 HTML 属性被 LLM 篡改的问题（引入 `_escape_for_json_prompt`），但尚无回归测试。本设计补充两层测试覆盖。

---

## 测试范围

仅执行新增测试文件/函数，不全量跑所有测试。

---

## Part 1：单元测试（`test_classify_node_unit.py`）

新增 4 个函数，均 mock `invoke_structured`，无需 LLM API Key。

### T1 `test_escape_for_json_prompt_escapes_double_quotes`

- 输入：含 HTML 属性的字符串，如 `<td rowspan="2">文本</td>`
- 断言：输出中 `"` 全部变为 `\"`，即 `rowspan=\"2\"`

### T2 `test_escape_for_json_prompt_preserves_other_characters`

- 输入：不含双引号的字符串（中文、单引号、`<>/`）
- 断言：输出与输入完全相同

### T3 `test_classify_node_html_chunk_prompt_escapes_attribute_quotes`

- chunk content：`<td rowspan="2">取适量试样...</td>`
- mock `invoke_structured`，捕获 prompt 参数
- 断言：prompt 中包含 `rowspan=\"2\"`，不含未转义的 `rowspan="2"`

### T4 `test_classify_node_html_chunk_content_unchanged_in_segment`

- 同 T3 的 chunk
- mock LLM 返回 content 为原始 HTML（含真双引号）
- 断言：`segment["content"]` 与原始 chunk content 字符串完全相等

---

## Part 2：真实 LLM 测试（`test_classify_node_real_llm.py`）

### T5 `test_classify_node_html_table_attribute_content_preserved_with_real_llm`

- 标记：`@pytest.mark.real_llm`，需 `LLM_API_KEY`
- chunk content：包含 `rowspan="2"` 的 HTML 表格片段
- 调用真实 `classify_node`
- 断言：
  - 所有 segment 的 content 拼合后仍包含 `rowspan="2"`（HTML 属性未被篡改）
  - 每个 segment 有合法的 `structure_type` 和 `semantic_type`

---

## 运行方式

```bash
# 单元测试（无需 LLM）
cd agent-server
uv run pytest tests/core/parser_workflow/test_classify_node_unit.py -v

# 真实 LLM 测试
LLM_API_KEY=xxx uv run pytest tests/core/parser_workflow/test_classify_node_real_llm.py::test_classify_node_html_table_attribute_content_preserved_with_real_llm -v -s -m real_llm
```
