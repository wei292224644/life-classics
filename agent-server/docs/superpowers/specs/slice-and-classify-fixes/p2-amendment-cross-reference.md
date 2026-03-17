# Spec P2-02：修改单条目与原标准章节缺乏交叉引用

## 问题现象

第 1 号修改单（chunk[23]）被 slice_node 切分为一个独立 chunk（section_path 顶层为"GB 1886.169—2016…第 1 号修改单"），classify_node 将其分为 3 个 segment：

```
seg[0]: standard_header  — 修改单头部（批准日期、实施日期）
seg[1]: numbered_list    — 修改事项一（1 范围）
seg[2]: numbered_list    — 修改事项二（2.3 微生物指标）
```

其中 seg[1] 的内容是：
> 将"...产品为 K(Kappa)、I(Iota)、λ(Lambda) 三种基本型号的混合物"修改为"...卡拉胶中常见的多糖为..."

seg[2] 的内容是：
> 将表 3"大肠埃希氏菌 CFU/g"指标 `< 10` 修改为 `< 100`；将项目名称"沙门氏菌 (25g)"修改为"沙门氏菌 (1g)"

但这两个 segment 的 `cross_refs` 均为空数组 `[]`，`ref_context` 也为空：

```json
"cross_refs": [],
"ref_context": ""
```

这意味着：
1. 修改单中明确指向"1 范围"和"2.3 微生物指标"的引用没有被识别和记录
2. RAG 检索"1 范围"时无法知道该节已被修改单修订
3. 检索"大肠埃希氏菌限量"时返回的可能是原始值 `< 10`，而非修改后的 `< 100`

## 根因

**问题一：修改单内的章节引用未被 enrich_node 识别**

`enrich_node.py` 中的 `_OTHER_REF_PATTERN` 用于提取章节引用：

```python
# enrich_node.py 第 27-32 行
_OTHER_REF_PATTERN = re.compile(
    r'(?:见|参见|参照|按照?)\s*((?:图|附录)[^\s，。；]{0,15}'
    r'|第?\s*\d+[\.\d]*\s*[节章条]'
    r'|\d+\.\d+[\.\d]*)',
    re.UNICODE,
)
```

该正则只匹配"见/参见/参照/按照"等引导词后的引用。修改单中的引用形式是：

```
### 一、1 范围
将"..."修改为"..."
```

以及：

```
### 二、2.3 微生物指标
将表 3"..."修改为"..."
```

章节标题本身就是引用目标（"1 范围"、"2.3 微生物指标"），但没有"见/参见"等引导词，因此 `_OTHER_REF_PATTERN` 无法匹配。

**问题二：修改单格式与普通章节截然不同，当前无专门处理逻辑**

当前 enrich_node 仅处理两类引用：
- `见表X` → 内联表格内容到 `ref_context`
- `见图X / 附录X / 章节X` → 记录到 `cross_refs`

修改单的引用形式是**标题即引用目标**（`### 一、1 范围` 表示"针对原标准 1 范围节的修改"），这是一种结构性引用，不是文本内引用，现有机制无法处理。

## 发现方式

**第一步：** 查看修改单 chunk 的 classify_node 输出：

```bash
cat tests/artifacts/parser_workflow_updates_*.jsonl | python3 -c "
import json, sys
lines = sys.stdin.read().strip().split('\n')
obj = json.loads(lines[4])  # classify_node
chunk23 = obj['node_output']['classified_chunks'][23]
for seg in chunk23['segments']:
    print('cross_refs:', seg['cross_refs'])
    print('ref_context:', seg['ref_context'])
"
```

输出均为空。

**第二步：** 查看 `enrich_node.py` 第 21-32 行的两个正则，确认不匹配"### 一、1 范围"这类标题式引用。

**第三步：** 确认修改单章节格式（取自原始 Markdown）：

```markdown
## （修改事项）

### 一、1 范围
将"..."修改为"..."

### 二、2.3 微生物指标
将表 3"..."修改为"..."
```

引用目标（"1 范围"、"2.3 微生物指标"）嵌在子标题"### 一、1 范围"中，需要专门的解析逻辑。

## 方案

### 方案 A：在 enrich_node 中增加修改单专用引用提取（推荐）

新增函数 `extract_amendment_refs`，专门解析修改单中的"### 一/二/三、X.X 章节名"格式，提取被修改的章节编号，写入 `cross_refs`：

```python
# enrich_node.py 新增

_AMENDMENT_REF_PATTERN = re.compile(
    r'###\s+[一二三四五六七八九十]+、\s*(\d+(?:\.\d+)*)\s*',
    re.UNICODE,
)

def extract_amendment_refs(text: str) -> List[str]:
    """
    从修改单条目中提取被修改的章节编号。
    如 "### 一、1 范围" → ["1"]
       "### 二、2.3 微生物指标" → ["2.3"]
    """
    return [m.group(1) for m in _AMENDMENT_REF_PATTERN.finditer(text)]
```

在 enrich_node 主逻辑中，判断 segment 的 `content_type` 为 `amendment` 时（新体系），调用 `extract_amendment_refs` 并将结果写入 `cross_refs`。

### 方案 B：在 classify_node prompt 中要求 LLM 提取修改单引用

在 classify_node 处理修改单 segment 时，通过 prompt 要求 LLM 识别引用目标并输出到 `cross_refs` 字段。

**优点**：逻辑集中在 classify_node。
**缺点**：依赖 LLM 准确识别，稳定性不如正则；且修改 `SegmentItem` schema 增加 `cross_refs` 字段会影响 Spec 02。

**推荐方案 A**，正则可精确匹配修改单的固定格式，稳定性更高。

### 向量化时的补充处理

修改单 segment 的 `transform_params` 应使用专门的 prompt_template，明确要求 LLM 在转写时：
1. 标注这是一条修改记录
2. 包含被修改章节的引用标识

这样检索"2.3 微生物指标"时，修改单的内容也能被召回并提示用户注意修订。

## 依赖关系

- 前置：dual-content-type Spec 01（`semantic_type=amendment` 确定后，才能在 enrich_node 中按类型分支处理）
- 与 Spec 08（enrich_node 双字段适配）在同一文件修改，建议合并实施

## 受影响文件

- `app/core/parser_workflow/nodes/enrich_node.py`（新增 `extract_amendment_refs`，在主逻辑中调用）
- `app/core/parser_workflow/rules/content_type_rules.json`（`amendment` 类型的 `transform.prompt_template` 需专门设计）
