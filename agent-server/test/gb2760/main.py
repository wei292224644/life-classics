"""
根据页数范围分割PDF文件
输入格式：[[1,2],[3]] 表示第1-2页是一块，第3页是一块
输入格式：[[1,2],[2,3]] 表示第1-2页是一块，第2-3页是一块（第2页重复，需要打TODO标签）
"""

import json
import pymupdf.layout  # 必须先导入这个来激活布局功能
import pymupdf  # PyMuPDF
import re
import sys
from pathlib import Path
from typing import List, Tuple, Set

# 添加项目根目录到路径，以便导入app模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import chat


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


def convert_txt_to_markdown(text: str) -> str:
    """
    使用LLM将txt文本转换为markdown格式

    Args:
        text: 原始文本内容

    Returns:
        转换后的markdown格式文本
    """
    if not text or not text.strip():
        return text

    # 构建prompt，要求整理格式但不修改数据内容
    system_prompt = """你是一个“食品安全国家标准结构化专家”。

你的任务是：
将来自 PDF 版式解析结果（基于坐标的文本数组） 的内容，
严格转换为【领域专用 DSL（Domain Specific Language）】格式数据，
用于食品添加剂知识库构建。

输入数据格式为 列表数组，每个元素表示一个文本片段：

(x0, y0, x1, y1, text, line_id, block_id)

其中：

x0, y0, x1, y1：页面坐标（左上 → 右下）

text：原始文本（可能包含换行、断词）

line_id / block_id：不保证可靠，仅作参考

你必须 基于坐标顺序重建阅读顺序与表格结构。

你必须遵守以下规则：
1. ❌ 不允许编造、补全、推测任何未明确出现的信息
2. ✅ 所有字段必须来源于原文
3. ✅ 表格必须被还原为结构化 usage 块
4. ❌ 不允许解释、总结、评论
5. ❌ 不输出自然语言
6. ✅ 只输出 DSL
7. 如果字段不存在，使用 null
8. 如果是“按生产需要适量使用”，不要给数值
9. 同一个添加剂可能有多个 usage
10. 每个添加剂必须单独输出一个 ADD_ADDITIVE 块
🔹 DSL Schema 约束（极其重要）
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
🔹 表格解析规则（防 AI 翻车）

表格解析规则：
- “食品分类号” → food_category
- “食品名称” → food_name
- “最大使用量” → max_amount
- 单位统一为 g/kg（如果原文有）
- “按生产需要适量使用” → max_amount = null, rule = 原文
- “备注” → remark
- 一个表格行 = 一个 usage
🔹 特殊文本处理规则（关键）

文本识别规则：
- “CNS号”“INS号”可能在多行，需合并
- “功能”字段可能为多个，用数组
- 中英文名称分别识别
- 标题即为添加剂名称
- 相邻但无表格的说明，不生成 usage
🔹 输出格式规则（非常重要）

当原文中出现以下“引用 / 排除”类型表述时：
- “表X.X中编号为……除外”
- “见表X.X”
- “附录X中……除外”
- “除……外”

你必须判断这是【标准内部引用】，而不是食品名称。

处理规则：
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

输出要求：
- 只输出 DSL
- 不要 Markdown
- 不要 JSON
- 不要代码块
- 不要解释
- 不要多余空行"""

    human_prompt = f"""以下是通过 extract_text() 得到的原始文本，请转换为 DSL：
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
    pdf_path: str, page_ranges: List[List[int]], output_dir: str = "chunks"
):
    """
    根据页数范围分割PDF文件

    Args:
        pdf_path: PDF文件路径
        page_ranges: 页数范围列表，格式如 [[1,2],[3]] 或 [[1,2],[2,3]]
        output_dir: 输出目录
    """
    # 转换输入格式：[[1,2],[3]] -> [(1,2), (3,3)]
    ranges = []
    for range_item in page_ranges:
        if len(range_item) == 1:
            ranges.append((range_item[0], range_item[0]))
        elif len(range_item) == 2:
            ranges.append((range_item[0], range_item[1]))
        else:
            print(f"警告: 无效的页数范围 {range_item}，跳过")
            continue

    # 检查重叠页面
    overlapping = check_overlapping_pages(ranges)
    if overlapping:
        overlapping_pages = set()
        for overlap_set in overlapping:
            overlapping_pages.update(overlap_set)
        print(f"\n⚠️  检测到页面重叠: {sorted(overlapping_pages)}")
        print("   这些页面会出现在多个块中，将在文件中标记TODO\n")

    # 提取文本
    texts = extract_pages_text(pdf_path, ranges)

    # 创建输出目录
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 保存每个块
    for idx, (range_item, text) in enumerate(zip(ranges, texts), 1):
        start_page, end_page = range_item

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

        # # 写入txt文件
        # with open(filepath, "w", encoding="utf-8") as f:
        #     # 如果有重叠页面，添加TODO标记
        #     if overlapping_pages_in_range:
        #         f.write(
        #             f"⚠️  TODO: 以下页面在其他块中也出现: {sorted(set(overlapping_pages_in_range))}\n\n"
        #         )

        #     f.write(text)

        # 转换为Markdown并保存
        md_filepath = filepath.with_suffix(".md")
        print(f"  正在使用LLM转换为Markdown...")
        markdown_content = convert_txt_to_markdown(text)

        with open(md_filepath, "w", encoding="utf-8") as f:
            # 如果有重叠页面，添加TODO标记
            if overlapping_pages_in_range:
                f.write(
                    f"⚠️  TODO: 以下页面在其他块中也出现: {sorted(set(overlapping_pages_in_range))}\n\n"
                )

            f.write(markdown_content)

        print(f"✓ 已保存: {filepath} (字符数: {len(text):,})")
        print(f"✓ 已保存: {md_filepath} (字符数: {len(markdown_content):,})")

    print(f"\n✅ 完成！共生成 {len(texts)} 个txt文件和 {len(texts)} 个md文件")


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

    # 示例1: [[1,2],[3]]
    # page_ranges = [[1, 2], [3]]

    # 示例2: [[1,2],[2,3]] - 有重叠
    # page_ranges = [[1, 2], [2, 3]]

    # 请修改下面的 page_ranges 来指定要分割的页数范围
    page_ranges = [
        # [1, "smaple"],
        # # [2], [3],
        # [4, 6, "smaple"],
        # [7, "sample"],
        # [8, "dsl"],
        # [9, "dsl"],
        [156]
    ]  # 修改这里

    split_pdf_by_page_ranges(str(pdf_path), page_ranges, str(output_dir))
