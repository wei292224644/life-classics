## 知识库架构设计

### 知识库通用数据结构

```json
{
  "chunk_id": "chunk_id", // Required
  "doc_id": "doc_id", // Required
  "doc_title": "doc_title", // Optional
  "section_path": ["section_path"], // Optional
  "content_type": "content_type", // Optional
  "content": "content", // Required
  "meta": {} // Optional
}
```

### 知识库支持导入格式类型

- PDF
- Markdown
- JSON
- Text

### 知识库切分策略

- structured: 结构化切分，按照章节、小节、段落等结构进行切分。当导入 PDF 时，会通过 LLM 分析文档结构,再转化为 Markdown 格式，然后进行切分。`暂不支持 Text/JSON 格式文件`。
- text: 文本切分，按照段落、句子等文本单位进行切分。
- table: 表格切分，按照表格、行、列等表格单位进行切分。
- heading: 标题切分，按照标题、副标题等标题单位进行切分。
- parent_child: 父子切分，按照父子关系进行切分。

### 知识库导入流程

1. 用户上传文件
2. 用户选择切分策略，默认为：text
3. 系统根据切分策略对文件进行切分
4. 系统将切分后的内容转换为知识库通用数据结构
5. 系统将知识库通用数据结构存储到知识库中

### 知识库工程文件结构

```
kb/
├── imports/
│   ├── import_pdf.py
│   ├── import_markdown.py
│   ├── import_json.py
│   └── import_text.py
├── pre-parse/
│   ├── pdf_to_markdown.py
│   └── pdf_ocr.py
├── strategy/
│   ├── text_strategy.py
│   ├── table_strategy.py
│   ├── heading_strategy.py
│   ├── structured_strategy.py
|   └── parent_child_strategy.py
├── vector_store/
│   ├── vector_store.py
```

## Content Type 说明

知识库系统支持多种内容类型（content_type），用于对文档内容进行语义分类和结构化存储。以下是所有支持的内容类型及其含义：

### 文档元信息类

- **`metadata`**: 文档元信息，包括标准编号、标准名称、发布日期、适用对象等基本信息

### 适用范围类

- **`scope`**: 适用范围，描述标准或文档的适用对象、应用领域等

### 定义类

- **`definition`**: 概念、术语、常数定义，用于解释文档中使用的专业术语或常量

### 化学信息类

- **`chemical_formula`**: 分子式，化学物质的分子式表示（如 C₄₀H₅₆）
- **`chemical_structure`**: 结构式说明，包括"原文未给出结构图"的明确描述
- **`molecular_weight`**: 相对分子质量，化学物质的相对分子质量数值

### 技术规范类

- **`specification_table`**: 技术指标/限量/要求类表格，以结构化表格形式存储的技术规范
- **`specification_text`**: 技术要求，非表格形式的文字性规范要求

### 检验方法类

- **`test_method`**: 检验方法/测定步骤，流程性的检验操作描述
- **`identification_test`**: 鉴别试验，用于识别和验证物质的方法
- **`chromatographic_method`**: 色谱/光谱/顶空/UV-Vis 等仪器分析方法

### 实验条件类

- **`instrument`**: 仪器与设备，实验或检验所需的仪器设备说明
- **`reagent`**: 试剂与材料，实验或检验所需的试剂和材料清单

### 计算公式类

- **`calculation_formula`**: 计算公式，包含公式本体和变量定义的计算公式

### 规则说明类

- **`general_rule`**: 一般规定、通用规则，适用于整个文档或特定章节的通用规则
- **`note`**: 注释、说明、补充性文字，包括"注：……"形式的补充说明

### 使用说明

在 Markdown 文档中，使用以下格式标注 content_type：

```markdown
【content_type: scope】
本标准适用于...

【content_type: specification_table】
| 项目 | 要求 | 检验方法 |
|------|------|----------|
| 色泽 | 暗红色至棕红色 | ... |
```

或者使用 fenced block 格式：

````markdown
```specification_table
| 项目 | 要求 |
|------|------|
| ... | ... |
```
````

```

系统会根据 content_type 对内容进行结构化解析和存储，便于后续的语义检索和知识推理。

## 许可证

MIT License
```
