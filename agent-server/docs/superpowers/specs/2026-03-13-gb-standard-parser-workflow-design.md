# GB 国家标准解析 Workflow 设计文档

**日期**：2026-03-13
**状态**：待实现
**范围**：独立的 LangGraph Workflow，将 MinerU 转换后的 Markdown 文件解析为结构化 `List[DocumentChunk]`，供外部调用方写入知识库。

---

## 1. 目标与约束

### 目标
构建一个完全独立的 LangGraph Workflow，只做一件事：将 MinerU 输出的 Markdown 文件，通过自动切片 + LLM 语义分类 + 按类型转化，输出为结构化 `List[DocumentChunk]`。

### 独立性声明
本 Workflow 与现有代码库（`app/core/kb/strategy/`、`app/core/document_chunk.py` 等）**完全独立**，不复用、不依赖现有类和函数。`DocumentChunk` 是本 Workflow 专属的输出数据结构，外部调用方负责将其适配到目标存储系统的格式。

### 约束
- Workflow 本身**无副作用**：不直接写数据库，输出纯数据对象，由外部调用方决定如何存储
- 切片逻辑**纯规则**，不调用 LLM
- LLM 仅在两处介入：content_type 分类（小模型）、未知情况的兜底推断（大模型）
- 规则以**外部 JSON 文件**形式管理，运行时动态加载，支持运行中追加新规则
- 规则文件不存在时自动初始化为内置默认值

---

## 2. Workflow 节点图

```
[parse_node]
    ↓ md_content + doc_metadata
[structure_node]                ← 原名 compress_node，重命名以准确反映职责
    ↓ 提取标题层级结构 + 推断 doc_type（规则优先，规则失败时调 LLM）
      → 新 doc_type 规则 append 到 doc_type_rules.json
[slice_node]
    ↓ 按标题递归切分 + 字符阈值控制，输出 List[RawChunk]
[classify_node]
    ↓ 小模型逐块分析，拆解为 List[TypedSegment]
    ├── 全部 confidence 达标 ──────────────────→ [transform_node]
    └── 含 unknown / 低置信度片段 → [escalate_node]
                                        ↓ 大模型语义匹配：unknown 片段是否符合已有 content_type？
                                        ├── 匹配已有 → 直接回写，不创建新规则
                                        └── 不匹配 → 创建新 content_type（含 strategy + prompt_template）
                                        ↓ append 新规则到 content_type_rules.json（仅创建时）
                                   [transform_node]
    ↓ 每块 List[TypedSegment] → 处理后输出 List[DocumentChunk]（一块可产出多个）
输出：List[DocumentChunk]
```

### 节点职责一览

| 节点 | 职责 | LLM | 规则文件 |
|---|---|---|---|
| `parse_node` | 读取 MD 文件，提取文档元数据 | 否 | 否 |
| `structure_node` | 提取标题结构 + 推断 doc_type | 失败时调用 | `doc_type_rules.json` |
| `slice_node` | 递归标题切分 + 字符阈值控制 | 否 | 无（配置项） |
| `classify_node` | 每块拆解为 List[TypedSegment] | 小模型 | `content_type_rules.json` |
| `escalate_node` | unknown 片段语义匹配已有类型 / 创建新类型（含 prompt_template） | 大模型 | `content_type_rules.json` |
| `transform_node` | 按 transform_params 转化，输出 List[DocumentChunk] | 条件性（llm_transform 策略时） | 读 transform_params |

### LangGraph 图结构定义

```python
from langgraph.graph import StateGraph, END

def should_escalate(state: WorkflowState) -> str:
    """conditional edge: classify_node 后判断是否需要 escalate"""
    has_unknown = any(
        chunk.has_unknown for chunk in state["classified_chunks"]
    )
    return "escalate_node" if has_unknown else "transform_node"

builder = StateGraph(WorkflowState)
builder.add_node("parse_node", parse_node)
builder.add_node("structure_node", structure_node)
builder.add_node("slice_node", slice_node)
builder.add_node("classify_node", classify_node)
builder.add_node("escalate_node", escalate_node)
builder.add_node("transform_node", transform_node)

builder.set_entry_point("parse_node")
builder.add_edge("parse_node", "structure_node")
builder.add_edge("structure_node", "slice_node")
builder.add_edge("slice_node", "classify_node")
builder.add_conditional_edges("classify_node", should_escalate)
builder.add_edge("escalate_node", "transform_node")
builder.add_edge("transform_node", END)

graph = builder.compile()
```

---

## 3. 核心数据结构

```python
# Workflow 全局状态（LangGraph State）
class WorkflowState(TypedDict):
    md_content: str
    doc_metadata: dict              # standard_no, title, year, doc_type, doc_type_source
    config: "ParserConfig"          # 由 run_parser_workflow 注入，节点通过 state["config"] 读取
    rules_dir: str                  # 规则文件目录，由 run_parser_workflow 注入
    raw_chunks: List[RawChunk]
    classified_chunks: List[ClassifiedChunk]
    final_chunks: List[DocumentChunk]
    errors: List[str]               # 非阻塞错误，如超 HARD_MAX 的块

# 切片后的原始块
class RawChunk(TypedDict):
    content: str
    section_path: List[str]         # 标题文字列表，如 ["3 范围", "3.1 适用范围"]
    char_count: int

# classify_node 输出（一个 RawChunk 的分析结果）
class ClassifiedChunk(TypedDict):
    raw_chunk: RawChunk
    segments: List[TypedSegment]
    has_unknown: bool               # 是否含需要 escalate 的片段

# 有类型的内容片段（LLM 完成分段 + 分类）
class TypedSegment(TypedDict):
    content: str
    content_type: str               # "table" / "formula" / "plain_text" / ...
    transform_params: dict          # 来自 content_type_rules.json 的转化参数
    confidence: float               # < CONFIDENCE_THRESHOLD 时触发 escalate
    escalated: bool                 # 是否经过 escalate_node 处理（默认 False，escalate 后置 True）

# 最终输出块（本 Workflow 专属，调用方负责适配目标存储格式）
class DocumentChunk(TypedDict):
    chunk_id: str                   # sha256(standard_no + section_path_str + content)[:16]
    doc_metadata: dict              # 含 doc_type、standard_no、title、year 等
    section_path: List[str]         # 与 RawChunk.section_path 一致
    content_type: str               # 该 chunk 的主要内容类型：
                                    # - split_rows 产出的行 chunk：固定为源 segment 的 content_type
                                    # - 单输出 chunk：按字符数占比最高的 segment 的 content_type
    content: str                    # transform 后的文本内容，用于向量化
    raw_content: str                # 原始 Markdown 内容，原样保留
    meta: dict                      # 扩展元数据（如 table_row_index、formula_vars 等）
```

### chunk_id 生成规则
```python
import hashlib

def make_chunk_id(standard_no: str, section_path: List[str], content: str) -> str:
    key = f"{standard_no}|{'|'.join(section_path)}|{content[:100]}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]
```

---

## 4. 切片逻辑（slice_node）

### 配置项

| 参数 | 默认值 | 说明 |
|---|---|---|
| `SLICE_HEADING_LEVELS` | `[2, 3, 4]` | 按序尝试的标题级别（整数，对应 `##`=2，`###`=3，`####`=4） |
| `CHUNK_SOFT_MAX` | 1500 字符 | 超过则尝试下一级标题继续拆 |
| `CHUNK_HARD_MAX` | 3000 字符 | 超过且无标题可拆则保留，记录 warning |

### 前置内容处理
标题之前的内容（文档前言、封面信息等）作为独立块保留，`section_path = ["__preamble__"]`，不参与递归切分。

### 算法

```
recursive_slice(content, heading_levels, parent_path):
    1. 按 heading_levels[0] 级别标题切分
    2. 若无该级别标题 → 作为整体处理（跳到步骤 4）
    3. 对每个子块（含其标题）：
       a. char_count <= SOFT_MAX → 保留为 RawChunk
       b. char_count > SOFT_MAX 且 len(heading_levels) > 1
          → recursive_slice(子块, heading_levels[1:], 更新后的 path)
       c. char_count > HARD_MAX 且 heading_levels 已空
          → 保留为 RawChunk，errors.append(f"WARN: chunk exceeds HARD_MAX at {path}")
    4. 收集所有子块，返回 List[RawChunk]
```

---

## 5. 规则文件设计

规则文件存放在 `rules_dir` 目录下。若文件不存在，首次运行时自动创建并写入内置默认规则。

### 5.1 文档类型规则（`doc_type_rules.json`）

```json
{
  "version": "1.0",
  "match_threshold": 2,
  "doc_types": [
    {
      "id": "single_additive",
      "description": "单一食品添加剂或产品标准，含技术要求和理化指标",
      "detect_keywords": ["技术要求", "理化指标", "鉴别", "含量"],
      "detect_heading_patterns": ["技术要求", "检验规则"],
      "source": "rule"
    },
    {
      "id": "detection_method",
      "description": "检测方法标准，含多种方法、试剂、仪器、操作步骤",
      "detect_keywords": ["方法一", "方法二", "试剂", "仪器", "操作步骤"],
      "detect_heading_patterns": ["试剂和材料", "仪器和设备", "分析步骤"],
      "source": "rule"
    },
    {
      "id": "microbiological",
      "description": "微生物检验标准，含培养基、流程图、判定规则",
      "detect_keywords": ["培养基", "菌落", "接种", "判定"],
      "detect_heading_patterns": ["培养基和试剂", "检验程序"],
      "source": "rule"
    }
  ]
}
```

**推断逻辑（structure_node 内部）**：
1. 提取文档所有 `##` 标题列表
2. 对每个 `doc_type` 统计匹配项数（`detect_keywords` + `detect_heading_patterns` 各计 1 分）
3. 最高分 >= `match_threshold` → 命中，`doc_type_source = "rule"`
4. 无命中 → 调 LLM，传入压缩后的标题列表，要求返回以下 JSON：
   ```json
   {
     "id": "new_type_id",
     "description": "...",
     "detect_keywords": ["...", "..."],
     "detect_heading_patterns": ["..."],
     "source": "llm"
   }
   ```
   验证格式后 append 到 `doc_type_rules.json`，`doc_type_source = "llm"`

### 5.2 内容类型规则（`content_type_rules.json`）

```json
{
  "version": "1.0",
  "confidence_threshold": 0.7,
  "content_types": [
    {
      "id": "table",
      "description": "Markdown 表格，以 | 开头的连续行",
      "transform": {
        "strategy": "split_rows",
        "preserve_header": true
      }
    },
    {
      "id": "formula",
      "description": "数学或化学公式，含 LaTeX 语法或化学分子式",
      "transform": {
        "strategy": "preserve_as_is"
      }
    },
    {
      "id": "numbered_list",
      "description": "有序编号列表，步骤或条款",
      "transform": {
        "strategy": "preserve_as_list"
      }
    },
    {
      "id": "plain_text",
      "description": "普通说明性段落，无特殊结构",
      "transform": {
        "strategy": "plain_embed"
      }
    }
  ]
}
```

**classify_node 分类逻辑**：
- 小模型接收：RawChunk 文本 + `content_type_rules.json` 中所有 content_type 的 id + description
- 模型职责：**同时完成分段和分类**——将 chunk 文本拆解为语义片段，为每段指定 content_type 和 confidence
- 模型输出 schema（强制 structured output）：
  ```json
  {
    "segments": [
      {
        "content": "...",
        "content_type": "table",
        "confidence": 0.95
      }
    ]
  }
  ```
- `confidence < confidence_threshold` 的片段标记为 `unknown`，交由 `escalate_node`

**escalate_node 扩展逻辑**：

职责单一：判断 unknown 片段归属，必要时创建新类型规则。不执行内容转化。

**Step 1 — 语义匹配已有类型（LLM）**：
- 大模型接收：unknown 片段文本 + 已有 content_type 列表（id + description）
- 大模型判断：该片段是否语义上符合某个已有 content_type？
- 若匹配 → 直接回写该 content_type，**不创建新规则，不写文件**，流程结束

**Step 2 — 创建新类型（LLM，仅 Step 1 未匹配时执行）**：
- 大模型为该片段生成新 content_type，输出 schema（强制 structured output）：
  ```json
  {
    "action": "create_new",
    "content_type": "new_type_id",
    "description": "...",
    "transform": {
      "strategy": "llm_transform",
      "prompt_template": "请将以下GB标准内容转化为规范化文本：\n{content}"
    }
  }
  ```
  strategy 可为 `llm_transform` 或现有四种确定性策略之一；`prompt_template` 仅 `llm_transform` 时必填。
- 验证格式后 append 到 `content_type_rules.json`，当前运行立即生效

**状态回写**：escalate_node 将 unknown 片段的 `content_type` 补全后，直接修改 `state["classified_chunks"]` 中对应 `TypedSegment` 的字段（`content_type` 更新为推断结果，`confidence` 更新为 1.0，`transform_params` 更新为对应规则的 transform 字段），`has_unknown` 置为 `False`。`transform_node` 始终从 `state["classified_chunks"]` 读取，无需区分是否经过 escalate。

---

## 6. transform_node 转化策略

**一个 RawChunk 可产出多个 DocumentChunk**（例如表格按行拆分时）。

| strategy | 行为 | LLM | 产出 DocumentChunk 数 |
|---|---|---|---|
| `split_rows` | 表格每行作为独立 chunk，行内容 + 表头上下文拼接为 content | 否 | 每行一个 |
| `preserve_as_is` | 原样保留，content = raw_content | 否 | 1 个 |
| `preserve_as_list` | 列表结构保留，去除多余空白 | 否 | 1 个 |
| `plain_embed` | 文本内容，去除多余空白 | 否 | 1 个 |
| `llm_transform` | 读取 `transform_params.prompt_template`，将 `{content}` 替换为原始内容后调用 LLM，输出转化后文本 | 是（`transform_model`，fallback `escalate_model`） | 1 个 |

`split_rows` 产出多行时，每个 `DocumentChunk.meta` 中附加 `table_row_index: int`，`content_type` 均标记为 `"table"`。

`llm_transform` 产出的 DocumentChunk 中，`raw_content` 保留原始 Markdown，`content` 为 LLM 转化结果。

---

## 7. 对外接口

```python
class ParserConfig(TypedDict, total=False):
    # 切片参数
    chunk_soft_max: int             # 默认 1500
    chunk_hard_max: int             # 默认 3000
    slice_heading_levels: List[int] # 默认 [2, 3, 4]
    # LLM 参数
    classify_model: str             # 小模型，用于 classify_node
    escalate_model: str             # 大模型，用于 escalate_node
    transform_model: str            # llm_transform 策略时使用的模型，不填则 fallback 到 escalate_model
    doc_type_llm_model: str         # structure_node LLM 推断时使用的模型
    llm_api_key: str
    llm_base_url: str
    # 行为控制
    confidence_threshold: float     # 默认读 content_type_rules.json，此处可覆盖

async def run_parser_workflow(
    md_content: str,
    doc_metadata: dict,             # 至少包含 standard_no, title
    rules_dir: str,                 # content_type_rules.json 和 doc_type_rules.json 所在目录
    config: ParserConfig = {},
) -> ParserResult:
    initial_state: WorkflowState = {
        "md_content": md_content,
        "doc_metadata": doc_metadata,
        "config": config,
        "rules_dir": rules_dir,
        "raw_chunks": [],
        "classified_chunks": [],
        "final_chunks": [],
        "errors": [],
    }
    result_state = await graph.ainvoke(initial_state)
    # escalate_count 在 escalate_node 运行前统计（has_unknown 在回写后置 False，故此处用 final_chunks 中的 meta 标记）
    escalate_count = sum(
        1 for c in result_state["classified_chunks"]
        if any(s.get("escalated") for s in c["segments"])
    )
    return ParserResult(
        chunks=result_state["final_chunks"],
        doc_metadata=result_state["doc_metadata"],
        errors=result_state["errors"],
        stats={
            "chunk_count": len(result_state["final_chunks"]),
            "escalate_count": escalate_count,  # 触发过 escalate 的 chunk 数
        }
    )

class ParserResult(TypedDict):
    chunks: List[DocumentChunk]
    doc_metadata: dict
    errors: List[str]
    stats: dict                     # chunk_count, escalate_count 等
```

### classify_node 执行模式
- 当前阶段：**顺序处理**，逐个 RawChunk 调用 LLM（实现简单，便于调试）
- 规则文件在每次 `run_parser_workflow` 调用开始时加载一次，escalate_node 追加规则后立即重载，在当前运行内生效
- 规则文件写入使用文件追加（append），不加分布式锁（当前单进程场景无需）

---

## 8. 扩展原则

- **新 content_type**：向 `content_type_rules.json` append 一条 entry，无需修改代码
- **新 doc_type**：向 `doc_type_rules.json` append 一条 entry，无需修改代码
- **新 transform strategy**：在 `transform_node` 中注册新的 strategy 函数，JSON 中通过 `"strategy"` 字段引用
- **切片参数**：通过 `ParserConfig` 调整，无需修改 Workflow 节点逻辑
- **并发扩展**：如需并行处理多个 chunk，可将 `classify_node` 改为 LangGraph `Send`-based fan-out，接口不变
