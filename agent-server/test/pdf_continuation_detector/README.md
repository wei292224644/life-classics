# PDF 跨页内容延续判定工具

## 项目简介

本项目用于判断 PDF 文档中跨页内容是否为上一页的延续。这对于 PDF 语义切分、文档解析等场景非常有用。

## 项目结构

```
pdf_continuation_detector/
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── models.py           # 数据结构定义（PageContext / Result）
│   ├── config.py           # 权重与阈值配置
│   ├── scorer.py           # 评分引擎（加权打分）
│   ├── rules.py            # 单条规则实现（纯规则函数）
│   └── detector.py         # 主入口：is_continuation
│
├── utils/                   # 工具模块
│   ├── __init__.py
│   ├── text_utils.py       # 文本/行处理工具
│   └── regex_patterns.py    # 国家标准专用正则
│
├── tests/                   # 测试模块
│   └── test_cases.py       # 单元测试（覆盖典型场景）
│
└── README.md
```

## 核心功能

### 1. 延续判定规则

项目实现了多种规则来判断内容是否延续：

- **句子延续**：判断上一页是否以未完成的句子结尾
- **词语延续**：判断词语是否被截断
- **段落延续**：判断段落是否未完成
- **表格延续**：判断表格是否跨页
- **列表延续**：判断列表是否跨页
- **章节中断**：判断是否开始新章节（负规则）
- **缩进匹配**：判断缩进是否一致
- **格式一致性**：判断格式是否一致

### 2. 评分机制

每个规则都会产生一个分数（0.0-1.0），然后根据配置的权重进行加权求和，最终得到总分。如果总分超过阈值且置信度足够，则判定为延续。

## 使用方法

### 基本使用

```python
from pdf_continuation_detector.core.detector import is_continuation

# 上一页文本
prev_page_text = "这是一个未完成的句子，需要"

# 下一页文本
next_page_text = "在下一页继续完成。"

# 判断是否为延续
result = is_continuation(prev_page_text, next_page_text)

# 查看结果
print(f"是否为延续: {result.is_continuation}")
print(f"置信度: {result.confidence}")
print(f"总分: {result.score}")
print(f"判定原因: {result.reasons}")
```

### 自定义配置

```python
from pdf_continuation_detector.core.detector import is_continuation
from pdf_continuation_detector.core.config import ContinuationConfig

# 创建自定义配置
config = ContinuationConfig(
    threshold=0.6,  # 提高阈值
    min_confidence=0.4,
    context_lines=10,  # 增加上下文行数
    rule_weights={
        "sentence_continuation": 0.3,  # 调整权重
        "table_continuation": 0.2,
        # ... 其他权重
    }
)

# 使用自定义配置
result = is_continuation(prev_page_text, next_page_text, config=config)
```

### 结果对象

`ContinuationResult` 对象包含以下属性：

- `is_continuation`: 布尔值，是否为延续
- `confidence`: 置信度（0.0-1.0）
- `score`: 总分
- `rule_scores`: 各规则得分详情（字典）
- `reasons`: 判定原因列表

## 配置说明

### 默认配置

```python
ContinuationConfig(
    rule_weights={
        "sentence_continuation": 0.25,
        "word_continuation": 0.15,
        "paragraph_continuation": 0.20,
        "table_continuation": 0.15,
        "list_continuation": 0.10,
        "section_break": -0.30,  # 负权重
        "indentation_match": 0.10,
        "format_consistency": 0.05,
    },
    threshold=0.5,
    min_confidence=0.3,
    context_lines=5,
    context_words=20,
)
```

### 参数说明

- `rule_weights`: 各规则的权重，权重越高越重要。负权重表示该规则倾向于判定为"不延续"
- `threshold`: 判定阈值，总分超过此值判定为延续
- `min_confidence`: 最小置信度，低于此值即使总分超过阈值也不判定为延续
- `context_lines`: 用于提取首尾行的上下文行数
- `context_words`: 用于提取首尾词的上下文词数

## 运行测试

```bash
# 运行所有测试
python -m pytest tests/test_cases.py

# 或使用 unittest
python -m unittest tests.test_cases
```

## 扩展开发

### 添加新规则

1. 在 `core/rules.py` 中添加新的规则函数：

```python
def rule_custom_rule(prev_page: PageContext, next_page: PageContext) -> Tuple[float, str]:
    """
    自定义规则
    
    Returns:
        (分数, 原因)
    """
    # 实现规则逻辑
    if some_condition:
        return 0.8, "原因说明"
    return 0.0, ""
```

2. 在 `core/scorer.py` 的 `rule_functions` 字典中注册新规则
3. 在 `core/config.py` 的默认权重中添加新规则的权重

### 调整规则权重

根据实际使用效果，可以调整 `config.py` 中各规则的权重，以获得更好的判定效果。

## 注意事项

1. 本工具主要针对中文文档（特别是国家标准类文档）进行了优化
2. 对于特殊格式的文档，可能需要调整规则权重或添加新规则
3. 判定结果仅供参考，建议结合人工审核

## 许可证

本项目为内部工具，仅供项目使用。

