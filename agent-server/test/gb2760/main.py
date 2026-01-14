"""
根据页数范围分割PDF文件
输入格式：[{"pages": [1, 2], "messages": [SystemMessage(...)]}, {"pages": [3], "messages": [SystemMessage(...)]}]
每个配置项必须包含：
- pages: 页数范围，可以是单个数字 [1] 或范围 [1, 2]
- messages: 消息列表，包含 SystemMessage、HumanMessage 等
可选配置项：
- split: 布尔值，如果为True且pages是范围，则将范围拆分成多个单页处理（默认False）
"""

import json
import pymupdf.layout  # 必须先导入这个来激活布局功能
import pymupdf  # PyMuPDF
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set, Dict, Any

# 添加项目根目录到路径，以便导入app模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
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

DSL_SYSTEM_PROMPT = """你是一个国家食品安全标准的结构化解析引擎。

你的任务是：
将来自 PDF 版式解析结果（基于坐标的文本数组）的内容，
严格、逐字地映射为调用方提供的领域专用 DSL 结构。

输入数据由若干文本片段组成，每个片段格式为：
(x0, y0, x1, y1, text, line_id, block_id)

解析与行为规则（必须严格遵守）：

1. 你必须基于页面坐标顺序恢复真实阅读顺序与表格行结构，
   不得假设 line_id 或 block_id 是正确的。

2. 你只能输出调用方在 schema_definition 中明确声明的结构与字段：
   - 不生成 schema 未声明的字段
   - 不生成 schema 未声明的结构
   - 不生成 schema 未声明的嵌套关系

3. 所有字段值必须逐字来源于原文文本：
   - 不允许编造、补全、推测
   - 不允许语义推导或常识补充
   - 不允许合并未明确声明可合并的行或字段

4. 如果某字段在原文中不存在，必须使用 null；
   如果整体内容与 schema_definition 不匹配，必须输出 EMPTY。

5. 你不得输出任何解释性、总结性或评论性文本，
   不得输出自然语言说明。

6. 你必须只输出 DSL 结构本身：
   - 不要 Markdown
   - 不要 JSON
   - 不要代码块
   - 不要多余空行

7. 除非 schema_definition 明确允许，否则：
   - 不得跨表推导关系
   - 不得展开被引用内容
   - 不得建立隐含引用

你的输出必须是一个确定性的、可被程序校验的 DSL 结果。
"""
ADD_ADDITIVE_USAGE_SCHEMA = """SCHEMA_DEFINITION

SCHEMA_NAME: ADD_ADDITIVE_USAGE

DESCRIPTION:
本 schema 用于解析食品安全国家标准中
“食品添加剂使用规定”相关表格或条文，
输出食品添加剂在不同食品中的允许使用情况。

————————————————————
【外层结构规则】
————————————————————

当原文中存在明确的表格标题，且该标题在版式上作为一组添加剂条目的共同来源时，
允许使用 TABLE 作为最外层容器。

TABLE {
  id: string        // 原文中的表编号，如“表 A.1”
  title: string     // 原文表标题全文，不得改写
}

如果原文未出现明确表标题：
- 不生成 TABLE
- 直接输出 ADD_ADDITIVE

不允许嵌套 TABLE。

————————————————————
【TABLE.title 判定规则（重要）】
————————————————————

TABLE.title 仅在原文中存在“明确的表主题描述”时才赋值。

判定规则：
- 如果表标题文本中，除表编号外，还包含对表内容的描述性文字，
  则该描述性文字作为 title。
- 描述性文字必须逐字来源于原文，不得改写。

以下情况，TABLE.title 必须为 null：
- 标题仅包含表编号
- 标题包含“（续）”“（续表）”“continued”等续表标记
- 标题未提供新的表主题信息

示例（仅用于判定理解，不输出）：
- “表 A.2 表 A.1中例外食品编号对应的食品类别”
  → id = “表 A.2”
  → title = “表 A.1中例外食品编号对应的食品类别”

- “表 A.2（续）”
  → id = “表 A.2”
  → title = null

————————————————————
【核心记录结构】
————————————————————

ADD_ADDITIVE {
  name_zh: string                // 添加剂中文名称，来源于标题或条文
  name_en: string | null         // 英文名称（如原文存在）
  CNS: string[] | null           // CNS 号，允许多行合并
  INS: string[] | null           // INS 号，允许多行合并
  function: string[] | null      // 功能，可为多个

  usage {
    food_category: string        // 食品分类号
    food_name: string            // 食品名称
    max_amount: number | null    // 最大使用量
    unit: "g/kg" | null          // 单位，仅当原文出现
    rule: string | null          // 使用规则原文
    remark: string | null        // 备注
    reference_exclusion: reference_exclusion | null
  }
}

————————————————————
【usage 行生成规则】
————————————————————

- 表格中的每一行对应一个 usage
- “食品分类号” → food_category
- “食品名称” → food_name
- “最大使用量” → max_amount
- 单位统一为 g/kg（仅当原文出现）
- “备注” → remark

特殊规则：
- 原文为“按生产需要适量使用”：
  - max_amount = null
  - rule = 原文完整表述
- 相邻但不属于表格的说明性文字，不生成 usage

————————————————————
【特殊字段处理】
————————————————————

- CNS号、INS号可能分散在多行，需要合并为数组
- 功能字段如出现多个，用数组表示
- 中英文名称分别识别，不得混合
- 添加剂标题即为 name_zh

————————————————————
【标准内部引用 / 排除规则】
————————————————————

当原文出现以下类型表述时：
- “表 X.X 中编号为……除外”
- “见表 X.X”
- “附录 X 中……除外”
- “除……外”

必须判断这是【标准内部引用】，而不是食品名称。

处理方式：
- 不得将该文本作为 food_name
- 在对应 usage 中生成 reference_exclusion 结构

reference_exclusion {
  standard: string | null   // 如 GB2760（仅当原文可判断）
  table: string | null      // 表编号，如 A.2
  ranges: string | null     // 编号范围，无法解析则为 null
  text: string              // 原文原句，不得改写
}

规则：
- 不展开被引用表内容
- 不推导或补全编号范围
- 即使仅出现“见表 X.X”，也必须生成 reference_exclusion

"""
# endregion


# region dsl2
DSL2_PROMPT = """SCHEMA_DEFINITION

SCHEMA_NAME: EXCEPTION_CATEGORY_INDEX

DESCRIPTION:
本 schema 用于解析食品安全国家标准中的
“例外食品类别表”，
作为后续 reference_exclusion 的可引用索引表。

本 schema 不生成任何添加剂使用规则。

————————————————————
【外层结构（强制）】
————————————————————

必须使用 TABLE 作为唯一外层结构。

TABLE {
  id: string        // 原文表编号
  title: string     // 原文表标题全文，如果原文中没有 title，则 title 为 null
}

TABLE 仅用于表达该例外表本身，
不得作为食品分类系统。

————————————————————
【TABLE.title 判定规则（重要）】
————————————————————

TABLE.title 仅在原文中存在“明确的表主题描述”时才赋值。

判定规则：
- 如果表标题文本中，除表编号外，还包含对表内容的描述性文字，
  则该描述性文字作为 title。
- 描述性文字必须逐字来源于原文，不得改写。

以下情况，TABLE.title 必须为 null：
- 标题仅包含表编号
- 标题包含“（续）”“（续表）”“continued”等续表标记
- 标题未提供新的表主题信息

示例（仅用于判定理解，不输出）：
- “表 A.2 表 A.1中例外食品编号对应的食品类别”
  → id = “表 A.2”
  → title = “表 A.1中例外食品编号对应的食品类别”

- “表 A.2（续）”
  → id = “表 A.2”
  → title = null

————————————————————
【核心记录结构】
————————————————————

EXCEPTION_CATEGORY {
  exception_id: string     // 例外食品类别编号，如“35.”
  food_category: string   // 食品分类号
  food_name: string       // 食品名称（含括号、示例）
}

————————————————————
【行映射规则】
————————————————————

- 表格中的每一行对应一个 EXCEPTION_CATEGORY
- “例外食品类别编号” → exception_id
- “食品分类号” → food_category
- “食品名称” → food_name

————————————————————
【严格约束】
————————————————————

- exception_id 必须保持原文格式（如“35.”、“36.”）
- 不得将 exception_id 转换为数字
- 不得推导编号范围（如 35~42）
- 不得合并多行
- food_category 不得拆分或改写
- food_name 必须完整保留括号与示例说明

————————————————————
【禁止行为】
————————————————————

- 不生成 ADD_ADDITIVE
- 不生成 usage
- 不生成 reference_exclusion
- 不建立任何跨表引用关系

本 TABLE 仅作为“可被引用的例外索引表”存在。
"""
# endregion


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
    pdf_path: str, page_ranges: List[Tuple[int, int, List[BaseMessage]]]
) -> List[str]:
    """
    从PDF中提取指定页数范围的文本

    Args:
        pdf_path: PDF文件路径
        page_ranges: 页数范围列表，每个元素为(start_page, end_page, messages)元组

    Returns:
        文本内容列表，每个元素对应一个页数范围的文本
    """
    texts = []

    # 使用PyMuPDF打开PDF（已导入pymupdf.layout激活布局功能）
    doc = pymupdf.open(pdf_path)
    try:
        total_pages = len(doc)
        print(f"PDF总页数: {total_pages}")

        for start_page, end_page, messages in page_ranges:
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
) -> List[Tuple[int, int, List[BaseMessage]]]:
    """
    解析页数范围配置

    Args:
        page_ranges: 页数范围列表，格式为：
            [
                {"pages": [1, 2], "messages": [SystemMessage(content="提示词")]},
                {"pages": [3], "messages": [SystemMessage(content="提示词")]},
                {"pages": [8, 148], "messages": [SystemMessage(content="提示词")], "split": True}  # split为True时拆分成单页
            ]

    Returns:
        解析后的配置列表，每个元素为 (start_page, end_page, messages) 元组
        messages 为消息列表（SystemMessage/HumanMessage等）
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

        # 必须提供 messages 字段
        if "messages" not in range_item:
            print(f"警告: 配置项缺少 'messages' 字段: {range_item}，跳过")
            continue

        messages = range_item["messages"]
        if not messages or not isinstance(messages, list) or len(messages) == 0:
            print(f"警告: messages 不能为空且必须是列表: {range_item}，跳过")
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
                parsed_configs.append((page_num, page_num, messages))
            print(
                f"  ✓ 配置: 页数 [{start_page}, {end_page}] 拆分为 {end_page - start_page + 1} 个单页, 提示词长度: {len(messages)} 字符"
            )
        else:
            parsed_configs.append((start_page, end_page, messages))
            print(
                f"  ✓ 配置: 页数 [{start_page}, {end_page}], 提示词长度: {len(messages)} 字符"
            )

    return parsed_configs


def check_overlapping_pages(
    page_ranges: List[Tuple[int, int, List[BaseMessage]]],
) -> List[Set[int]]:
    """
    检查页数范围是否有重叠

    Args:
        page_ranges: 页数范围列表，每个元素为 (start_page, end_page, messages) 元组
    Returns:
        重叠页面的集合列表，每个集合包含重叠的页面编号
    """
    overlapping_pages = []

    # 收集所有页面
    all_pages = {}
    for idx, (start, end, messages) in enumerate(page_ranges):
        for page in range(start, end + 1):
            if page not in all_pages:
                all_pages[page] = []
            all_pages[page].append(idx)

    # 找出重复的页面
    for page, indices in all_pages.items():
        if len(indices) > 1:
            overlapping_pages.append({page})

    return overlapping_pages


def detect_content_type(text: str) -> Tuple[str, str]:
    """
    检测内容是文本还是表格，如果是表格则直接生成并返回 schemaIR
    在一次 AI 调用中完成类型检测和 schemaIR 生成（如果是表格）
    
    Args:
        text: 原始文本内容
        
    Returns:
        (content_type, schema_ir) 元组
        - content_type: "text" 或 "table"
        - schema_ir: 如果是表格，返回生成的 schemaIR；如果是文本，返回空字符串
    """
    if not text or not text.strip():
        return ("text", "")
    
    # 取前5000字符用于检测和生成 schemaIR
    text_sample = text[:5000]
    
    detection_prompt = f"""请分析以下内容，判断它是文本还是表格。

内容：
<<<
{text_sample}
>>>

如果内容是表格，请直接生成一个 schemaIR 来描述这个表格的结构。
如果内容是文本，请只回答 "text"。

schemaIR 应该包含：
1. 表格的基本信息（表编号、表标题等）
2. 表格的列结构
3. 每列的数据类型和含义
4. 表格的行映射规则

请以 JSON 格式输出 schemaIR，格式如下：
{{
  "schema_name": "表格名称",
  "description": "表格描述",
  "table": {{
    "id": "表编号字段名",
    "title": "表标题字段名（如果存在）"
  }},
  "columns": [
    {{
      "name": "字段名",
      "type": "string|number|null",
      "description": "字段描述",
      "source": "来源列名或位置"
    }}
  ],
  "row_mapping": "行映射规则说明"
}}

输出格式：
- 如果是文本：只输出 "text"
- 如果是表格：输出 JSON 格式的 schemaIR"""
    
    try:
        messages = [
            SystemMessage(content="你是一个内容类型检测和表格结构分析专家。请根据内容判断是文本还是表格。如果是表格，请直接生成描述其结构的 schemaIR。"),
            HumanMessage(content=detection_prompt),
        ]
        result = chat(
            messages,
            provider_name="dashscope",
            provider_config={"model": "qwen3-max-preview", "temperature": 0.1},
        )
        result = result.strip()
        
        # 判断返回结果
        result_lower = result.lower()
        if "text" in result_lower and len(result) < 10:
            # 纯文本响应
            return ("text", "")
        else:
            # 尝试解析为 JSON（表格的 schemaIR）
            try:
                import json
                import re
                # 尝试提取 JSON 内容（可能被代码块包裹）
                json_text = result.strip()
                # 移除可能的 markdown 代码块标记
                json_text = re.sub(r'^```(?:json)?\s*\n', '', json_text, flags=re.MULTILINE)
                json_text = re.sub(r'\n```\s*$', '', json_text, flags=re.MULTILINE)
                json_text = json_text.strip()
                
                # 尝试提取 JSON 对象
                json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(0)
                
                # 验证是否为有效的 JSON
                schema_data = json.loads(json_text)
                # 如果解析成功，说明是表格的 schemaIR
                print("  📊 检测到表格，已生成 schemaIR")
                return ("table", result)
            except (json.JSONDecodeError, ValueError):
                # 如果不是有效的 JSON，可能是文本
                if "text" in result_lower:
                    return ("text", "")
                else:
                    # 无法确定，默认按文本处理
                    print(f"⚠️  无法解析返回结果，默认按文本处理: {result[:100]}")
                    return ("text", "")
                    
    except Exception as e:
        print(f"⚠️  内容类型检测失败: {e}，默认按文本处理")
        return ("text", "")


def generate_schema_ir(text: str) -> str:
    """
    如果检测到是表格，生成 schemaIR 来描述表格结构
    
    Args:
        text: 原始文本内容（表格）
        
    Returns:
        schemaIR 字符串
    """
    schema_generation_prompt = f"""请分析以下表格内容，生成一个 schemaIR 来描述这个表格的结构。

schemaIR 应该包含：
1. 表格的基本信息（表编号、表标题等）
2. 表格的列结构
3. 每列的数据类型和含义
4. 表格的行映射规则

请以 JSON 格式输出 schemaIR，格式如下：
{{
  "schema_name": "表格名称",
  "description": "表格描述",
  "table": {{
    "id": "表编号字段名",
    "title": "表标题字段名（如果存在）"
  }},
  "columns": [
    {{
      "name": "字段名",
      "type": "string|number|null",
      "description": "字段描述",
      "source": "来源列名或位置"
    }}
  ],
  "row_mapping": "行映射规则说明"
}}

内容：
<<<
{text[:5000]}
>>>
"""
    
    try:
        messages = [
            SystemMessage(content="你是一个表格结构分析专家。请分析表格内容并生成描述其结构的 schemaIR。"),
            HumanMessage(content=schema_generation_prompt),
        ]
        schema_ir = chat(
            messages,
            provider_name="dashscope",
            provider_config={"model": "qwen3-max-preview", "temperature": 0.1},
        )
        return schema_ir.strip()
    except Exception as e:
        print(f"⚠️  SchemaIR 生成失败: {e}")
        return ""


def render_schema_prompt(schema_ir: str) -> str:
    """
    将 schemaIR 转化为 prompt
    
    Args:
        schema_ir: schemaIR JSON 字符串（可能包含代码块标记）
        
    Returns:
        生成的 prompt 字符串
    """
    try:
        import json
        import re
        
        # 尝试提取 JSON 内容（可能被代码块包裹）
        json_text = schema_ir.strip()
        # 移除可能的 markdown 代码块标记
        json_text = re.sub(r'^```(?:json)?\s*\n', '', json_text, flags=re.MULTILINE)
        json_text = re.sub(r'\n```\s*$', '', json_text, flags=re.MULTILINE)
        json_text = json_text.strip()
        
        # 尝试提取 JSON 对象（如果 LLM 返回了其他文本）
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', json_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
        
        schema_data = json.loads(json_text)
        
        # 构建 prompt
        prompt_parts = []
        prompt_parts.append("SCHEMA_DEFINITION\n")
        prompt_parts.append(f"SCHEMA_NAME: {schema_data.get('schema_name', 'UNKNOWN')}\n\n")
        prompt_parts.append(f"DESCRIPTION:\n{schema_data.get('description', '')}\n\n")
        
        # 外层结构
        if "table" in schema_data:
            prompt_parts.append("————————————————————\n")
            prompt_parts.append("【外层结构】\n")
            prompt_parts.append("————————————————————\n\n")
            prompt_parts.append("TABLE {\n")
            if "id" in schema_data["table"]:
                prompt_parts.append(f"  id: string        // {schema_data['table']['id']}\n")
            if "title" in schema_data["table"]:
                prompt_parts.append(f"  title: string | null     // {schema_data['table']['title']}\n")
            prompt_parts.append("}\n\n")
        
        # 核心记录结构
        if "columns" in schema_data:
            prompt_parts.append("————————————————————\n")
            prompt_parts.append("【核心记录结构】\n")
            prompt_parts.append("————————————————————\n\n")
            prompt_parts.append("RECORD {\n")
            for col in schema_data["columns"]:
                col_type = col.get("type", "string")
                col_name = col.get("name", "")
                col_desc = col.get("description", "")
                prompt_parts.append(f"  {col_name}: {col_type}     // {col_desc}\n")
            prompt_parts.append("}\n\n")
        
        # 行映射规则
        if "row_mapping" in schema_data:
            prompt_parts.append("————————————————————\n")
            prompt_parts.append("【行映射规则】\n")
            prompt_parts.append("————————————————————\n\n")
            prompt_parts.append(f"{schema_data['row_mapping']}\n\n")
        
        return "".join(prompt_parts)
    except Exception as e:
        print(f"⚠️  SchemaIR 渲染失败: {e}")
        return ""


def convert_txt_to_markdown(text: str, messages: List[BaseMessage]) -> str:
    """
    使用LLM将txt文本转换为markdown格式
    首先检测内容是文本还是表格，然后选择相应的处理策略

    Args:
        text: 原始文本内容
        messages: 系统提示词列表（如果检测到表格，此参数可能被忽略）

    Returns:
        转换后的markdown格式文本
    """
    if not text or not text.strip():
        return text

    # 步骤1: 检测内容类型（如果是表格，会直接生成 schemaIR）
    print("  🔍 正在检测内容类型...")
    content_type, schema_ir = detect_content_type(text)
    print(f"  ✓ 检测结果: {content_type}")

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
                provider_config={"model": "qwen3-max-preview", "temperature": 0.1},
            )
            return markdown_text.strip()
        
        else:  # content_type == "table"
            # schemaIR 已经在检测阶段生成
            if not schema_ir:
                print("  ⚠️  SchemaIR 生成失败，使用默认 DSL 模式")
                # 如果生成失败，使用默认的 DSL 模式
                human_prompt = f"""请按照要求转换：
<<<
{text}
>>>
"""
                conversion_messages = [
                    SystemMessage(content=DSL_SYSTEM_PROMPT),
                    HumanMessage(content=DSL2_PROMPT),
                    HumanMessage(content=human_prompt),
                ]
            else:
                print("  🔧 将 schemaIR 转换为 prompt...")
                schema_prompt = render_schema_prompt(schema_ir)
                
                if not schema_prompt:
                    print("  ⚠️  Prompt 渲染失败，使用默认 DSL 模式")
                    human_prompt = f"""请按照要求转换：
<<<
{text}
>>>
"""
                    conversion_messages = [
                        SystemMessage(content=DSL_SYSTEM_PROMPT),
                        HumanMessage(content=DSL2_PROMPT),
                        HumanMessage(content=human_prompt),
                    ]
                else:
                    print("  ✅ 使用生成的 schema prompt 进行转换...")
                    human_prompt = f"""请按照要求转换：
<<<
{text}
>>>
"""
                    conversion_messages = [
                        SystemMessage(content=DSL_SYSTEM_PROMPT),
                        HumanMessage(content=schema_prompt),
                        HumanMessage(content=human_prompt),
                    ]
            
            markdown_text = chat(
                conversion_messages,
                provider_name="dashscope",
                provider_config={"model": "qwen3-max-preview", "temperature": 0.1},
            )
            return markdown_text.strip()
            
    except Exception as e:
        print(f"⚠️  LLM转换失败: {e}")
        print("   将使用原始文本作为Markdown内容")
        return text


def split_pdf_by_page_ranges(
    pdf_path: str,
    page_ranges: List[Dict[str, Any]],
    output_dir: str = "chunks",
):
    """
    根据页数范围分割PDF文件

    Args:
        pdf_path: PDF文件路径
        page_ranges: 页数范围列表，格式为：
            [
                {"pages": [1, 2], "messages": [SystemMessage(...)]},
                {"pages": [3], "messages": [SystemMessage(...)]}
            ]
        output_dir: 输出目录
    """
    print("\n📋 解析配置...")
    # 解析配置，获取页数范围和对应的提示词
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

    # 保存每个块
    print("\n💾 转换并保存文件...")
    for idx, ((start_page, end_page, messages), text) in enumerate(
        zip(parsed_configs, texts), 1
    ):
        # 生成文件名
        if start_page == end_page:
            filename = f"page_{start_page}.txt"
        else:
            filename = f"pages_{start_page}_{end_page}.txt"

        filepath = output_path / filename

        # 检查是否有重叠页面
        overlapping_pages_in_range = []
        if overlapping:
            for page in range(start_page, end_page + 1):
                for overlap_set in overlapping:
                    if page in overlap_set:
                        overlapping_pages_in_range.append(page)

        # 转换为Markdown并保存
        md_filepath = filepath.with_suffix(".md")
        print(
            f"\n  [{idx}/{len(parsed_configs)}] 正在处理第 {start_page}-{end_page} 页..."
        )
        print(f"  正在使用LLM转换为Markdown...")
        markdown_content = convert_txt_to_markdown(text, messages=messages)

        with open(md_filepath, "w", encoding="utf-8") as f:
            # 如果有重叠页面，添加TODO标记
            if overlapping_pages_in_range:
                f.write(
                    f"⚠️  TODO: 以下页面在其他块中也出现: {sorted(set(overlapping_pages_in_range))}\n\n"
                )

            f.write(markdown_content)

        print(f"  ✓ 已保存: {md_filepath} (字符数: {len(markdown_content):,})")

    print(f"\n✅ 完成！共生成 {len(texts)} 个md文件")


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
    # 示例1: 基本使用
    # page_ranges = [
    #     {"pages": [1, 2], "prompt": "你的提示词1"},
    #     {"pages": [3], "prompt": "你的提示词2"},
    # ]

    # 示例2: 有重叠页面的情况
    # page_ranges = [
    #     {"pages": [1, 2], "prompt": "提示词1"},
    #     {"pages": [2, 3], "prompt": "提示词2"},  # 第2页重叠
    # ]

    # ==================== 当前配置 ====================
    # 请修改下面的 page_ranges 来指定要分割的页数范围和提示词
    page_ranges = [
        # {"pages": [1], "prompt": MARKDOWN_PROMPT},
        # {"pages": [4, 6], "prompt": MARKDOWN_PROMPT},
        # {"pages": [7], "prompt": MARKDOWN_PROMPT},
        # # {"pages": [8, 148], "prompt": DSL2_PROMPT, "split": True},
        # {"pages": [8], "prompt": DSL_PROMPT},
        # {
        #     "pages": [149,150],
        #     "messages": [
        #         SystemMessage(content=DSL_SYSTEM_PROMPT),
        #         HumanMessage(content=DSL2_PROMPT),
        #     ],
        #     "split": True,
        # },
        {
            "pages": [151],
            "messages": [
                SystemMessage(content=MARKDOWN_PROMPT),
            ],
        },
    ]

    split_pdf_by_page_ranges(str(pdf_path), page_ranges, str(output_dir))
