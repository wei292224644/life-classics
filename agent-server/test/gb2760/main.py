"""
根据页数范围分割PDF文件，并将结果导入到知识库

输入格式：[{"pages": [1, 2]}, {"pages": [3]}]
每个配置项必须包含：
- pages: 页数范围，可以是单个数字 [1] 或范围 [1, 2]
可选配置项：
- split: 布尔值，如果为True且pages是范围，则将范围拆分成多个单页处理（默认False）

处理流程：
1. 从PDF提取指定页面的文本
2. 使用LLM将文本转换为结构化Markdown
3. 通过架构的 convert_to_structured 生成 markdown_cache
4. 使用架构的 split_structured 切分文档
5. 将 chunks 导入到知识库

注意：
- prompt 现在通过 AI 自动生成，无需手动配置
- 处理后的内容会直接导入到知识库，不再保存为文件
- markdown_cache 会自动生成并保存到架构的 markdown_cache 目录
"""

import pymupdf.layout  # 必须先导入这个来激活布局功能
import pymupdf4llm
import pymupdf  # PyMuPDF
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Set, Dict, Any

# 添加项目根目录到路径，以便导入app模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import chat
from app.core.document_chunk import DocumentChunk, ContentType
from app.core.kb.pre_parse.convert_to_structured import convert_to_structured
from app.core.kb.strategy.structured_strategy import split_structured
from app.core.kb.vector_store import vector_store_manager
import uuid


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


def extract_pages_text(
    pdf_path: str, page_ranges: List[Tuple[int, int, bool]]
) -> List[str]:
    """
    从PDF中提取指定页数范围的文本，使用 pymupdf4llm.to_markdown 转换为 markdown

    Args:
        pdf_path: PDF文件路径
        page_ranges: 页数范围列表，每个元素为(start_page, end_page, is_split)元组

    Returns:
        markdown 文本内容列表，每个元素对应一个页数范围的 markdown 文本
    """
    texts = []

    # 使用PyMuPDF打开PDF
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

            # 构建页数列表（pymupdf4llm 使用 0-based 索引）
            page_indices = [
                page_num - 1 for page_num in range(start_page, end_page + 1)
            ]

            # 使用 pymupdf4llm.to_markdown 提取并转换为 markdown
            markdown_text = pymupdf4llm.to_markdown(
                doc, pages=page_indices, header=False, footer=False
            )

            texts.append(markdown_text)
            print(
                f"✓ 已提取第 {start_page}-{end_page} 页，共 {end_page - start_page + 1} 页，字符数量: {len(markdown_text):,}"
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


def split_pdf_by_page_ranges(
    pdf_path: str,
    page_ranges: list[dict[str, Any]],
    output_dir: str = "chunks",  # 保留参数以保持兼容性，但不再使用
):
    """
    根据页数范围分割PDF文件，并将结果导入到知识库

    Args:
        pdf_path: PDF文件路径
        page_ranges: 页数范围列表，格式为：
            [
                {"pages": [1, 2]},
                {"pages": [3]},
                {"pages": [3, 100], "split": True}
            ]
        output_dir: 输出目录（已废弃，保留以保持兼容性）

    注意：
    - prompt 现在通过 AI 自动生成，无需手动配置
    - 处理后的内容会直接导入到知识库，不再保存为文件
    - markdown_cache 会自动生成并保存到架构的 markdown_cache 目录
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
        print("   这些页面会出现在多个块中\n")

    # 提取文本
    print("\n📄 提取文本...")
    texts = extract_pages_text(pdf_path, parsed_configs)

    # 获取PDF文件名（不含扩展名）作为基础 doc_id
    pdf_name = Path(pdf_path).stem

    # 处理每个块并导入到知识库
    print("\n💾 处理并导入到知识库...")

    all_chunks = []

    for idx, ((start_page, end_page, is_split), markdown_content) in enumerate(
        zip(parsed_configs, texts), 1
    ):
        # 记录开始处理
        start_time = datetime.now()
        print(
            f"\n  [{idx}/{len(parsed_configs)}] 正在处理第 {start_page}-{end_page} 页..."
        )

        try:
            # 如果需要调试查看原始 Markdown，这里将其写入本地文件
            # 确保 chunks 目录存在
            chunks_dir = Path(output_dir)
            chunks_dir.mkdir(parents=True, exist_ok=True)
            with open(chunks_dir / f"page_{start_page}.md", "w", encoding="utf-8") as f:
                f.write(markdown_content)
            doc_id = "GB2760-2024"

            # 生成 markdown_id（唯一标识）
            markdown_id = uuid.uuid4().hex[:16]

            # 创建 DocumentChunk
            document_chunk = DocumentChunk(
                doc_id=doc_id,
                doc_title=doc_id,
                section_path=[],
                content_type=ContentType.NOTE,
                content=markdown_content,
                meta={
                    "file_name": pdf_name,
                    "source_format": "pdf",
                    "page_range": f"{start_page}-{end_page}",
                    "is_split": is_split,
                },
                markdown_id=markdown_id,
            )

            # 使用架构中的 convert_to_structured 处理（这会生成 markdown_cache）
            print(f"  正在转换为结构化格式...")
            document_chunk = convert_to_structured(document_chunk)
            print(f"  ✓ 结构化转换完成")

            # 使用架构中的 split_structured 切分
            print(f"  正在切分文档...")
            chunks = split_structured([document_chunk])
            print(f"  ✓ 切分完成，生成 {len(chunks)} 个 chunks")

            all_chunks.extend(chunks)

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"  ✓ 处理完成，耗时: {duration:.2f} 秒")

        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            print(f"  ❌ 处理失败: {e} (耗时: {duration:.2f} 秒)")
            raise

    # 将所有 chunks 导入到知识库
    if all_chunks:
        print(f"\n📚 正在导入 {len(all_chunks)} 个 chunks 到知识库...")
        vector_store_manager.add_chunks(all_chunks)
        print(f"  ✓ 成功导入到知识库")

    print(f"\n✅ 完成！共处理 {len(texts)} 个页面块，生成 {len(all_chunks)} 个 chunks")


if __name__ == "__main__":
    # 获取脚本所在目录
    script_dir = Path(__file__).parent

    # PDF文件路径（相对于脚本所在目录）
    pdf_path = script_dir / "GB2760-2024.pdf"

    # 从知识库中删除所有 chunks
    vector_store_manager.delete_by_doc_id("GB2760-2024")

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
        {"pages": [4, 6]},
        # {"pages": [8, 10], "split": True},
        # {"pages": [149, 150], "split": True},
        # {"pages": [220, 221], "split": True},
        # {"pages": [238, 241], "split": True},
        {"pages": [233], "split": True},
    ]

    split_pdf_by_page_ranges(str(pdf_path), page_ranges, str(output_dir))
