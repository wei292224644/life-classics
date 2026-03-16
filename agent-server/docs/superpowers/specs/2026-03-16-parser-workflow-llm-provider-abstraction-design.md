# Parser Workflow LLM Provider Abstraction Design

**Date:** 2026-03-16
**Scope:** `agent-server/app/core/parser_workflow/`

## Background

Four nodes in `parser_workflow` (`classify_node`, `escalate_node`, `transform_node`, `structure_node`) each create a `ChatOpenAI` instance at **module level** (import time). This hardcodes:

1. The provider as `langchain_openai.ChatOpenAI`
2. Configuration as fixed at import — cannot be changed per-call
3. Provider-specific quirks (e.g., DashScope's `extra_body={"enable_thinking": False}`) scattered across node files

Note: the fourth node is `structure_node.py`, which handles doc-type inference. Its provider is controlled by `DOC_TYPE_LLM_PROVIDER` / `DOC_TYPE_LLM_MODEL` — the naming reflects the logical role, not the file name.

## Goals

- Abstract LLM creation into a single factory
- Support per-node provider configuration with a global default fallback
- Extensible: adding a new provider requires changes only in `llm.py`
- Structured output (`with_structured_output`) compatibility is the caller's responsibility — no fallback logic needed

## Supported Providers

| Identifier | Implementation | Notes |
|------------|----------------|-------|
| `openai` | `langchain_openai.ChatOpenAI` | Uses `LLM_API_KEY` + `LLM_BASE_URL` |
| `dashscope` | `langchain_openai.ChatOpenAI` | Uses `DASHSCOPE_API_KEY` + `DASHSCOPE_BASE_URL`; auto-injects `extra_body={"enable_thinking": False}` |
| `ollama` | `langchain_ollama.ChatOllama` | Uses `OLLAMA_BASE_URL`, defaults to `http://localhost:11434` |

New providers are added by extending the factory in `llm.py` only.

## Configuration

### New settings in `app/core/config.py`

```
# Provider selection
PARSER_LLM_PROVIDER=openai       # Global default for all parser_workflow nodes
CLASSIFY_LLM_PROVIDER=           # Node-level override; empty = use global default
ESCALATE_LLM_PROVIDER=
TRANSFORM_LLM_PROVIDER=
DOC_TYPE_LLM_PROVIDER=           # Used in structure_node.py

# DashScope credentials (separate from OpenAI)
DASHSCOPE_API_KEY=
DASHSCOPE_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
```

Resolution order for provider: node-level setting → `PARSER_LLM_PROVIDER` → `"openai"` (hardcoded fallback).

**Provider-to-credentials mapping:**
- `openai` → `LLM_API_KEY`, `LLM_BASE_URL`
- `dashscope` → `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL`
- `ollama` → `OLLAMA_BASE_URL`

This allows OpenAI and DashScope to coexist without sharing `LLM_BASE_URL`.

### `ParserConfig` (`parser_workflow/config.py`)

Add optional fields for runtime provider override via `run_parser_workflow(..., config={...})`.
Nodes read provider from both `settings` and `state["config"]`, with `state["config"]` taking priority.

```python
class ParserConfig(TypedDict, total=False):
    # existing fields...
    parser_llm_provider: str
    classify_llm_provider: str
    escalate_llm_provider: str
    transform_llm_provider: str
    doc_type_llm_provider: str
```

## New File: `parser_workflow/llm.py`

### Public API

```python
from typing import Type
from pydantic import BaseModel

def resolve_provider(node_provider: str | None, config: dict | None = None) -> str:
    """
    Resolution order:
    1. config[node_key] if provided
    2. node_provider (from settings)
    3. settings.PARSER_LLM_PROVIDER
    4. "openai" (hardcoded fallback)
    """

def create_chat_model(
    model: str,
    provider: str,
    output_schema: Type[BaseModel] | dict | None = None,
    **kwargs,
) -> Runnable:
    """
    Create and return the appropriate LangChain chat model.
    output_schema: a Pydantic BaseModel subclass or JSON schema dict accepted
                   by LangChain's with_structured_output(). If provided, returns
                   the wrapped runnable.
    Raises ValueError for unknown providers.
    """
```

### Factory Logic

```python
def create_chat_model(model, provider, output_schema=None, **kwargs):
    if provider == "openai":
        llm = ChatOpenAI(model=model, api_key=settings.LLM_API_KEY,
                         base_url=settings.LLM_BASE_URL or None, **kwargs)
    elif provider == "dashscope":
        llm = ChatOpenAI(model=model, api_key=settings.DASHSCOPE_API_KEY,
                         base_url=settings.DASHSCOPE_BASE_URL,
                         extra_body={"enable_thinking": False}, **kwargs)
    elif provider == "ollama":
        llm = ChatOllama(model=model,
                         base_url=settings.OLLAMA_BASE_URL or "http://localhost:11434",
                         **kwargs)
    else:
        raise ValueError(
            f"Unknown provider: {provider!r}. Supported: openai, dashscope, ollama"
        )

    if output_schema is not None:
        return llm.with_structured_output(output_schema)
    return llm
```

## Node Changes

All four nodes follow the same pattern. The module-level `chat = ChatOpenAI(...)` and all `from langchain_openai import ChatOpenAI` imports (including any function-scoped ones) are removed. Provider creation moves into the LLM-calling helper function.

Example (`classify_node.py`):

**Before:**
```python
# module level
from langchain_openai import ChatOpenAI

chat = ChatOpenAI(
    model=settings.CLASSIFY_MODEL,
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_BASE_URL or None,
    extra_body={"enable_thinking": False},
).with_structured_output(ClassifyOutput)

def _call_classify_llm(chunk_content, content_types):
    result: ClassifyOutput = chat.invoke(prompt)
```

**After:**
```python
# no module-level chat instance; no langchain_openai import
from app.core.parser_workflow.llm import create_chat_model, resolve_provider

def _call_classify_llm(chunk_content, content_types):
    provider = resolve_provider(settings.CLASSIFY_LLM_PROVIDER)
    chat = create_chat_model(settings.CLASSIFY_MODEL, provider, ClassifyOutput)
    result: ClassifyOutput = chat.invoke(prompt)
```

**Notes on inline imports to remove:**
- `escalate_node.py` has a redundant `from langchain_openai import ChatOpenAI` inside `_call_escalate_llm` (line 31) — remove it
- `structure_node.py` has a redundant `from langchain_openai import ChatOpenAI` inside `_infer_doc_type_with_llm` (line 60) — remove it

## Files Changed

| File | Change |
|------|--------|
| `parser_workflow/llm.py` | **New** — factory + resolve_provider |
| `app/core/config.py` | Add `PARSER_LLM_PROVIDER`, `CLASSIFY_LLM_PROVIDER`, `ESCALATE_LLM_PROVIDER`, `TRANSFORM_LLM_PROVIDER`, `DOC_TYPE_LLM_PROVIDER`, `DASHSCOPE_API_KEY`, `DASHSCOPE_BASE_URL` |
| `parser_workflow/config.py` | Add 5 provider fields to `ParserConfig` |
| `parser_workflow/nodes/classify_node.py` | Remove module-level `chat` + `langchain_openai` import, use factory |
| `parser_workflow/nodes/escalate_node.py` | Remove module-level `chat` + both `langchain_openai` imports, use factory |
| `parser_workflow/nodes/transform_node.py` | Remove module-level `chat` + `langchain_openai` import, use factory |
| `parser_workflow/nodes/structure_node.py` | Remove module-level `chat` + both `langchain_openai` imports, use factory |
| `tests/core/parser_workflow/test_llm.py` | **New** — unit tests for factory |

## Testing

### New tests (`test_llm.py`)

- `create_chat_model("gpt-4o", "openai")` returns `ChatOpenAI` instance
- `create_chat_model("qwen-max", "dashscope")` returns `ChatOpenAI` with `extra_body={"enable_thinking": False}` and DashScope credentials
- `create_chat_model("llama3", "ollama")` returns `ChatOllama` instance
- `create_chat_model(..., output_schema=MySchema)` returns wrapped runnable (not bare LLM)
- `create_chat_model("x", "unknown_provider")` raises `ValueError`
- `resolve_provider("ollama")` returns `"ollama"`
- `resolve_provider(None)` with `PARSER_LLM_PROVIDER="dashscope"` returns `"dashscope"`
- `resolve_provider(None)` with `PARSER_LLM_PROVIDER=""` (unset) returns `"openai"` (hardcoded fallback)

### Existing tests

No changes needed. Existing tests mock at `_call_classify_llm`, `_call_escalate_llm`, `_infer_doc_type_with_llm`, or `chat.invoke` — these mock targets are unaffected by this refactor.

## Error Handling

- Unknown provider → `ValueError` with clear message listing supported options
- Missing credentials (e.g., empty `LLM_API_KEY` for OpenAI) → raised by LangChain at invoke time, not wrapped
