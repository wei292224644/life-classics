# Parser Workflow LLM Provider 抽象化 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**目标：** 将 `parser_workflow` 中四个节点里硬编码的 `ChatOpenAI` 创建逻辑抽象为统一工厂，支持通过配置切换 OpenAI、DashScope、Ollama 等 provider。

**架构：** 新增 `parser_workflow/llm.py` 作为唯一 LLM 工厂，对外暴露 `create_chat_model` 和 `resolve_provider` 两个函数。各节点将模块顶层的 `chat = ChatOpenAI(...)` 移入 LLM 调用函数体内，改为调用工厂。provider 通过 settings 中的节点级配置项选择，回退链为：节点级配置 → 全局默认 `PARSER_LLM_PROVIDER` → `"openai"`。

**技术栈：** Python 3.11+、LangChain（`langchain_openai`、`langchain_ollama`）、Pydantic Settings、pytest

---

## 文件结构

| 文件 | 变更类型 | 职责 |
|------|---------|------|
| `app/core/config.py` | 修改 | 新增 provider 选择配置项 + DashScope 专用凭证 |
| `app/core/parser_workflow/config.py` | 修改 | `ParserConfig` 新增 provider 字段 |
| `app/core/parser_workflow/llm.py` | **新建** | LLM 工厂：`create_chat_model` + `resolve_provider` |
| `app/core/parser_workflow/nodes/classify_node.py` | 修改 | 移除模块级 `chat`，改用工厂 |
| `app/core/parser_workflow/nodes/escalate_node.py` | 修改 | 移除模块级 `chat` 及内联 import，改用工厂 |
| `app/core/parser_workflow/nodes/transform_node.py` | 修改 | 移除模块级 `chat`，改用工厂 |
| `app/core/parser_workflow/nodes/structure_node.py` | 修改 | 移除模块级 `chat` 及内联 import，改用工厂 |
| `tests/core/parser_workflow/test_llm.py` | **新建** | `llm.py` 单元测试 |

---

## Chunk 1: 配置层 + LLM 工厂

### Task 1: 添加配置字段

**文件：**
- 修改：`app/core/config.py`
- 修改：`app/core/parser_workflow/config.py`

- [ ] **步骤 1：在 `app/core/config.py` 的 `Settings` 中添加配置项**

  在 `LLM_BASE_URL` 字段后、`# ── 各用途模型` 注释前，插入：

  ```python
  # ── DashScope 专用凭证 ────────────────────────────────────────────────────
  DASHSCOPE_API_KEY: str = ""
  DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

  # ── Ollama 连接 ───────────────────────────────────────────────────────────
  OLLAMA_BASE_URL: str = "http://localhost:11434"

  # ── Parser Workflow Provider 选择 ─────────────────────────────────────────
  PARSER_LLM_PROVIDER: str = "openai"    # 全局默认，可选 openai / dashscope / ollama
  CLASSIFY_LLM_PROVIDER: str = ""        # 节点级覆盖，空则使用全局默认
  ESCALATE_LLM_PROVIDER: str = ""
  TRANSFORM_LLM_PROVIDER: str = ""
  DOC_TYPE_LLM_PROVIDER: str = ""        # 对应 structure_node.py
  ```

- [ ] **步骤 2：在 `app/core/parser_workflow/config.py` 的 `ParserConfig` 中添加 provider 字段**

  `ParserConfig` 是 `TypedDict`（`total=False`，所有字段可选），在 `confidence_threshold` 字段后追加（保留已有的 `llm_api_key` / `llm_base_url` 字段，不删除）：

  ```python
  parser_llm_provider: str
  classify_llm_provider: str
  escalate_llm_provider: str
  transform_llm_provider: str
  doc_type_llm_provider: str
  ```

- [ ] **步骤 3：运行全量测试，确认配置变更无破坏**

  ```bash
  cd agent-server && pytest tests/ -v --ignore=tests/core/parser_workflow/test_workflow.py
  ```

  预期：全部 PASS（纯字段新增，不影响任何现有逻辑）

- [ ] **步骤 4：提交**

  ```bash
  git add app/core/config.py app/core/parser_workflow/config.py
  git commit -m "feat: add LLM provider config fields for parser_workflow"
  ```

---

### Task 2: TDD 创建 `llm.py` 工厂

**文件：**
- 新建：`app/core/parser_workflow/llm.py`
- 新建：`tests/core/parser_workflow/test_llm.py`

- [ ] **步骤 1：新建测试文件，写全部失败测试**

  新建 `tests/core/parser_workflow/test_llm.py`，内容如下：

  ```python
  from __future__ import annotations

  import pytest
  from unittest.mock import patch
  from pydantic import BaseModel

  from app.core.parser_workflow.llm import create_chat_model, resolve_provider


  class _DummySchema(BaseModel):
      content: str


  # ── resolve_provider ────────────────────────────────────────────────────────

  def test_resolve_provider_explicit():
      """明确传入 provider 时直接返回。"""
      assert resolve_provider("ollama") == "ollama"


  def test_resolve_provider_fallback_to_global():
      """node_provider 为空时，回退到 PARSER_LLM_PROVIDER。"""
      from unittest.mock import MagicMock, patch
      mock_settings = MagicMock()
      mock_settings.PARSER_LLM_PROVIDER = "dashscope"
      with patch("app.core.parser_workflow.llm.settings", mock_settings):
          assert resolve_provider("") == "dashscope"
          assert resolve_provider(None) == "dashscope"


  def test_resolve_provider_hardcoded_fallback():
      """PARSER_LLM_PROVIDER 也为空时，回退到 'openai'。"""
      from unittest.mock import MagicMock, patch
      mock_settings = MagicMock()
      mock_settings.PARSER_LLM_PROVIDER = ""
      with patch("app.core.parser_workflow.llm.settings", mock_settings):
          assert resolve_provider(None) == "openai"


  # ── create_chat_model ───────────────────────────────────────────────────────

  def test_create_chat_model_openai():
      """provider='openai' 返回 ChatOpenAI 实例。"""
      from langchain_openai import ChatOpenAI
      with patch("app.core.parser_workflow.llm.settings") as mock_settings:
          mock_settings.LLM_API_KEY = "test-key"
          mock_settings.LLM_BASE_URL = ""
          model = create_chat_model("gpt-4o", "openai")
      assert isinstance(model, ChatOpenAI)


  def test_create_chat_model_dashscope():
      """provider='dashscope' 返回 ChatOpenAI 实例，且自动注入 extra_body={"enable_thinking": False}。"""
      from langchain_openai import ChatOpenAI
      with patch("app.core.parser_workflow.llm.settings") as mock_settings:
          mock_settings.DASHSCOPE_API_KEY = "ds-key"
          mock_settings.DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
          model = create_chat_model("qwen-max", "dashscope")
      assert isinstance(model, ChatOpenAI)
      # 验证 extra_body 已自动注入（langchain_openai 将 extra_body 存为 Pydantic 字段）
      extra = getattr(model, "extra_body", None) or model.model_kwargs.get("extra_body")
      assert extra == {"enable_thinking": False}


  def test_create_chat_model_ollama():
      """provider='ollama' 返回 ChatOllama 实例。"""
      from langchain_ollama import ChatOllama
      with patch("app.core.parser_workflow.llm.settings") as mock_settings:
          mock_settings.OLLAMA_BASE_URL = "http://localhost:11434"
          model = create_chat_model("llama3", "ollama")
      assert isinstance(model, ChatOllama)


  def test_create_chat_model_with_output_schema():
      """传入 output_schema 时返回 with_structured_output 包装后的 Runnable。"""
      from langchain_openai import ChatOpenAI
      with patch("app.core.parser_workflow.llm.settings") as mock_settings:
          mock_settings.LLM_API_KEY = "test-key"
          mock_settings.LLM_BASE_URL = ""
          model = create_chat_model("gpt-4o", "openai", output_schema=_DummySchema)
      # with_structured_output 返回的是 RunnableSequence，不再是 ChatOpenAI 本身
      assert not isinstance(model, ChatOpenAI)


  def test_create_chat_model_unknown_provider():
      """未知 provider 抛出 ValueError，错误信息包含支持的 provider 列表。"""
      with pytest.raises(ValueError, match="unknown_xyz"):
          create_chat_model("some-model", "unknown_xyz")
  ```

- [ ] **步骤 2：运行测试，确认全部失败（模块不存在）**

  ```bash
  cd agent-server && pytest tests/core/parser_workflow/test_llm.py -v
  ```

  预期：`ImportError: cannot import name 'create_chat_model' from 'app.core.parser_workflow.llm'`（或 ModuleNotFoundError）

- [ ] **步骤 3：新建 `app/core/parser_workflow/llm.py`，实现工厂**

  ```python
  from __future__ import annotations

  from typing import Type

  from langchain_core.runnables import Runnable
  from langchain_openai import ChatOpenAI
  from pydantic import BaseModel

  from app.core.config import settings


  def resolve_provider(node_provider: str | None) -> str:
      """
      Provider 解析优先级：
      1. node_provider（节点级 settings 字段）
      2. settings.PARSER_LLM_PROVIDER（全局默认）
      3. "openai"（硬编码兜底）
      """
      if node_provider:
          return node_provider
      if settings.PARSER_LLM_PROVIDER:
          return settings.PARSER_LLM_PROVIDER
      return "openai"


  def create_chat_model(
      model: str,
      provider: str,
      output_schema: Type[BaseModel] | dict | None = None,
      **kwargs,
  ) -> Runnable:
      """
      根据 provider 创建对应的 LangChain chat model。

      支持的 provider：
      - "openai"    → ChatOpenAI，使用 LLM_API_KEY / LLM_BASE_URL
      - "dashscope" → ChatOpenAI，使用 DASHSCOPE_API_KEY / DASHSCOPE_BASE_URL，
                      自动注入 extra_body={"enable_thinking": False}
      - "ollama"    → ChatOllama，使用 OLLAMA_BASE_URL

      若传入 output_schema，返回 llm.with_structured_output(output_schema)。
      未知 provider 抛出 ValueError。
      """
      if provider == "openai":
          llm = ChatOpenAI(
              model=model,
              api_key=settings.LLM_API_KEY,
              base_url=settings.LLM_BASE_URL or None,
              **kwargs,
          )
      elif provider == "dashscope":
          # 自动注入 enable_thinking=False，禁用通义千问思考模式，避免影响 structured output
          extra_body = {**kwargs.pop("extra_body", {}), "enable_thinking": False}
          llm = ChatOpenAI(
              model=model,
              api_key=settings.DASHSCOPE_API_KEY,
              base_url=settings.DASHSCOPE_BASE_URL,
              extra_body=extra_body,
              **kwargs,
          )
      elif provider == "ollama":
          from langchain_ollama import ChatOllama  # type: ignore[import]

          llm = ChatOllama(
              model=model,
              base_url=settings.OLLAMA_BASE_URL or "http://localhost:11434",
              **kwargs,
          )
      else:
          raise ValueError(
              f"未知 provider: {provider!r}。支持的 provider：openai, dashscope, ollama"
          )

      if output_schema is not None:
          return llm.with_structured_output(output_schema)
      return llm
  ```

- [ ] **步骤 4：运行测试，确认全部通过**

  ```bash
  cd agent-server && pytest tests/core/parser_workflow/test_llm.py -v
  ```

  预期：8 个测试全部 PASS

- [ ] **步骤 5：提交**

  ```bash
  git add app/core/parser_workflow/llm.py tests/core/parser_workflow/test_llm.py
  git commit -m "feat: add LLM provider factory (llm.py) with TDD"
  ```

---

## Chunk 2: 节点重构

> 以下 4 个 Task 是对现有节点的纯重构：不改变业务逻辑，只替换 LLM 创建方式。
> 每个节点现有的 mock 测试（mock `chat.invoke` 或 `_call_*_llm`）**无需修改**，直接作为回归测试。

---

### Task 3: 重构 `classify_node.py`

**文件：**
- 修改：`app/core/parser_workflow/nodes/classify_node.py`

**当前状态：**
- 第 14 行：`from langchain_openai import ChatOpenAI`
- 第 18-25 行：模块级 `chat = ChatOpenAI(...).with_structured_output(ClassifyOutput)`

- [ ] **步骤 1：删除模块级 `chat` 实例和 `langchain_openai` import，改用工厂**

  将文件头部 import 区替换为：

  ```python
  from app.core.parser_workflow.llm import create_chat_model, resolve_provider
  ```

  删除以下内容：
  ```python
  from langchain_openai import ChatOpenAI

  chat = ChatOpenAI(
      model=settings.CLASSIFY_MODEL,
      api_key=settings.LLM_API_KEY,
      base_url=settings.LLM_BASE_URL or None,
      extra_body={
          "enable_thinking": False
      },
  ).with_structured_output(ClassifyOutput)
  ```

  在 `_call_classify_llm` 函数体**最顶部**（`type_descriptions = ...` 这行之前）插入：

  ```python
  provider = resolve_provider(settings.CLASSIFY_LLM_PROVIDER)
  chat = create_chat_model(settings.CLASSIFY_MODEL, provider, output_schema=ClassifyOutput)
  ```

  函数签名和其余函数体（`type_descriptions`、prompt 构建、`result: ClassifyOutput = chat.invoke(prompt)`）保持不变。

  > **说明：** 原代码中的 `extra_body={"enable_thinking": False}` 已由工厂在 `dashscope` provider 中自动注入，调用方无需再传。

- [ ] **步骤 2：运行现有测试，确认回归通过**

  ```bash
  cd agent-server && pytest tests/ -v -k "classify" --ignore=tests/core/parser_workflow/test_workflow.py
  ```

  预期：所有 classify 相关测试 PASS（若无专项测试则跳过此步）

- [ ] **步骤 3：提交**

  ```bash
  git add app/core/parser_workflow/nodes/classify_node.py
  git commit -m "refactor: classify_node use LLM factory"
  ```

---

### Task 4: 重构 `escalate_node.py`

**文件：**
- 修改：`app/core/parser_workflow/nodes/escalate_node.py`

**当前状态：**
- 第 10 行：`from langchain_openai import ChatOpenAI`（模块级）
- 第 13-17 行：模块级 `chat = ChatOpenAI(...).with_structured_output(EscalateOutput)`
- 第 31 行：函数内 `from langchain_openai import ChatOpenAI`（内联，冗余）

- [ ] **步骤 1：删除模块级 `langchain_openai` import 和模块级 `chat`**

  将 `from langchain_openai import ChatOpenAI`（第 10 行）和以下模块级代码块一并删除：

  ```python
  from langchain_openai import ChatOpenAI   # ← 删除此行

  chat = ChatOpenAI(                         # ← 删除以下 5 行
      model=settings.ESCALATE_MODEL,
      api_key=settings.LLM_API_KEY,
      base_url=settings.LLM_BASE_URL or None,
  ).with_structured_output(EscalateOutput)
  ```

  在文件顶部 import 区增加：

  ```python
  from app.core.parser_workflow.llm import create_chat_model, resolve_provider
  ```

- [ ] **步骤 2：删除 `_call_escalate_llm` 函数体内的内联 import，改为工厂调用**

  `_call_escalate_llm` 函数体**第一行**（找到函数定义 `def _call_escalate_llm` 后的第一行）是：
  ```python
  from langchain_openai import ChatOpenAI  # type: ignore[import]   # ← 删除此行
  ```

  在删除该行后，在函数体**最顶部**（`type_list = ...` 这行之前）插入：

  ```python
  provider = resolve_provider(settings.ESCALATE_LLM_PROVIDER)
  chat = create_chat_model(settings.ESCALATE_MODEL, provider, output_schema=EscalateOutput)
  ```

  函数签名和其余函数体（prompt 构建、`chat.invoke`）保持不变。

- [ ] **步骤 3：运行现有测试，确认回归通过**

  ```bash
  cd agent-server && pytest tests/ -v -k "escalate" --ignore=tests/core/parser_workflow/test_workflow.py
  ```

- [ ] **步骤 4：提交**

  ```bash
  git add app/core/parser_workflow/nodes/escalate_node.py
  git commit -m "refactor: escalate_node use LLM factory"
  ```

---

### Task 5: 重构 `transform_node.py`

**文件：**
- 修改：`app/core/parser_workflow/nodes/transform_node.py`

**当前状态：**
- 第 15 行：`from langchain_openai import ChatOpenAI`
- 第 20-24 行：模块级 `chat = ChatOpenAI(...).with_structured_output(TransformOutput)`

- [ ] **步骤 1：删除模块级 `chat` 和 import，改用工厂**

  import 区替换：

  ```python
  from app.core.parser_workflow.llm import create_chat_model, resolve_provider
  ```

  删除：
  ```python
  from langchain_openai import ChatOpenAI

  chat = ChatOpenAI(
      model=settings.TRANSFORM_MODEL,
      api_key=settings.LLM_API_KEY,
      base_url=settings.LLM_BASE_URL or None,
  ).with_structured_output(TransformOutput)
  ```

  在 `_call_llm_transform` 函数体**最顶部**（`format_example = ...` 这行之前）插入：

  ```python
  provider = resolve_provider(settings.TRANSFORM_LLM_PROVIDER)
  chat = create_chat_model(settings.TRANSFORM_MODEL, provider, output_schema=TransformOutput)
  ```

  函数签名和其余函数体（`format_example`、prompt 构建、`resp: TransformOutput = chat.invoke(prompt)`）保持不变。

- [ ] **步骤 2：运行现有测试，确认回归通过**

  ```bash
  cd agent-server && pytest tests/ -v -k "transform" --ignore=tests/core/parser_workflow/test_workflow.py
  ```

- [ ] **步骤 3：提交**

  ```bash
  git add app/core/parser_workflow/nodes/transform_node.py
  git commit -m "refactor: transform_node use LLM factory"
  ```

---

### Task 6: 重构 `structure_node.py`

**文件：**
- 修改：`app/core/parser_workflow/nodes/structure_node.py`

**当前状态：**
- 第 9 行：`from langchain_openai import ChatOpenAI`（模块级）
- 第 19-24 行：模块级 `chat = ChatOpenAI(...).with_structured_output(DocTypeOutput)`
- 第 60 行：函数 `_infer_doc_type_with_llm` 内部有内联 `from langchain_openai import ChatOpenAI`（冗余）

- [ ] **步骤 1：删除模块级 `langchain_openai` import 和模块级 `chat`**

  将 `from langchain_openai import ChatOpenAI`（第 9 行）和以下模块级代码块一并删除：

  ```python
  from langchain_openai import ChatOpenAI   # ← 删除此行

  chat = ChatOpenAI(                         # ← 删除以下 6 行
      model=settings.DOC_TYPE_LLM_MODEL,
      api_key=settings.LLM_API_KEY,
      base_url=settings.LLM_BASE_URL or None,
      extra_body={"enable_thinking": False},
  ).with_structured_output(DocTypeOutput)
  ```

  在文件顶部 import 区增加：

  ```python
  from app.core.parser_workflow.llm import create_chat_model, resolve_provider
  ```

- [ ] **步骤 2：删除 `_infer_doc_type_with_llm` 函数体内的内联 import，改为工厂调用**

  `_infer_doc_type_with_llm` 函数体**第一行**（找到函数定义 `def _infer_doc_type_with_llm` 后的第一行）是：

  ```python
  from langchain_openai import ChatOpenAI  # type: ignore[import]   # ← 删除此行
  ```

  在删除该行后，在函数体**最顶部**（`existing_ids = ...` 这行之前）插入：

  ```python
  provider = resolve_provider(settings.DOC_TYPE_LLM_PROVIDER)
  chat = create_chat_model(settings.DOC_TYPE_LLM_MODEL, provider, output_schema=DocTypeOutput)
  ```

  函数签名和其余函数体（prompt 构建、`resp = chat.invoke(prompt)`）保持不变。

  > **说明：** 原代码中的 `extra_body={"enable_thinking": False}` 已由工厂在 `dashscope` provider 中自动注入，调用方无需再传。

- [ ] **步骤 3：运行现有测试，确认回归通过**

  ```bash
  cd agent-server && pytest tests/ -v -k "structure" --ignore=tests/core/parser_workflow/test_workflow.py
  ```

- [ ] **步骤 4：运行全部 parser_workflow 测试（排除需要真实 LLM 的集成测试）**

  ```bash
  cd agent-server && pytest tests/core/parser_workflow/ -v --ignore=tests/core/parser_workflow/test_workflow.py
  ```

  预期：全部 PASS

- [ ] **步骤 5：提交**

  ```bash
  git add app/core/parser_workflow/nodes/structure_node.py
  git commit -m "refactor: structure_node use LLM factory"
  ```

---

## 验收标准

- [ ] `pytest tests/core/parser_workflow/test_llm.py -v` 全部通过（8 个测试）
- [ ] `pytest tests/core/parser_workflow/ -v --ignore=tests/core/parser_workflow/test_workflow.py` 全部通过
- [ ] `grep -r "from langchain_openai import ChatOpenAI" app/core/parser_workflow/nodes/` 无输出（所有节点已清除）
- [ ] `.env` 中可通过 `PARSER_LLM_PROVIDER=ollama` 或 `CLASSIFY_LLM_PROVIDER=dashscope` 等配置切换 provider
