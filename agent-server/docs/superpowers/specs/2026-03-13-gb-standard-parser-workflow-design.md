# GB 国家标准解析 Workflow 设计文档

**日期**：2026-03-13
**状态**：待实现
**范围**：独立的 LangGraph Workflow，将 MinerU 转换后的 Markdown 文件解析为结构化 `List[DocumentChunk]`，供外部调用方写入知识库。

---

## 1. 目标与约束

### 目标
构建一个完全独立的 LangGraph Workflow，只做一件事：将 MinerU 输出的 Markdown 文件，通过自动切片 + LLM 语义分类 + 按类型转化，输出为结构化 `List[DocumentChunk]`。

### 约束
- Workflow 本身**无副作用**：不直接写数据库，输出纯数据对象，由外部调用方决定如何存储
- 切片逻辑**纯规则**，不调用 LLM
- LLM 仅在两处介入：content_type 分类（小模型）、未知情况的兜底推断（大模型）
- 规则以**外部 JSON 文件**形式管理，运行时动态加载，支持运行中追加新规则

---

## 2. Workflow 节点图

```
[parse_node]
    ↓ md_content + doc_metadata
[compress_node]
    ↓ 提取标题层级结构 + 推断 doc_type（规则优先，规则失败时调 LLM）
      → 新 doc_type 规则 append 到 doc_type_rules.json
[slice_node]
    ↓ 按标题递归切分 + 字符阈值控制，输出 List[RawChunk]
[classify_node]
    ↓ 小模型逐块分析，拆解为 List[TypedSegment]
    ├── 全部 confidence 达标 ──────────────────→ [transform_node]
    └── 含 unknown / 低置信度片段 → [escalate_node]
                                        ↓ 大模型分析 unknown 片段
                                        ↓ 补全 content_type
                                        ↓ append 新规则到 content_type_rules.json
                                   [transform_node]
    ↓ 每块 List[TypedSegment] → 处理后合并为 DocumentChunk
输出：List[DocumentChunk]
```

### 节点职责一览

| 节点 | 职责 | LLM | 规则文件 |
|---|---|---|---|
| `parse_node` | 读取 MD 文件，提取文档元数据 | 否 | 否 |
| `compress_node` | 提取标题结构 + 推断 doc_type | 失败时调用 | `doc_type_rules.json` |
| `slice_node` | 递归标题切分 + 字符阈值控制 | 否 | 无（配置项） |
| `classify_node` | 每块拆解为 List[TypedSegment] | 小模型 | `content_type_rules.json` |
| `escalate_node` | 处理 unknown 片段 + 追加新规则 | 大模型 | `content_type_rules.json` |
| `transform_node` | 按 transform_params 转化，合并为 DocumentChunk | 否 | 读 transform_params |

---

## 3. 核心数据结构

```python
# Workflow 全局状态
class WorkflowState(TypedDict):
    md_content: str
    doc_metadata: dict              # standard_no, title, year, doc_type, doc_type_source
    raw_chunks: List[RawChunk]
    classified_chunks: List[ClassifiedChunk]
    final_chunks: List[DocumentChunk]
    errors: List[str]               # 非阻塞错误，如超 HARD_MAX 的块

# 切片后的原始块
class RawChunk(TypedDict):
    content: str
    section_path: List[str]         # 如 ["3", "3.1", "3.1.2"]
    char_count: int

# classify_node 输出（一个 RawChunk 的分析结果）
class ClassifiedChunk(TypedDict):
    raw_chunk: RawChunk
    segments: List[TypedSegment]
    has_unknown: bool               # 是否含需要 escalate 的片段

# 有类型的内容片段
class TypedSegment(TypedDict):
    content: str
    content_type: str               # "table" / "formula" / "plain_text" / ...
    transform_params: dict          # 来自 content_type_rules.json 的转化参数
    confidence: float               # < CONFIDENCE_THRESHOLD 时触发 escalate

# 最终输出块
class DocumentChunk(TypedDict):
    chunk_id: str
    doc_metadata: dict              # 含 doc_type、standard_no 等
    section_path: List[str]
    segments: List[TypedSegment]
    content_summary: str            # transform 后的文本表示，用于向量化
```

---

## 4. 切片逻辑（slice_node）

### 配置项

| 参数 | 默认值 | 说明 |
|---|---|---|
| `SLICE_HEADING_LEVELS` | `[##, ###, ####]` | 按序尝试的标题级别 |
| `CHUNK_SOFT_MAX` | 1500 字符 | 超过则尝试下一级标题继续拆 |
| `CHUNK_HARD_MAX` | 3000 字符 | 超过且无标题可拆则保留，记录 warning |

### 算法

```
recursive_slice(content, heading_levels):
    1. 按 heading_levels[0] 切分
    2. 对每个子块：
       a. char_count <= SOFT_MAX → 保留
       b. char_count > SOFT_MAX 且还有更细标题级别 → recursive_slice(子块, heading_levels[1:])
       c. char_count > HARD_MAX 且 heading_levels 已空 → 保留原块，errors.append(warning)
```

---

## 5. 规则文件设计

### 5.1 文档类型规则（`doc_type_rules.json`）

```json
{
  "version": "1.0",
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

**推断逻辑（compress_node 内部）**：
1. 提取所有 `##` 标题列表
2. 逐个 `doc_type` 计算关键词匹配分（`detect_keywords` + `detect_heading_patterns`）
3. 最高分超过阈值 → 命中，`doc_type_source = "rule"`
4. 无命中 → 调 LLM，传入压缩后的标题列表，返回新 `doc_type` + 规则描述 → append 到文件，`doc_type_source = "llm"`

### 5.2 内容类型规则（`content_type_rules.json`）

```json
{
  "version": "1.0",
  "confidence_threshold": 0.7,
  "content_types": [
    {
      "id": "table",
      "description": "Markdown 表格，以 | 开头的连续行",
      "detect_pattern": "^\\|",
      "transform": {
        "strategy": "split_rows",
        "preserve_header": true
      }
    },
    {
      "id": "formula",
      "description": "数学或化学公式，含 LaTeX 语法或化学分子式",
      "detect_pattern": "\\$.*\\$|\\\\frac|[A-Z][a-z]?\\d*[\\+\\-]?",
      "transform": {
        "strategy": "preserve_as_is"
      }
    },
    {
      "id": "numbered_list",
      "description": "有序编号列表，步骤或条款",
      "detect_pattern": "^\\d+[\\.)）]",
      "transform": {
        "strategy": "preserve_as_list"
      }
    },
    {
      "id": "plain_text",
      "description": "普通说明性段落，无特殊结构",
      "detect_pattern": ".*",
      "transform": {
        "strategy": "plain_embed"
      }
    }
  ]
}
```

**分类逻辑（classify_node 内部）**：
- 小模型接收：chunk 文本 + `content_type_rules.json` 内容（作为 prompt 的一部分）
- 模型输出：每个片段的 `content_type` + `confidence`
- `confidence < threshold` 的片段标记为 `unknown`，交由 `escalate_node` 处理

**escalate_node 扩展逻辑**：
- 大模型接收：unknown 片段文本 + 已有 content_type 列表
- 模型输出：新 `content_type` ID + 描述 + detect_pattern + transform 参数
- 自动 append 到 `content_type_rules.json`，下次运行生效

---

## 6. transform_node 转化策略

| strategy | 行为 |
|---|---|
| `split_rows` | 表格按行拆分，每行保留表头上下文，各自生成独立 segment |
| `preserve_as_is` | 原样保留，不做任何处理 |
| `preserve_as_list` | 列表项保留编号结构，拼接为连续文本 |
| `plain_embed` | 直接作为文本内容，去除多余空白 |

`transform_node` 处理完一个 `RawChunk` 的所有 `TypedSegment` 后，将结果合并为一个 `DocumentChunk`，其中 `content_summary` 为所有 segment 转化后文本的拼接，用于向量化。

---

## 7. 对外接口

```python
async def run_parser_workflow(
    md_content: str,
    doc_metadata: dict,         # 至少包含 standard_no, title
    rules_dir: str,             # content_type_rules.json 和 doc_type_rules.json 所在目录
    config: ParserConfig,       # CHUNK_SOFT_MAX, CHUNK_HARD_MAX, LLM 配置等
) -> ParserResult:
    ...

class ParserResult(TypedDict):
    chunks: List[DocumentChunk]
    doc_metadata: dict          # 含推断出的 doc_type
    errors: List[str]           # 非阻塞警告
    stats: dict                 # chunk_count, escalate_count, new_rules_added 等
```

---

## 8. 扩展原则

- **新 content_type**：向 `content_type_rules.json` append 一条 entry，无需修改代码
- **新 doc_type**：向 `doc_type_rules.json` append 一条 entry，无需修改代码
- **新 transform strategy**：在 `transform_node` 中注册新的 strategy 函数，JSON 中通过 `"strategy"` 字段引用
- **切片参数**：通过 `ParserConfig` 调整，无需修改 Workflow 节点逻辑
