---
name: document-type
description: 判断某份标准文档属于哪一类（单添加剂/检测方法/微生物检验/产品/其他）。在用户询问文档类型、或需要按类型选择检索或解释策略时使用。
allowed-tools: ["knowledge_base"]
---

# 文档类型分类

## 概述

本技能用于对「国家标准」类文档做类型判断，便于后续编排：例如先判类型再决定用哪类检索策略，或直接回答「这份标准是什么类型」。

## 何时使用

- 用户明确问：「这份文档是什么类型」「属于哪类标准」「是添加剂标准还是检测方法」等。
- 需要按文档类型做差异化处理时：例如先对当前讨论的文档调用 `document_type`，再根据返回的 single_additive / detection_method / microbiological 等选择解释方式或推荐检索词。
- 对检索到的文档做二次归类说明时：可根据文件名或检索结果中的标题/目录摘要调用本工具，再在回答中说明类型。

## 使用步骤

1. **确定输入**：从用户问题或当前上下文取得「文档文件名或标准号」；若有目录/章节信息，可截取为 `heading_summary` 以提高准确率。
2. **调用 document_type 工具**：传入 `filename`（必填），可选传 `heading_summary`（章节或摘要文本）。
3. **解读与编排**：根据返回的类型标识（single_additive / detection_method / microbiological / product / other）回答用户或决定下一步（如选用 knowledge_base 的检索策略）。

## 类型含义

- **single_additive**：单添加剂/食品添加剂类标准（如某一种添加剂的质量规格与检验方法）。
- **detection_method**：检测/测定方法标准（如某成分的测定、液相色谱法等）。
- **microbiological**：微生物检验/流程类标准（如沙门氏菌检验、检验程序）。
- **product**：产品标准（如花粉、某类食品产品）。
- **other**：以上都不是。
