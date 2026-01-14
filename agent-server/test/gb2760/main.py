"""
根据页数范围分割PDF文件
输入格式：[{"pages": [1, 2], "prompt": "提示词"}, {"pages": [3], "prompt": "提示词"}]
每个配置项必须包含：
- pages: 页数范围，可以是单个数字 [1] 或范围 [1, 2]
- prompt: 系统提示词字符串
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
DSL_PROMPT = """你是一个"食品安全国家标准结构化专家"。

你的任务是：  
将来自 PDF 版式解析结果（基于坐标的文本数组） 的内容，  
严格转换为【领域专用 DSL（Domain Specific Language）】格式数据，  
用于食品添加剂知识库构建。

输入数据格式为 列表数组，每个元素表示一个文本片段：

(x0, y0, x1, y1, text, line_id, block_id)

其中：

- x0, y0, x1, y1：页面坐标（左上 → 右下）  
- text：原始文本（可能包含换行、断词）  
- line_id / block_id：不保证可靠，仅作参考  

你必须 基于坐标顺序重建阅读顺序与表格结构。

你必须遵守以下规则：  
1. ❌ 不允许编造、补全、推测任何未明确出现的信息  
2. ✅ 所有字段必须来源于原文  
3. ✅ 表格必须被还原为结构化 usage 块  
4. ❌ 不允许解释、总结、评论  
5. ❌ 不输出自然语言  
6. ✅ 只输出 DSL  
7. 如果字段不存在，使用 null  
8. 如果是"按生产需要适量使用"，不要给数值  
9. 同一个添加剂可能有多个 usage  
10. 每个添加剂必须单独输出一个 ADD_ADDITIVE 块  

---

### 🔹 TABLE 外层结构规则（新增）

当原文中存在明确的表格标题（如“表 A.1 ……”、“表 A.2 ……”），  
且该表格标题在版式上作为一组 ADD_ADDITIVE 的共同来源时：

- 允许使用 TABLE 作为最外层容器  
- TABLE 仅用于表达版式与来源分组，不改变 ADD_ADDITIVE 的语义  

**TABLE 结构定义如下：**

TABLE {
    id: string
    title: string
    rows: ADD_ADDITIVE[]
}

**规则约束：**
1. TABLE 必须来源于原文表标题，不允许改写  
2. TABLE 只能作为外层分组容器，不得省略 ADD_ADDITIVE  
3. ADD_ADDITIVE 不得依赖 TABLE 才成立，其结构与语义保持不变  
4. 若原文未出现明确表标题，则不生成 TABLE，直接输出 ADD_ADDITIVE  
5. 不允许嵌套 TABLE  

---

### 🔹 DSL Schema 约束（极其重要）

DSL 结构必须严格遵循以下 schema：

ADD_ADDITIVE {
    name_zh: string
    name_en: string | null
    CNS: string[] | null
    INS: string[] | null
    function: string[] | null

    usage {
        food_category: string
        food_name: string
        max_amount: number | null
        unit: "g/kg" | null
        rule: string | null
        remark: string | null
    }
}

---

### 🔹 表格解析规则（防 AI 翻车）

- “食品分类号” → food_category  
- “食品名称” → food_name  
- “最大使用量” → max_amount  
- 单位统一为 g/kg（如果原文有）  
- “按生产需要适量使用” → max_amount = null, rule = 原文  
- “备注” → remark  
- 一个表格行 = 一个 usage  

---

### 🔹 特殊文本处理规则（关键）

- “CNS号”“INS号”可能在多行，需合并  
- “功能”字段可能为多个，用数组  
- 中英文名称分别识别  
- 标题即为添加剂名称  
- 相邻但无表格的说明，不生成 usage  

---

### 🔹 输出格式规则（非常重要）

当原文中出现以下“引用 / 排除”类型表述时：

- “表X.X中编号为……除外”  
- “见表X.X”  
- “附录X中……除外”  
- “除……外”  

你必须判断这是【标准内部引用】，而不是食品名称。

**处理规则：**
1. 不要将该内容作为 food_name  
2. 在对应的 usage 中生成 reference_exclusion 结构  
3. reference_exclusion 必须包含：  
   - standard（如 GB2760，若原文可判断）  
   - table（如 A.2）  
   - ranges（如 1~62、64~，无法解析则为 null）  
   - text（必须为原文原句）  
4. 不展开表内容  
5. 不进行语义推导  
6. 如果只是“见表X.X”但未出现“除外”，仍生成 reference_exclusion  

---

### 🔹 输出要求

- 只输出 DSL  
- 不要 Markdown  
- 不要 JSON  
- 不要代码块  
- 不要解释  
- 不要多余空行"""
# endregion


# region dsl2
DSL2_PROMPT = """你是一个"食品安全国家标准解析专家"。

你的任务是：
将来自 PDF 版式解析结果（基于坐标的文本数组） 的内容，
严格转换为【领域专用 DSL（Domain Specific Language）】格式数据，
用于食品添加剂知识库构建。

输入数据格式为 列表数组，每个元素表示一个文本片段：

(x0, y0, x1, y1, text, line_id, block_id)

其中：

x0, y0, x1, y1：页面坐标（左上 → 右下）"""
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


def extract_pages_text(pdf_path: str, page_ranges: List[Tuple[int, int]]) -> List[str]:
    """
    从PDF中提取指定页数范围的文本

    Args:
        pdf_path: PDF文件路径
        page_ranges: 页数范围列表，每个元素为(start_page, end_page)元组

    Returns:
        文本内容列表，每个元素对应一个页数范围的文本
    """
    texts = []

    # 使用PyMuPDF打开PDF（已导入pymupdf.layout激活布局功能）
    doc = pymupdf.open(pdf_path)
    try:
        total_pages = len(doc)
        print(f"PDF总页数: {total_pages}")

        for start_page, end_page in page_ranges:
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
) -> List[Tuple[int, int, str]]:
    """
    解析页数范围配置

    Args:
        page_ranges: 页数范围列表，格式为：
            [
                {"pages": [1, 2], "prompt": "提示词"},
                {"pages": [3], "prompt": "提示词"},
                {"pages": [8, 148], "prompt": "提示词", "split": True}  # split为True时拆分成单页
            ]

    Returns:
        解析后的配置列表，每个元素为 (start_page, end_page, prompt) 元组
        prompt 为系统提示词字符串
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

        # 必须提供 prompt 字段
        if "prompt" not in range_item:
            print(f"警告: 配置项缺少 'prompt' 字段: {range_item}，跳过")
            continue

        prompt = range_item["prompt"]
        if not prompt or not prompt.strip():
            print(f"警告: 提示词不能为空: {range_item}，跳过")
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
                parsed_configs.append((page_num, page_num, prompt))
            print(
                f"  ✓ 配置: 页数 [{start_page}, {end_page}] 拆分为 {end_page - start_page + 1} 个单页, 提示词长度: {len(prompt)} 字符"
            )
        else:
            parsed_configs.append((start_page, end_page, prompt))
            print(
                f"  ✓ 配置: 页数 [{start_page}, {end_page}], 提示词长度: {len(prompt)} 字符"
            )

    return parsed_configs


def check_overlapping_pages(page_ranges: List[Tuple[int, int]]) -> List[Set[int]]:
    """
    检查页数范围是否有重叠

    Args:
        page_ranges: 页数范围列表

    Returns:
        重叠页面的集合列表，每个集合包含重叠的页面编号
    """
    overlapping_pages = []

    # 收集所有页面
    all_pages = {}
    for idx, (start, end) in enumerate(page_ranges):
        for page in range(start, end + 1):
            if page not in all_pages:
                all_pages[page] = []
            all_pages[page].append(idx)

    # 找出重复的页面
    for page, indices in all_pages.items():
        if len(indices) > 1:
            overlapping_pages.append({page})

    return overlapping_pages


def convert_txt_to_markdown(text: str, system_prompt: str = None) -> str:
    """
    使用LLM将txt文本转换为markdown格式

    Args:
        text: 原始文本内容
        system_prompt: 系统提示词，如果为None则使用默认模式（dsl）的提示词

    Returns:
        转换后的markdown格式文本
    """
    if not text or not text.strip():
        return text

    # 如果没有提供提示词，使用默认模式的提示词
    if system_prompt is None:
        system_prompt = PROMPT_MODES.get(DEFAULT_MODE, "")

    human_prompt = f"""以下是通过 extract_text() 得到的原始文本，请按照要求转换：
<<<
{text}
>>>
"""

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]
        markdown_text = chat(
            messages,
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
                {"pages": [1, 2], "prompt": "提示词1"},
                {"pages": [3], "prompt": "提示词2"}
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
    ranges = [(start, end) for start, end, _ in parsed_configs]

    # 检查重叠页面
    overlapping = check_overlapping_pages(ranges)
    if overlapping:
        overlapping_pages = set()
        for overlap_set in overlapping:
            overlapping_pages.update(overlap_set)
        print(f"\n⚠️  检测到页面重叠: {sorted(overlapping_pages)}")
        print("   这些页面会出现在多个块中，将在文件中标记TODO\n")

    # 提取文本
    print("\n📄 提取文本...")
    texts = extract_pages_text(pdf_path, ranges)

    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 保存每个块
    print("\n💾 转换并保存文件...")
    for idx, ((start_page, end_page, prompt), text) in enumerate(
        zip(parsed_configs, texts), 1
    ):
        # 生成文件名
        if start_page == end_page:
            filename = f"chunk_{idx}_page_{start_page}.txt"
        else:
            filename = f"chunk_{idx}_pages_{start_page}_{end_page}.txt"

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
        markdown_content = convert_txt_to_markdown(text, system_prompt=prompt)

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
        {"pages": [8], "prompt": DSL_PROMPT},
        # {"pages": [156], "prompt": DSL2_PROMPT},
    ]

    split_pdf_by_page_ranges(str(pdf_path), page_ranges, str(output_dir))
