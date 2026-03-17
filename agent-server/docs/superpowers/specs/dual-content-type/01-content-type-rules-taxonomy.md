# Spec 01：content_type_rules.json 分类体系重写

## 问题现象

运行 classify_node 处理 GB 标准文档后，所有 segment 的 `content_type` 均落入以下 6 个值之一：

```
plain_text | numbered_list | table | formula | standard_header | preface
```

其中 `plain_text` 覆盖了"1 范围"、"A.1 一般规定"、"分析步骤"、"结果计算"等完全不同用途的章节；`numbered_list` 覆盖了"试剂和材料"、"仪器和设备"、"分析步骤"、"参考色谱条件"等语义迥异的内容。下游 RAG 无法通过 `content_type` 区分这些章节。

## 根因

`content_type_rules.json` 的 `content_types` 数组只定义了 6 个类型，这 6 个类型是按**呈现形式**设计的（段落、列表、表格…），没有**语义维度**。两个维度混在一个字段里，导致：

- 呈现形式相同但用途不同的内容（如"试剂清单"和"操作步骤"都是列表）被归为同一类型
- 呈现形式不同但用途相同的内容（如含公式的"结果计算"节和不含公式的"分析步骤"节）被归为不同类型

## 发现方式

1. 运行完整 parser_workflow 测试并查看 JSONL artifacts：

```bash
pytest tests/core/parser_workflow/test_workflow.py -v -s
```

2. 统计 classify_node 输出中各 content_type 的分布，与文档章节结构对比：

```python
# 所有语义不同的章节最终落入的类型只有 6 个
# "试剂和材料"和"分析步骤"的 content_type 值相同：numbered_list
```

3. 查看规则文件：

```
agent-server/app/core/parser_workflow/rules/content_type_rules.json
```

只有 6 条 `content_types` 条目，无 examples，无 GB 标准特定描述。

## 方案

将 `content_type_rules.json` 从单数组结构改为**双数组结构**，分别定义结构类型和语义类型：

### structure_types（5种，描述呈现形式）

| id | 描述 | examples |
|---|---|---|
| `paragraph` | 叙述性段落 | "本标准适用于..."、"本方法按照..." |
| `list` | 编号或条目列表 | "A.3.1.1 异丙醇溶液：60%"、"——增加了酸不溶物" |
| `table` | 表格数据（HTML 或 Markdown） | "表1 感官要求"、"表2 理化指标" |
| `formula` | 数学或化学公式（含 LaTeX） | `$$w_1 = \frac{...}{m} \times 100\%$$` |
| `header` | 纯章节标题，无实质内容 | `## 2 技术要求`（后无内容） |

### semantic_types（8种，描述用途）

| id | 用户会怎么查 | examples |
|---|---|---|
| `metadata` | 这是哪个标准、何时发布 | "GB 1886.169—2016"、"2016-08-31 发布" |
| `scope` | 这个标准适用于什么 | "1 范围"、"本标准适用于以红藻类植物为原料..." |
| `limit` | 某指标的限量或要求值 | "感官要求"、"理化指标"、"铅(Pb) ≤ 5.0 mg/kg" |
| `procedure` | 怎么操作或测定 | "A.3.3 分析步骤"、"称取试样...置于..." |
| `material` | 需要哪些试剂或仪器 | "A.3.1 试剂和材料"、"A.3.2 仪器和设备" |
| `calculation` | 结果怎么计算 | "A.3.4 结果计算"、"式中 m1——坩埚加残渣质量" |
| `definition` | 某术语或概念的含义 | "术语和定义"、"卡拉胶是指..." |
| `amendment` | 该标准历史上改过什么 | "第1号修改单"、"将'...'修改为'...'" |

### transform 策略索引改为按 semantic_type 查找

```json
{
  "confidence_threshold": 0.7,
  "structure_types": [...],
  "semantic_types": [...],
  "transform": {
    "by_semantic_type": {
      "metadata":    { "strategy": "plain_embed", "prompt_template": "..." },
      "scope":       { "strategy": "plain_embed", "prompt_template": "..." },
      "limit":       { "strategy": "table_to_text", "prompt_template": "..." },
      "procedure":   { "strategy": "plain_embed", "prompt_template": "..." },
      "material":    { "strategy": "plain_embed", "prompt_template": "..." },
      "calculation": { "strategy": "formula_embed", "prompt_template": "..." },
      "definition":  { "strategy": "plain_embed", "prompt_template": "..." },
      "amendment":   { "strategy": "plain_embed", "prompt_template": "..." }
    }
  }
}
```

旧的 `content_types` 数组及各条目内嵌的 `transform` 字段一并移除。

## 受影响文件

- `app/core/parser_workflow/rules/content_type_rules.json`（直接修改）
- 该文件的下游读取方见 Spec 06（RulesStore）
