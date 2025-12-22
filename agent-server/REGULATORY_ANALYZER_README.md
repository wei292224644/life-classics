# 法规语义解析系统使用说明

## 概述

本系统实现了法规语义解析功能，能够从PDF文档中提取规范性规则（Normative Rules）和生成解释型问答（QA）。

## 核心模块

### 1. `regulatory_semantic_analyzer.py`
法规语义解析器，负责：
- 判断结构单元类型（rule/qa/ignore）
- 提取规范性规则的结构化信息
- 生成问答对

### 2. `pdf_structure_extractor.py`
PDF结构单元提取器，负责：
- 从PDF/Markdown中提取结构单元
- 识别表格行、句子、段落、注释等

### 3. `process_regulatory_document.py`
处理脚本，用于批量处理PDF文件

## 使用方法

### 处理单个PDF文件

```bash
python process_regulatory_document.py files/20120518_10.pdf
```

### 处理单个PDF文件并保存结果

```bash
python process_regulatory_document.py files/20120518_10.pdf results.json
```

### 处理整个目录

```bash
python process_regulatory_document.py files/ --output results.json
```

## 输出格式

### 规则（Rule）格式

```json
{
  "type": "rule",
  "rules": [
    {
      "document": "产品的总β-胡萝卜素含量不得低于96.0%。",
      "item": "total_beta_carotene_content",
      "limit_type": ">=",
      "limit_value": 96.0,
      "unit": "%",
      "condition": "",
      "standard_ref": "GB 28310-2012"
    }
  ]
}
```

### 问答（QA）格式

```json
{
  "type": "qa",
  "qas": [
    {
      "question": "商品化的β-胡萝卜素产品允许使用哪些原料？",
      "answer": "商品化的β-胡萝卜素产品应以符合本标准的β-胡萝卜素为原料，可添加食品级明胶、抗氧化剂、食用植物油、糊精或淀粉等载体。",
      "standard_ref": "GB 28310-2012"
    }
  ]
}
```

### 忽略（Ignore）格式

```json
{
  "type": "ignore"
}
```

## 设计原则

1. **规则边界判断**：由大模型根据法规语义判断，而不是通过文本结构判断
2. **最小单位**：chunk的最小单位必须是"一条可独立判断真伪的规范性规则"
3. **法规语义表达**：使用"不得低于"、"不得超过"、"应当"等法规语言，不使用≥≤等符号
4. **完整性**：每条规则必须完整、独立，不依赖上下文即可成立

## 示例

### 输入示例1
```
总β-胡萝卜素含量，w/% ≥ 96.0
```

### 输出示例1
```json
{
  "type": "rule",
  "rules": [
    {
      "document": "产品的总β-胡萝卜素含量不得低于96.0%。",
      "item": "total_beta_carotene_content",
      "limit_type": ">=",
      "limit_value": 96.0,
      "unit": "%",
      "condition": "",
      "standard_ref": "GB 28310-2012"
    }
  ]
}
```

### 输入示例2
```
注：商品化的β-胡萝卜素产品应以符合本标准的β-胡萝卜素为原料……
```

### 输出示例2
```json
{
  "type": "qa",
  "qas": [
    {
      "question": "商品化的β-胡萝卜素产品允许使用哪些原料？",
      "answer": "商品化的β-胡萝卜素产品应以符合本标准的β-胡萝卜素为原料，可添加食品级明胶、抗氧化剂、食用植物油、糊精或淀粉等载体。",
      "standard_ref": "GB 28310-2012"
    }
  ]
}
```

## 配置

系统使用项目中的LLM配置（`app/core/config.py`），默认使用Ollama。如需修改，请编辑配置文件或环境变量。

## 注意事项

1. 确保LLM服务（Ollama/DashScope/OpenRouter）已正确配置并运行
2. PDF文件需要能够被正确解析（支持OCR的图片型PDF）
3. 处理大量文件时可能需要较长时间，建议分批处理
