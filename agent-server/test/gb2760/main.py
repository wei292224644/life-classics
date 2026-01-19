"""
根据页数范围分割PDF文件
输入格式：[{"pages": [1, 2]}, {"pages": [3]}]
每个配置项必须包含：
- pages: 页数范围，可以是单个数字 [1] 或范围 [1, 2]
可选配置项：
- split: 布尔值，如果为True且pages是范围，则将范围拆分成多个单页处理（默认False）

注意：prompt 现在通过 AI 自动生成，无需手动配置
"""

import json
import logging
import pymupdf.layout  # 必须先导入这个来激活布局功能
import pymupdf  # PyMuPDF
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Set, Dict, Any

# 添加项目根目录到路径，以便导入app模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import chat


# ==================== 提示词模式定义 ====================
# region markdown
MARKDOWN_PROMPT = """你是一名资深的【文档解析与知识工程专家】，
擅长将标准类 PDF 文档转化为可直接用于知识库（RAG / Agent / 推理系统）的结构化文本。

你将收到一份 PDF 文档内容，请严格按照以下规则解析并输出结果。

输入数据格式为 列表数组，每个元素表示一个文本片段：

(x0, y0, x1, y1, text, line_id, block_id)

其中：

x0, y0, x1, y1：页面坐标（左上 → 右下）

====================
【一、核心目标】
====================
1. 完整提取 PDF 中出现的所有信息，不得遗漏正文、公式、表格、注释、脚注、说明、条件限制等内容。
2. 不追求版式复刻，但必须保证语义完整、逻辑清晰、结构稳定。
3. 输出结果必须“可直接切 chunk 入库”，无需人工二次清洗。

====================
【二、绝对禁止事项（高优先级）】
====================
1. 禁止对任何数值、单位、公式进行修改、推导、估算或重新计算。
2. 禁止合并、简化或省略变量定义、符号说明或注释内容。
3. 禁止引入 PDF 中未出现的背景知识、解释或结论。
4. 禁止使用“约”“大致”“通常”等模糊表述。

====================
【三、文档结构规范（强制）】
====================
1. 严格按以下层级组织内容：
   - 文档标题
   - 一级章节（##）
   - 二级章节（###）
   - 三级章节（####，如存在）
2. 每一个最小语义单元必须可作为一个独立 chunk 使用。
3. 不使用“如上所述”“见下表”等依赖版面的指代。

====================
【四、content_type 语义标注（必须使用）】
====================
每一个可切分的最小内容块，必须在标题下一行显式标注 content_type：

[content_type: <type>]

允许使用的 content_type 如下（只能从此列表中选择）：

- metadata                文档元信息（标准号、适用对象等）
- scope                   适用范围
- definition              概念 / 常数 / 术语定义
- chemical_formula        分子式
- chemical_structure      结构式说明
- molecular_weight        相对分子质量
- specification_table     技术指标 / 限量表格
- specification_text      技术要求（非表格）
- test_method             检验 / 测定方法
- instrument              仪器设备
- reagent                 试剂与材料
- calculation_formula     计算公式
- chromatographic_method  色谱 / 光谱类方法
- identification_test     鉴别试验
- general_rule            一般规定
- note                    注释 / 说明


====================
【五、数学公式处理规则】
====================
1. 所有公式必须使用 Markdown 数学公式格式（$$ ... $$）。
2. 公式后必须紧跟“变量解释区”，逐一列出：
   - 符号
   - 含义
   - 单位（如有）
3. 若公式中出现常数，必须说明其物理或化学含义及来源。
4. 若公式中出现公式（或计算式）的符号说明 / 参数定义（Symbol definitions / Where clause），必须用一个[__calculation_formula_note__]的标记替换类似“其中：”、“其中”、”注：”等字样。
5. 变量解释区不要被识别成其他的 content_type，应该添加[__calculation_formula_note__]标识。


====================
【六、表格处理规则】
====================
1. 表格必须作为一个完整的语义块，不得拆分为多段。
2. 使用标准 Markdown 表格格式。
3. 保留表头、单位、数值、注释、来源说明。
4. 表格下方如存在“注”“说明”“备注”，必须单独保留。
6. 如表格中出现“同上”“同下”“同前”等指代性内容：
   - 必须将其替换为所指向行的完整原文内容
   - 替换后不得保留“同上”等字样
示例：
原文：
| 项目 | 要求 | 检验方法 |  
| 色泽 | 无色 | 取适量样品置于清洁、干燥的白瓷盘中，在自然光线下，观察其色泽和状态，并嗅其味 |  
| 气味 | 无味 | 同上 |  

输出：
| 项目 | 要求 | 检验方法 |  
| 色泽 | 无色 | 取适量样品置于清洁、干燥的白瓷盘中，在自然光线下，观察其色泽和状态，并嗅其味 |  
| 气味 | 无味 | 取适量样品置于清洁、干燥的白瓷盘中，在自然光线下，观察其色泽和状态，并嗅其味 |  

====================
【七、 Metadata 处理规则】
====================
1. 采用无序列表格式。
2. 采用自然语言描述，不要使用表格格式。
3. 必须使用 [content_type: metadata] 标记。
示例：
[content_type: metadata]
- 本标准的标准号为 GB 28302—2012
- 本标准的中文名称为食品安全国家标准 食品添加剂 辛,癸酸甘油酯
- 本标准的发布日期为 2012-04-25
- 本标准的实施日期为 2012-06-25
- 本标准的发布机构为中华人民共和国卫生部


====================
【八、输出格式要求】
====================
1. 使用 Markdown 作为最终输出格式。
2. 仅输出解析后的结构化内容，不输出解析过程、思考说明或免责声明。
3. 不添加总结、评价或推论性内容。"""
# endregion

# region dsl

# DSL_SYSTEM_PROMPT = """你是一个国家食品安全标准的结构化解析引擎。

# 你的任务是：
# 将来自 PDF 版式解析结果（基于坐标的文本数组）的内容，
# 严格、逐字地映射为调用方提供的领域专用 DSL 结构。

# 输入数据由若干文本片段组成，每个片段格式为：
# (x0, y0, x1, y1, text, line_id, block_id)

# 解析与行为规则（必须严格遵守）：

# 1. 你必须基于页面坐标顺序恢复真实阅读顺序与表格行结构，
#    不得假设 line_id 或 block_id 是正确的。

# 2. 你只能输出调用方在 schema_definition 中明确声明的结构与字段：
#    - 不生成 schema 未声明的字段
#    - 不生成 schema 未声明的结构
#    - 不生成 schema 未声明的嵌套关系

# 3. 所有字段值必须逐字来源于原文文本：
#    - 不允许编造、补全、推测
#    - 不允许语义推导或常识补充
#    - 不允许合并未明确声明可合并的行或字段

# 4. 如果某字段在原文中不存在，必须使用 null；
#    如果整体内容与 schema_definition 不匹配，必须输出 EMPTY。

# 5. 你不得输出任何解释性、总结性或评论性文本，
#    不得输出自然语言说明。

# 6. 你必须只输出 DSL 结构本身：
#    - 不要 Markdown
#    - 不要 JSON
#    - 不要代码块
#    - 不要多余空行

# 7. 除非 schema_definition 明确允许，否则：
#    - 不得跨表推导关系
#    - 不得展开被引用内容
#    - 不得建立隐含引用

# 你的输出必须是一个确定性的、可被程序校验的 DSL 结果。
# """
DSL_SYSTEM_PROMPT = """你是一个国家食品安全标准的结构化解析引擎。

你的唯一任务是：
将来自 PDF 版式解析结果（基于坐标的文本数组）的内容，严格、逐字地映射为调用方提供的 SchemaIR 所定义的领域专用 DSL 结构。

一、输入数据说明

输入由若干文本片段组成，每个片段格式为：

(x0, y0, x1, y1, text, line_id, block_id)

其中：

* 坐标用于恢复真实阅读顺序与表格结构
* line_id、block_id 仅供参考，不具备权威性

二、Schema 约束（最高优先级）

你只能使用 SchemaIR 中明确声明的实体与字段。

允许的实体：

* RegulatoryStandard
* TableReference
* TableStructure
* FlavoringSubstance

严格禁止：

* 生成 Schema 未声明的实体
* 生成 Schema 未声明的字段
* 生成 Schema 未声明的嵌套关系
* 改写字段名、合并字段、拆分字段

SchemaIR 是唯一合法的结构边界。

三、解析与映射规则（必须全部遵守）

1. 阅读顺序与表格恢复

* 必须仅基于页面坐标恢复真实阅读顺序
* 必须基于坐标对齐恢复表头与数据行
* 不得假设 line_id 或 block_id 是正确的
* 不得跨页、跨表推导结构关系，除非 Schema 明确允许

2. 字段填充规则（逐字映射）

* 所有字段值必须逐字来源于原文 text，但应将原文中的换行符 \n 删除，内容连续性保持不变。
* 不允许编造、补全、推测、语义归纳或常识推导
* 不允许合并未在 Schema 中明确允许合并的多行文本

3. 缺失与不匹配处理

* 若某字段在原文中完全不存在，必须填 null
* 若整体内容无法与 SchemaIR 匹配，必须输出 EMPTY
* 不得为了“看起来完整”而强行构造结构

四、输出规则（强制）

* 你只能输出 DSL 结构本身
* 严禁输出 Markdown、JSON、代码块、注释或任何解释性、总结性自然语言
* 输出必须是确定性的、可被程序校验的、严格符合 SchemaIR 的 DSL(Domain Specific Language) 结果
* 不得输出任何解释性、总结性或评论性文本，不得输出自然语言说明。
* 输出必须是确定性的、可被程序校验的 JSON

五、失败即 EMPTY

只要出现以下任一情况，必须输出 EMPTY：

* Schema 无法匹配
* 表格结构无法确定
* 字段来源不明确

你不是解释器，不是总结器，不是知识补全模型。
你是一个严格的、零推理容错的法规结构映射引擎。"""


def clean_page_header_footer(text: str) -> str:
    """
    清理页头和页尾内容
    - 页头：GB 2760-2024 或 GB2760—2024（可能有空格和不同格式）
    - 页尾：数字或罗马数字（Ⅰ、Ⅱ、Ⅲ、Ⅳ、Ⅴ等）

    Args:
        text: 原始文本

    Returns:
        清理后的文本
    """
    if not text:
        return text

    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        # 去除页头：GB 2760-2024 或 GB2760—2024 的各种格式
        # 匹配：GB 2760-2024, GB2760-2024, GB 2760—2024, GB2760—2024 等
        if re.match(r"^\s*GB\s*2760[—\-]\s*2024\s*$", line.strip()):
            continue

        # 去除页尾：单独一行的数字或罗马数字
        # 匹配：纯数字（如 1, 2, 3）或罗马数字（Ⅰ、Ⅱ、Ⅲ、Ⅳ、Ⅴ、Ⅵ、Ⅶ、Ⅷ、Ⅸ、Ⅹ等）
        line_stripped = line.strip()
        if re.match(r"^[0-9]+$", line_stripped):  # 纯数字
            continue
        if re.match(r"^[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+$", line_stripped):  # 罗马数字
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def extract_text_with_layout(page: pymupdf.Page) -> str:
    """
    使用PyMuPDF的layout功能提取文本，保留布局信息

    Args:
        page: PyMuPDF页面对象

    Returns:
        提取的文本内容，保留布局结构
    """
    list = page.get_text_blocks() or ""
    res = json.dumps(list, ensure_ascii=False)
    return res


def extract_pages_text(
    pdf_path: str, page_ranges: List[Tuple[int, int, bool]]
) -> List[str]:
    """
    从PDF中提取指定页数范围的文本

    Args:
        pdf_path: PDF文件路径
        page_ranges: 页数范围列表，每个元素为(start_page, end_page, is_split)元组

    Returns:
        文本内容列表，每个元素对应一个页数范围的文本
    """
    texts = []

    # 使用PyMuPDF打开PDF（已导入pymupdf.layout激活布局功能）
    doc = pymupdf.open(pdf_path)
    try:
        total_pages = len(doc)
        print(f"PDF总页数: {total_pages}")

        for start_page, end_page, _ in page_ranges:
            # 验证页数范围
            if start_page < 1 or end_page > total_pages:
                print(
                    f"警告: 页数范围 [{start_page}, {end_page}] 超出PDF总页数 {total_pages}"
                )
                texts.append("")
                continue

            if start_page > end_page:
                print(f"警告: 起始页 {start_page} 大于结束页 {end_page}，跳过")
                texts.append("")
                continue

            # 提取指定页面的文本（使用layout功能）
            page_texts = []
            for page_num in range(start_page, end_page + 1):
                page = doc[page_num - 1]  # PyMuPDF的索引从0开始
                # 使用layout功能提取文本
                text = extract_text_with_layout(page) or ""
                if text:
                    # 清理页头和页尾
                    cleaned_text = clean_page_header_footer(text)
                    page_texts.append(cleaned_text)

            combined_text = "\n".join(page_texts)
            texts.append(combined_text)
            print(
                f"✓ 已提取第 {start_page}-{end_page} 页，共 {end_page - start_page + 1} 页，字符数量: {len(combined_text)}"
            )
    finally:
        doc.close()

    return texts


def parse_page_range_config(
    page_ranges: List[Dict[str, Any]],
) -> List[Tuple[int, int, bool]]:
    """
    解析页数范围配置

    Args:
        page_ranges: 页数范围列表，格式为：
            [
                {"pages": [1, 2]},
                {"pages": [3]},
                {"pages": [8, 148], "split": True}  # split为True时拆分成单页
            ]

    Returns:
        解析后的配置列表，每个元素为 (start_page, end_page, is_split) 元组
        is_split: 表示该配置是否来自 split=True 的拆分
        如果配置项设置了 split=True，范围会被拆分成多个单页配置
    """
    parsed_configs = []

    for range_item in page_ranges:
        if not isinstance(range_item, dict):
            print(f"警告: 配置项必须是字典格式: {range_item}，跳过")
            continue

        pages = range_item.get("pages", [])
        if not pages:
            print(f"警告: 配置项缺少 'pages' 字段: {range_item}，跳过")
            continue

        # 解析页数范围
        if len(pages) == 1:
            start_page, end_page = pages[0], pages[0]
        elif len(pages) == 2:
            start_page, end_page = pages[0], pages[1]
        else:
            print(f"警告: 无效的页数范围 {pages}，跳过")
            continue

        # 检查是否需要拆分（split选项）
        split = range_item.get("split", False)
        if split and start_page != end_page:
            # 将范围拆分成多个单页配置
            for page_num in range(start_page, end_page + 1):
                parsed_configs.append((page_num, page_num, True))
            print(
                f"  ✓ 配置: 页数 [{start_page}, {end_page}] 拆分为 {end_page - start_page + 1} 个单页"
            )
        else:
            parsed_configs.append((start_page, end_page, False))
            print(f"  ✓ 配置: 页数 [{start_page}, {end_page}]")

    return parsed_configs


def check_overlapping_pages(
    page_ranges: List[Tuple[int, int, bool]],
) -> List[Set[int]]:
    """
    检查页数范围是否有重叠

    Args:
        page_ranges: 页数范围列表，每个元素为 (start_page, end_page, is_split) 元组
    Returns:
        重叠页面的集合列表，每个集合包含重叠的页面编号
    """
    overlapping_pages = []

    # 收集所有页面
    all_pages = {}
    for idx, (start, end, _) in enumerate(page_ranges):
        for page in range(start, end + 1):
            if page not in all_pages:
                all_pages[page] = []
            all_pages[page].append(idx)

    # 找出重复的页面
    for page, indices in all_pages.items():
        if len(indices) > 1:
            overlapping_pages.append({page})

    return overlapping_pages


def detect_content_type(text: str) -> str:
    """
    检测内容是文本还是表格，如果是表格则直接生成并返回 schemaIR
    在一次 AI 调用中完成类型检测和 schemaIR 生成（如果是表格）

    Args:
        text: 原始文本内容

    Returns:
        content_type: "text" 或 "table"
    """
    if not text or not text.strip():
        return "text"

    # 取前1000字符用于检测和生成 schemaIR
    text_sample = text[:1000]

    system_prompt = """你是一个“食品安全国家标准表结构分析器”。

你的唯一任务是：
判断输入内容是【连续文本】还是【结构化表格】。

你不负责解析具体数据，
不生成任何 ADD_ADDITIVE、usage 或 EXCEPTION_CATEGORY 实例，
只描述“这张表应该如何被解析”。

---

【输入】

输入内容来自 PDF 版式解析结果，形式为文本片段集合，
每个片段包含坐标与文本信息，例如：

(x0, y0, x1, y1, text, line_id, block_id)

坐标仅用于判断阅读顺序与是否构成表格结构，
不得推测缺失内容。

---

【判断规则】

1. 如果内容不具备稳定的行列结构，仅为说明性或连续性文字：
   - 直接输出字符串：
     "text"

2. 如果内容呈现明确的表格结构（存在表头、行对应关系、重复列语义）：
   - 输出字符串：
     "table"
---

【输出规则】

- 如果判断为文本：
  只输出字符串：
  "text"

- 如果判断为表格：
  只输出字符串：
  "table"
"""

    human_prompt = f"""请分析以下内容，判断是文本还是表格：
<<<
{text_sample}
>>>
"""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]
        result = chat(
            messages,
            provider_name="dashscope",
            provider_config={
                "model": "qwen-flash",
                "temperature": 0.1,
                "reasoning": False,
            },
        )
        result = result.strip()

        # 判断返回结果
        result_lower = result.lower()
        if "text" in result_lower and len(result) < 10:
            # 纯文本响应
            return "text"
        else:
            return "table"

    except Exception as e:
        print(f"⚠️  内容类型检测失败: {e}，默认按文本处理")
        return "text"


def generate_schema_ir(text: str) -> str:
    """
    如果检测到是表格，生成 schemaIR 来描述表格结构

    Args:
        text: 原始文本内容（表格）

    Returns:
        schemaIR 字符串
    """
    schema_generation_prompt = """你是一名“结构化信息建模专家（Schema Designer）”。

我将提供一组来自中国食品安全法规（如 GB 2760）的 OCR 坐标文本数据。
这些数据是非结构化的，包含标题、表格、字段名、数据行和注释。

你的任务不是整理具体数据，
而是【仅根据这份数据本身】，抽象并生成一份 SchemaIR 结构定义。

━━━━━━━━━━━━━━━━━━
【你的目标】

1. 识别文档中隐含的“核心实体”（如：标准、表格、食品添加剂、使用规则）
2. 推导这些实体之间的层级关系
3. 为每个实体设计字段（字段名 + 含义）
4. 判断哪些字段是：
   - 单值 / 多值
   - 可为空 / 必填
   - 子结构 / 数组
5. 输出一个通用、可复用的 SchemaIR，
   使其可以用于解析同一法规中其他表格或页面

━━━━━━━━━━━━━━━━━━
【SchemaIR 输出要求】

- 使用 JSON 表达 Schema 结构（不是数据实例）
- 字段值类型使用以下占位形式：
  - string
  - number
  - boolean
  - string | null
  - object
  - array
- 不允许引入 OCR 数据中未体现的概念
- 不允许绑定某一个具体添加剂或食品
- 结构应具备“法规级长期复用性”

━━━━━━━━━━━━━━━━━━
【Schema 抽象规则（非常重要）】

1. 表格标题、标准编号 → 应提升为高层结构
2. 重复出现的“食品添加剂名称 + 编号 + 功能” → 独立实体
3. 表头（如“食品分类号 / 食品名称 / 最大使用量 / 备注”）
   → 必须转化为子结构 schema
4. 同一添加剂下出现多行食品分类
   → 推导为 array 结构
5. “功能”若出现并列词语
   → 必须设计为数组字段
6. 表下注释（如 1)、2)）
   → 设计为可扩展说明字段，而不是硬编码字段

━━━━━━━━━━━━━━━━━━
【输出格式（仅此一种）】

{
  "SchemaIR": {
    "entities": [
      {
        "name": "EntityName",
        "description": "该实体在法规中的语义角色",
        "fields": [
          {
            "field": "field_name",
            "type": "string | array | object | string | null",
            "description": "字段含义"
          }
        ]
      }
    ]
  }
}
"""

    human_prompt = f"""
━━━━━━━━━━━━━━━━━━
【OCR 原始数据如下】
━━━━━━━━━━━━━━━━━━
<<<
{text}
>>>
"""

    try:
        messages = [
            SystemMessage(content=schema_generation_prompt),
            HumanMessage(content=human_prompt),
        ]
        schema_ir = chat(
            messages,
            provider_name="dashscope",
            provider_config={"model": "qwen-flash", "temperature": 0.1},
        )
        return schema_ir.strip()
    except Exception as e:
        print(f"⚠️  SchemaIR 生成失败: {e}")
        return ""


def convert_txt_to_markdown(
    text: str, content_type: str = None, schema_prompt: str = None
) -> str:
    """
    使用LLM将txt文本转换为markdown格式
    首先检测内容是文本还是表格，然后通过AI自动生成相应的prompt进行处理

    Args:
        text: 原始文本内容
        content_type: 可选，预检测的内容类型（"text" 或 "table"），如果提供则跳过检测
        schema_prompt: 可选，预生成的 schema prompt，如果提供则跳过生成

    Returns:
        转换后的markdown格式文本
    """
    if not text or not text.strip():
        return text

    # 步骤1: 检测内容类型（如果未提供）
    if content_type is None:
        print("  🔍 正在检测内容类型...")
        content_type = detect_content_type(text)
        print(f"  ✓ 检测结果: {content_type}")
    else:
        print(f"  ✓ 使用缓存的 content_type: {content_type}")

    try:
        if content_type == "text":
            # 如果是文本，直接使用 MARKDOWN_PROMPT 转换
            print("  📝 使用 Markdown 模式转换...")
            human_prompt = f"""请按照要求转换：
<<<
{text}
>>>
"""
            conversion_messages = [
                SystemMessage(content=MARKDOWN_PROMPT),
                HumanMessage(content=human_prompt),
            ]
            markdown_text = chat(
                conversion_messages,
                provider_name="dashscope",
                provider_config={"model": "qwen-flash", "temperature": 0.1},
            )
            return markdown_text.strip()

        else:  # content_type == "table"
            # 生成 schema prompt（如果未提供）
            if schema_prompt is None:
                print("  🔧 生成 schemaIR...")
                schema_prompt = generate_schema_ir(text)
                schema_prompt = (
                    "以下是表格的schemaIR，请按照要求转换：\n" + schema_prompt
                )
            else:
                print("  ✓ 使用缓存的 schema prompt")

            print("  ✅ 使用生成的 schema prompt 进行转换...")
            human_prompt = f"""请按照要求转换：
<<<
{text}
>>>
"""
            dsl_messages = [
                SystemMessage(content=DSL_SYSTEM_PROMPT),
                HumanMessage(content=schema_prompt),
                HumanMessage(content=human_prompt),
            ]
            dsl_text = chat(
                dsl_messages,
                provider_name="dashscope",
                provider_config={"model": "qwen-flash", "temperature": 0.1},
            )
            return dsl_text.strip()
    except Exception as e:
        print(f"⚠️  LLM转换失败: {e}")
        print("   将使用原始文本作为Markdown内容")
        return text


def split_pdf_by_page_ranges(
    pdf_path: str,
    page_ranges: list[dict[str, Any]],
    output_dir: str = "chunks",
):
    """
    根据页数范围分割PDF文件

    Args:
        pdf_path: PDF文件路径
        page_ranges: 页数范围列表，格式为：
            [
                {"pages": [1, 2]},
                {"pages": [3]},
                {"pages": [3, 100], "split": True}
            ]
        output_dir: 输出目录

    注意：prompt 现在通过 AI 自动生成，无需手动配置
    """
    print("\n📋 解析配置...")
    # 解析配置，获取页数范围
    parsed_configs = parse_page_range_config(page_ranges)

    if not parsed_configs:
        print("错误: 没有有效的页数范围配置")
        return

    # 提取页数范围用于检查重叠
    # 检查重叠页面
    overlapping = check_overlapping_pages(parsed_configs)
    if overlapping:
        overlapping_pages = set()
        for overlap_set in overlapping:
            overlapping_pages.update(overlap_set)
        print(f"\n⚠️  检测到页面重叠: {sorted(overlapping_pages)}")
        print("   这些页面会出现在多个块中，将在文件中标记TODO\n")

    # 提取文本
    print("\n📄 提取文本...")
    texts = extract_pages_text(pdf_path, parsed_configs)

    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 创建统一的日志文件
    log_filepath = output_path / "processing.log"
    logger = logging.getLogger("pdf_processing")
    logger.setLevel(logging.INFO)
    logger.handlers = []  # 清除已有处理器

    # 创建文件处理器
    file_handler = logging.FileHandler(log_filepath, encoding="utf-8", mode="w")
    file_handler.setLevel(logging.INFO)

    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 记录处理开始
    logger.info("=" * 80)
    logger.info("开始处理 PDF 分割任务")
    logger.info(f"输出目录: {output_path}")
    logger.info(f"共 {len(parsed_configs)} 个配置项")
    logger.info("=" * 80)

    # 保存每个块
    print("\n💾 转换并保存文件...")

    # 缓存用于 split=True 的情况
    cached_content_type = None
    cached_schema_prompt = None
    current_split_group_start_idx = None

    for idx, ((start_page, end_page, is_split), text) in enumerate(
        zip(parsed_configs, texts), 1
    ):
        # 生成文件名
        if start_page == end_page:
            filename = f"page_{start_page}.txt"
        else:
            filename = f"pages_{start_page}_{end_page}.txt"

        filepath = output_path / filename

        # 记录开始处理
        start_time = datetime.now()
        logger.info(f"开始处理第 {start_page}-{end_page} 页")
        logger.info(f"配置索引: {idx}/{len(parsed_configs)}")
        logger.info(f"是否 split: {is_split}")
        logger.info(f"原始文本字符数: {len(text):,}")

        # 检查是否有重叠页面
        overlapping_pages_in_range = []
        if overlapping:
            for page in range(start_page, end_page + 1):
                for overlap_set in overlapping:
                    if page in overlap_set:
                        overlapping_pages_in_range.append(page)
            if overlapping_pages_in_range:
                logger.warning(
                    f"检测到页面重叠: {sorted(set(overlapping_pages_in_range))}"
                )

        try:
            # with open(filepath, "w", encoding="utf-8") as f:
            #     f.write(text)
            # logger.info(f"已保存原始文本: {filepath}")

            # 转换为Markdown并保存
            md_filepath = filepath.with_suffix(".md")
            print(
                f"\n  [{idx}/{len(parsed_configs)}] 正在处理第 {start_page}-{end_page} 页..."
            )

            # 如果是 split=True 的情况，检测并缓存 content_type 和 schema_prompt
            use_cached_content_type = None
            use_cached_schema_prompt = None

            if is_split:
                # 检查是否是新的 split 组
                is_new_split_group = False
                if idx == 1:
                    # 第一个配置项，肯定是新组
                    is_new_split_group = True
                elif current_split_group_start_idx is None:
                    # 没有缓存，是新组
                    is_new_split_group = True
                else:
                    # 检查上一个配置项
                    prev_start, prev_end, prev_is_split = parsed_configs[idx - 2]
                    if not prev_is_split:
                        # 上一个不是 split，是新组
                        is_new_split_group = True
                    elif prev_end != start_page - 1:
                        # 页面不连续，是新组
                        is_new_split_group = True

                if is_new_split_group:
                    # 新的 split 组，检测第一页并缓存
                    logger.info(f"检测 split 组的第一页（第 {start_page} 页）...")
                    print(f"  🔍 检测 split 组的第一页（第 {start_page} 页）...")
                    cached_content_type = detect_content_type(text)
                    logger.info(f"内容类型检测结果: {cached_content_type}")
                    print(f"  ✓ 检测结果: {cached_content_type}")

                    if cached_content_type == "table":
                        logger.info("开始生成 schemaIR...")
                        print("  🔧 生成 schemaIR...")
                        cached_schema_prompt = generate_schema_ir(text)
                        cached_schema_prompt = (
                            "以下是表格的schemaIR，请按照要求转换：\n"
                            + cached_schema_prompt
                        )
                        logger.info(f"cached_schema_prompt: {cached_schema_prompt}")
                        logger.info(
                            f"schemaIR 生成完成，长度: {len(cached_schema_prompt):,} 字符"
                        )
                    else:
                        cached_schema_prompt = None
                        logger.info("内容类型为文本，无需生成 schemaIR")

                    current_split_group_start_idx = idx
                    use_cached_content_type = cached_content_type
                    use_cached_schema_prompt = cached_schema_prompt
                else:
                    # 复用缓存的 content_type 和 schema_prompt
                    logger.info(
                        f"复用 split 组的缓存（content_type: {cached_content_type}）"
                    )
                    print(
                        f"  ✓ 复用 split 组的缓存（content_type: {cached_content_type}）"
                    )
                    use_cached_content_type = cached_content_type
                    use_cached_schema_prompt = cached_schema_prompt
            else:
                logger.info("非 split 模式，将进行内容类型检测")

            logger.info("开始使用 LLM 转换为 Markdown...")
            print(f"  正在使用LLM转换为Markdown...")
            markdown_content = convert_txt_to_markdown(
                text,
                content_type=use_cached_content_type,
                schema_prompt=use_cached_schema_prompt,
            )
            logger.info(f"Markdown 转换完成，字符数: {len(markdown_content):,}")

            with open(md_filepath, "w", encoding="utf-8") as f:
                # 如果有重叠页面，添加TODO标记
                if overlapping_pages_in_range:
                    f.write(
                        f"⚠️  TODO: 以下页面在其他块中也出现: {sorted(set(overlapping_pages_in_range))}\n\n"
                    )

                f.write(markdown_content)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"已保存 Markdown 文件: {md_filepath}")
            logger.info(f"处理完成，耗时: {duration:.2f} 秒")
            print(f"  ✓ 已保存: {md_filepath} (字符数: {len(markdown_content):,})")

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"处理失败: {str(e)}", exc_info=True)
            logger.error(f"失败时耗时: {duration:.2f} 秒")
            print(f"  ❌ 处理失败: {e}")
            raise

    # 关闭日志处理器
    logger.info("=" * 80)
    logger.info(f"处理完成！共生成 {len(texts)} 个md文件")
    logger.info("=" * 80)
    file_handler.close()
    logger.removeHandler(file_handler)

    print(f"\n✅ 完成！共生成 {len(texts)} 个md文件")
    print(f"📝 日志文件: {log_filepath}")


if __name__ == "__main__":
    # 获取脚本所在目录
    script_dir = Path(__file__).parent

    # PDF文件路径（相对于脚本所在目录）
    pdf_path = script_dir / "GB2760-2024.pdf"

    # 检查文件是否存在
    if not pdf_path.exists():
        print(f"错误: 找不到PDF文件: {pdf_path}")
        exit(1)

    # 输出目录（相对于脚本所在目录）
    output_dir = script_dir / "chunks"

    # ==================== 配置示例 ====================

    # ==================== 当前配置 ====================
    # 请修改下面的 page_ranges 来指定要分割的页数范围
    # 注意：prompt 现在通过 AI 自动生成，无需手动配置
    page_ranges = [
        # {"pages": [4, 6]},
        # {"pages": [8, 10], "split": True},
        # {"pages": [149, 150], "split": True},
        {"pages": [220, 221], "split": True},
    ]

    split_pdf_by_page_ranges(str(pdf_path), page_ranges, str(output_dir))
