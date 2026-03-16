# Parser Workflow LLM Provider Abstraction Design

**Date:** 2026-03-16
**Scope:** `agent-server/app/core/parser_workflow/`

## Background

Four nodes in `parser_workflow` (`classify_node`, `escalate_node`, `transform_node`, `structure_node`) each create a `ChatOpenAI` instance at **module level** (import time). This hardcodes:

1. The provider as `langchain_openai.ChatOpenAI`
2. Configuration as fixed at import — cannot be changed per-call
3. Provider-specific quirks (e.g., DashScope's `extra_body={"enable_thinking": False}`) scattered across node files

## Goals

- Abstract LLM creation into a single factory
- Support per-node provider configuration with a global default fallback
- Extensible: adding a new provider requires changes only in `llm.py`
- Structured output (`with_structured_output`) compatibility is the caller's responsibility — no fallback logic needed

## Supported Providers

| Identifier | Implementation | Notes |
|------------|----------------|-------|
| `openai` | `langchain_openai.ChatOpenAI` | Standard OpenAI or compatible API |
| `dashscope` | `langchain_openai.ChatOpenAI` | DashScope base URL + `extra_body={"enable_thinking": False}` auto-injected |
| `ollama` | `langchain_ollama.ChatOllama` | Local Ollama instance |

New providers are added by extending the factory in `llm.py` only.

## Configuration

### New settings in `app/core/config.py`

```
PARSER_LLM_PROVIDER=openai       # Global default for all parser_workflow nodes
CLASSIFY_LLM_PROVIDER=           # Node-level override; empty = use global default
ESCALATE_LLM_PROVIDER=
TRANSFORM_LLM_PROVIDER=
DOC_TYPE_LLM_PROVIDER=
```

Resolution order: node-level setting → `PARSER_LLM_PROVIDER` → `"openai"` (hardcoded fallback).

### `ParserConfig` (`parser_workflow/config.py`)

Add corresponding optional fields so provider can also be passed at call time via `run_parser_workflow(..., config={...})`:

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
def resolve_provider(node_provider: str | None) -> str:
    """Return node_provider if set, else settings.PARSER_LLM_PROVIDER, else 'openai'."""

def create_chat_model(
    model: str,
    provider: str,
    output_schema=None,
    **kwargs,
) -> Runnable:
    """
    Create and return the appropriate LangChain chat model.
    If output_schema is provided, returns model.with_structured_output(output_schema).
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
        llm = ChatOpenAI(model=model, api_key=settings.LLM_API_KEY,
                         base_url=settings.LLM_BASE_URL or None,
                         extra_body={"enable_thinking": False}, **kwargs)
    elif provider == "ollama":
        llm = ChatOllama(model=model,
                         base_url=settings.OLLAMA_BASE_URL or "http://localhost:11434",
                         **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider!r}. Supported: openai, dashscope, ollama")

    if output_schema is not None:
        return llm.with_structured_output(output_schema)
    return llm
```

## Node Changes

All four nodes follow the same pattern. Example (`classify_node.py`):

**Before:**
```python
# module level
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
# no module-level chat instance

def _call_classify_llm(chunk_content, content_types):
    provider = resolve_provider(settings.CLASSIFY_LLM_PROVIDER)
    chat = create_chat_model(settings.CLASSIFY_MODEL, provider, ClassifyOutput)
    result: ClassifyOutput = chat.invoke(prompt)
```

The `from langchain_openai import ChatOpenAI` import is removed from all node files and lives only in `llm.py`.

## Files Changed

| File | Change |
|------|--------|
| `parser_workflow/llm.py` | **New** — factory + resolve_provider |
| `app/core/config.py` | Add 5 new provider config fields |
| `parser_workflow/config.py` | Add 5 provider fields to `ParserConfig` |
| `parser_workflow/nodes/classify_node.py` | Remove module-level `chat`, use factory |
| `parser_workflow/nodes/escalate_node.py` | Remove module-level `chat`, use factory |
| `parser_workflow/nodes/transform_node.py` | Remove module-level `chat`, use factory |
| `parser_workflow/nodes/structure_node.py` | Remove module-level `chat`, use factory |
| `tests/core/parser_workflow/test_llm.py` | **New** — unit tests for factory |

## Testing

### New tests (`test_llm.py`)

- `create_chat_model("gpt-4o", "openai")` returns `ChatOpenAI` instance
- `create_chat_model("qwen-max", "dashscope")` returns `ChatOpenAI` with `extra_body`
- `create_chat_model("llama3", "ollama")` returns `ChatOllama` instance
- `create_chat_model(..., output_schema=MySchema)` returns wrapped runnable
- `create_chat_model("x", "unknown_provider")` raises `ValueError`
- `resolve_provider(None)` returns `settings.PARSER_LLM_PROVIDER`
- `resolve_provider("ollama")` returns `"ollama"`

### Existing tests

No changes needed. Existing tests mock `chat.invoke` or `_call_classify_llm` directly — these mocking points are unaffected.

## Error Handling

- Unknown provider → `ValueError` with clear message listing supported options
- Missing credentials (e.g., empty `LLM_API_KEY` for OpenAI) → raised by LangChain at invoke time, not wrapped
