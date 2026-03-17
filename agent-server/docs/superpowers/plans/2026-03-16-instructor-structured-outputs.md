# Instructor Structured Outputs Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `parser_workflow` 的四个结构化节点统一迁移到 Instructor，确保在 `openai/dashscope/ollama` 下稳定输出结构化对象并在失败时 `fail-fast`。

**Architecture:** 新增 `structured_llm` 网关层，节点只负责业务 prompt 与 schema，网关负责 provider 适配、重试、错误包装。通过 `node_name -> settings` 映射统一解析 provider/model，并保持 `TRANSFORM_MODEL` 为空时 fallback 到 `ESCALATE_MODEL`。测试从“节点内 fallback”转为“网关统一异常与重试策略”。

**Tech Stack:** Python 3.12, instructor, openai-compatible clients, pydantic v2, pytest

---

## Chunk 1: 基础设施与配置（依赖 + 网关骨架）

### Task 1: 增加 Instructor 依赖

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: 修改依赖（先不实现业务代码）**

```toml
# pyproject.toml
dependencies = [
  # ...existing...
  "instructor>=1.14.5",
]
```

- [ ] **Step 2: 同步依赖**

Run: `cd agent-server && uv sync`  
Expected: lock/install 成功，无依赖冲突

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add instructor dependency for structured outputs"
```

---

### Task 2: 新增结构化网关模块与配置字段

**Files:**
- Create: `app/core/parser_workflow/structured_llm/__init__.py`
- Create: `app/core/parser_workflow/structured_llm/errors.py`
- Create: `app/core/parser_workflow/structured_llm/types.py`
- Create: `app/core/parser_workflow/structured_llm/client_factory.py`
- Create: `app/core/parser_workflow/structured_llm/invoker.py`
- Modify: `app/core/config.py`
- Test: `tests/core/parser_workflow/test_structured_llm.py`

- [ ] **Step 1: 先写失败测试（配置默认值 + invoker 核心行为）**

```python
def test_structured_settings_defaults():
    s = Settings()
    assert s.PARSER_STRUCTURED_MAX_RETRIES == 2
    assert s.PARSER_STRUCTURED_TIMEOUT_SECONDS == 60
    assert s.PARSER_STRUCTURED_TEMPERATURE == 0.0
    assert s.PARSER_STRUCTURED_LOG_PROMPT_PREVIEW is False

def test_resolve_model_for_transform_fallback():
    model = resolve_model_for_node(
        node_name="transform_node",
        node_model="",
        fallback_model="qwen-max",
    )
    assert model == "qwen-max"

def test_resolve_model_for_classify():
    model = resolve_model_for_node(
        node_name="classify_node",
        node_model="qwen-turbo",
        fallback_model="",
    )
    assert model == "qwen-turbo"
```

- [ ] **Step 2: 运行失败测试**

Run: `cd agent-server && pytest tests/core/parser_workflow/test_structured_llm.py -v`  
Expected: FAIL（模块/符号不存在）

- [ ] **Step 3: 最小实现通过**

```python
# errors.py
class StructuredOutputError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: str,
        node_name: str,
        response_model: str,
        retry_count: int,
        raw_error: str,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.node_name = node_name
        self.response_model = response_model
        self.retry_count = retry_count
        self.raw_error = raw_error

# invoker.py
def resolve_model_for_node(node_name: str, node_model: str, fallback_model: str) -> str:
    if node_name == "transform_node" and not node_model:
        return fallback_model
    return node_model

def invoke_structured(
    *,
    node_name: str,
    prompt: str,
    response_model: type[BaseModel],
    provider: str | None = None,
    model: str | None = None,
    max_retries: int | None = None,
    temperature: float | None = None,
    timeout_seconds: int | None = None,
) -> BaseModel:
    ...
```

`invoke_structured` 约定：
- 若 `provider/model` 未显式传入，则按 `node_name -> settings` 自动解析：
  - `classify_node` -> `CLASSIFY_LLM_PROVIDER/CLASSIFY_MODEL`
  - `escalate_node` -> `ESCALATE_LLM_PROVIDER/ESCALATE_MODEL`
  - `transform_node` -> `TRANSFORM_LLM_PROVIDER/TRANSFORM_MODEL`（空则 fallback `ESCALATE_MODEL`）
  - `structure_node` -> `DOC_TYPE_LLM_PROVIDER/DOC_TYPE_LLM_MODEL`
- provider 解析优先级：节点覆盖 > `PARSER_LLM_PROVIDER` > `"openai"`。

- [ ] **Step 4: 继续补充 provider 适配测试并实现**
  - 覆盖 `openai/dashscope/ollama` 三分支
  - 验证 dashscope 默认注入 `enable_thinking=False`
  - 验证 ollama 默认注入 `reasoning=False`
  - 验证 Pydantic 校验失败时不重试
  - 验证网络/超时错误会按上限重试

- [ ] **Step 5: 全量运行本文件测试**

Run: `pytest tests/core/parser_workflow/test_structured_llm.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/core/config.py app/core/parser_workflow/structured_llm tests/core/parser_workflow/test_structured_llm.py
git commit -m "feat: add structured llm gateway with instructor"
```

---

## Chunk 2: 四节点迁移（classify/escalate/transform/structure）

### Task 3: 迁移 `classify_node` 到 `invoke_structured`

**Files:**
- Modify: `app/core/parser_workflow/nodes/classify_node.py`
- Modify: `tests/core/parser_workflow/test_classify_node_fallback.py`
- Modify: `tests/core/parser_workflow/test_classify_node.py`

- [ ] **Step 1: 先改测试（删除 fallback 成功预期，改为 fail-fast，且使用 mock）**

```python
def test_call_classify_llm_raise_error_when_structured_failed():
    with patch("app.core.parser_workflow.nodes.classify_node.invoke_structured") as mock_call:
        mock_call.side_effect = StructuredOutputError(
            "mock failure",
            provider="openai",
            model="gpt-4o-mini",
            node_name="classify_node",
            response_model="ClassifyOutput",
            retry_count=2,
            raw_error="ValidationError",
        )
        with pytest.raises(StructuredOutputError):
            _call_classify_llm("前言", [{"id": "preface", "description": "前言"}])
```

- [ ] **Step 2: 跑单测确认失败**

Run: `pytest tests/core/parser_workflow/test_classify_node_fallback.py -v`  
Expected: FAIL（旧逻辑仍在）

- [ ] **Step 3: 实现节点改造**
  - 移除 `create_chat_model(...with_structured_output...)` 调用
  - 改为 `invoke_structured(..., node_name="classify_node", response_model=ClassifyOutput)`
  - 不做 raw JSON 清洗

- [ ] **Step 4: 运行相关测试**

Run: `pytest tests/core/parser_workflow/test_classify_node.py tests/core/parser_workflow/test_classify_node_fallback.py -v`  
Expected: PASS

- [ ] **Step 4.1: 补一个成功路径 mock 测试（可放在 fallback 文件或 classify 单测）**
  - `invoke_structured` 返回 `ClassifyOutput` 时，`_call_classify_llm` 返回 `segments`

- [ ] **Step 5: Commit**

```bash
git add app/core/parser_workflow/nodes/classify_node.py tests/core/parser_workflow/test_classify_node.py tests/core/parser_workflow/test_classify_node_fallback.py
git commit -m "refactor: migrate classify node to instructor structured gateway"
```

---

### Task 4: 迁移 `escalate_node` 与 `transform_node`

**Files:**
- Modify: `app/core/parser_workflow/nodes/escalate_node.py`
- Modify: `app/core/parser_workflow/nodes/transform_node.py`
- Modify: `tests/core/parser_workflow/test_transform_node.py`
- Create: `tests/core/parser_workflow/test_escalate_node.py`

- [ ] **Step 1: 先写/改失败测试（mock 目标改为 `invoke_structured`）**

```python
def test_call_llm_transform_uses_invoke_structured():
    with patch("app.core.parser_workflow.nodes.transform_node.invoke_structured") as mock_call:
        mock_call.return_value = TransformOutput(content="x")
        assert _call_llm_transform("a", {"strategy": "plain_embed", "prompt_template": "p"}) == "x"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/core/parser_workflow/test_transform_node.py -v`  
Expected: FAIL（尚未迁移）

- [ ] **Step 3: 实现最小改造并通过**
  - `escalate_node` 使用 `node_name="escalate_node"`
  - `transform_node` 使用 `node_name="transform_node"`，并验证空 `TRANSFORM_MODEL` fallback
  - 保留业务行为（append 新 content_type、DocumentChunk 组装）不变

- [ ] **Step 4: 运行测试**

Run: `pytest tests/core/parser_workflow/test_transform_node.py tests/core/parser_workflow/test_escalate_node.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/parser_workflow/nodes/escalate_node.py app/core/parser_workflow/nodes/transform_node.py tests/core/parser_workflow/test_transform_node.py tests/core/parser_workflow/test_escalate_node.py
git commit -m "refactor: migrate escalate and transform nodes to instructor gateway"
```

---

### Task 5: 迁移 `structure_node`（规则命中/未命中双路径）

**Files:**
- Modify: `app/core/parser_workflow/nodes/structure_node.py`
- Modify: `tests/core/parser_workflow/test_structure_node.py`

- [ ] **Step 1: 先写失败测试**
  - 规则命中：不调用 `invoke_structured`
  - 规则未命中：调用 `invoke_structured` 并写入新规则
  - LLM 失败：抛 `StructuredOutputError`

- [ ] **Step 2: 运行失败测试**

Run: `pytest tests/core/parser_workflow/test_structure_node.py -v`  
Expected: FAIL（旧 mock 路径仍是 `create_chat_model`）

- [ ] **Step 3: 实现迁移**
  - `_infer_doc_type_with_llm` 改用 `invoke_structured(..., node_name="structure_node", response_model=DocTypeOutput)`
  - 保持规则优先逻辑不变

- [ ] **Step 4: 运行测试**

Run: `pytest tests/core/parser_workflow/test_structure_node.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/parser_workflow/nodes/structure_node.py tests/core/parser_workflow/test_structure_node.py
git commit -m "refactor: migrate structure node to instructor gateway"
```

---

## Chunk 3: 清理旧路径与回归验证

### Task 6: 收敛 `llm.py` 责任与测试职责

**Files:**
- Modify: `app/core/parser_workflow/llm.py`
- Modify: `tests/core/parser_workflow/test_llm.py`

- [ ] **Step 1: 先写/改失败测试**
  - `test_llm.py` 仅保留 `resolve_provider` 与非结构化职责测试
  - 旧 `with_structured_output` 断言迁移到 `test_structured_llm.py`
  - 明确迁移用例：`test_create_chat_model_with_output_schema`、`test_create_chat_model_dashscope` 中 structured 相关断言

- [ ] **Step 2: 运行失败测试**

Run: `pytest tests/core/parser_workflow/test_llm.py tests/core/parser_workflow/test_structured_llm.py -v`  
Expected: FAIL（职责未收敛前）

- [ ] **Step 3: 实现收敛**
  - 删除或弃用 `llm.py` 中结构化输出分支
  - 确保四节点不再依赖 `create_chat_model(...output_schema=...)`

- [ ] **Step 4: 运行测试**

Run: `pytest tests/core/parser_workflow/test_llm.py tests/core/parser_workflow/test_structured_llm.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/core/parser_workflow/llm.py tests/core/parser_workflow/test_llm.py tests/core/parser_workflow/test_structured_llm.py
git commit -m "refactor: remove legacy structured-output path from llm helper"
```

---

### Task 7: 端到端验证与 real-llm 分层

**Files:**
- Modify: `tests/core/parser_workflow/test_classify_node_real_llm.py`
- Modify: `tests/core/parser_workflow/test_escalate_node_real_llm.py`
- Modify: `tests/core/parser_workflow/test_transform_node_real_llm.py`
- Modify: `tests/core/parser_workflow/test_structure_node_real_llm.py`
- Modify: `tests/core/parser_workflow/test_workflow.py`

- [ ] **Step 1: 增加 marker 分层（如 `@pytest.mark.real_llm`）**
- [ ] **Step 2: 去除 fallback 相关预期，统一为结构化成功或 fail-fast 断言**
- [ ] **Step 3: 跑非 real_llm 回归**

Run: `pytest tests/core/parser_workflow -v -m "not real_llm"`  
Expected: PASS

- [ ] **Step 4: 选跑 real_llm（环境可用时）**

Run: `pytest tests/core/parser_workflow -v -m "real_llm"`  
Expected: PASS（若环境缺 key 则按测试内 skip）

- [ ] **Step 4.1: 确认四个 real-llm 文件均已覆盖迁移**
  - `test_classify_node_real_llm.py`
  - `test_escalate_node_real_llm.py`
  - `test_transform_node_real_llm.py`
  - `test_structure_node_real_llm.py`

- [ ] **Step 5: Commit**

```bash
git add tests/core/parser_workflow/test_*real_llm.py tests/core/parser_workflow/test_workflow.py
git commit -m "test: align real-llm parser workflow tests with instructor fail-fast behavior"
```

---

### Task 8: 最终验收与文档同步

**Files:**
- Modify: `docs/superpowers/specs/2026-03-16-instructor-structured-outputs-design.md`（若实现偏差需回写）
- Modify: `docs/superpowers/plans/2026-03-16-instructor-structured-outputs.md`（勾选步骤/记录偏差）

- [ ] **Step 1: 运行最终验收命令**

Run:

```bash
pytest tests/core/parser_workflow/test_structured_llm.py -v && \
pytest tests/core/parser_workflow -v -m "not real_llm"
```

Expected: PASS

- [ ] **Step 2: 执行静态检查（如项目当前有）**

Run: `pytest -q`（或仓库约定最小集合）  
Expected: 关键相关模块无新增失败

- [ ] **Step 3: 最终 Commit**

```bash
git add app/core/config.py app/core/parser_workflow docs/superpowers/specs/2026-03-16-instructor-structured-outputs-design.md docs/superpowers/plans/2026-03-16-instructor-structured-outputs.md tests/core/parser_workflow pyproject.toml uv.lock
git commit -m "feat: adopt instructor as parser workflow structured output gateway"
```

---

## 交接说明（执行前检查）

- 如果执行环境支持 subagents，实施阶段必须使用 `superpowers:subagent-driven-development`。
- 每个 Task 执行时严格采用 TDD：先失败测试，再最小实现，再回归，再提交。
- 若遇到 provider 行为差异，优先修正 `client_factory.py`，不要在节点内加 provider 分支。
