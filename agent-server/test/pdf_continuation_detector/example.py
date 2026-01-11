#!/usr/bin/env python3
"""
根据给定的页数范围切分PDF内容，导出成txt文件

示例：
    page_ranges = [[1, 2], [3]]  # 将1-2页分成一个内容，3页分成一个内容
    page_ranges = [[1, 2], [2, 3]]  # 将1-2页分成一个内容，2-3页分成一个内容（重叠情况，TODO处理）
"""

import sys
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("警告: pdfplumber 未安装，请安装: pip install pdfplumber")


def clean_header_footer(text: str) -> str:
    """
    清理页眉页脚：删除页眉中的"GB"和页脚的页数

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
        stripped = line.strip()
        # 跳过单独一行的"GB"（页眉）
        if stripped == "GB2760—2024" or stripped == "GB 2760—2024":
            continue
        # 跳过单独一行的纯数字（页脚，通常是1-3位数字，最多4位）
        if stripped.isdigit() and 1 <= len(stripped) <= 4:
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def extract_pages_text(
    pdf_path: str, page_ranges: List[List[int]], output_dir: str = None
) -> List[Tuple[str, str]]:
    """
    根据给定的页数范围切分PDF内容，导出成txt文件

    Args:
        pdf_path: PDF文件路径
        page_ranges: 页数范围列表，如 [[1,2], [3]] 或 [[1,2], [2,3]]
        output_dir: 输出目录，如果为None则使用PDF同目录下的chunks子目录

    Returns:
        列表，每个元素为 (输出文件路径, 内容)
    """
    if not PDFPLUMBER_AVAILABLE:
        raise ImportError("pdfplumber 未安装，请安装: pip install pdfplumber")

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

    # 检查是否有重叠的页数范围
    all_pages = set()
    overlapping_ranges = []
    for i, page_range in enumerate(page_ranges):
        if len(page_range) == 1:
            page_set = {page_range[0]}
        else:
            start, end = page_range[0], page_range[1]
            page_set = set(range(start, end + 1))

        # 检查是否与之前的范围重叠
        if all_pages & page_set:
            overlapping_ranges.append((i, page_range, all_pages & page_set))

        all_pages.update(page_set)

    # TODO: 处理重叠的页数范围
    # 如果 page_ranges 中有重叠（如 [[1,2], [2,3]]），说明某些页既属于第一块，也属于第二块
    # 需要决定如何处理：是复制内容到两个文件，还是只保留在一个文件中
    # 当前实现：如果范围重叠，会在两个文件中都包含重叠的页面内容
    if overlapping_ranges:
        print("⚠️  警告: 检测到重叠的页数范围:")
        for idx, page_range, overlapping_pages in overlapping_ranges:
            print(
                f"  范围 {idx+1}: {page_range} 与之前的范围重叠，重叠页数: {sorted(overlapping_pages)}"
            )
        print("  TODO: 后续需要处理重叠页面的分割逻辑")
        print()

    # 确定输出目录
    if output_dir is None:
        output_dir = pdf_file.parent / "chunks"
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(f"PDF 内容切分")
    print(f"文件: {pdf_path}")
    print(f"页数范围: {page_ranges}")
    print(f"输出目录: {output_dir}")
    print("=" * 80)
    print()

    results = []

    try:
        with pdfplumber.open(str(pdf_file)) as pdf:
            total_pages = len(pdf.pages)
            print(f"PDF 总页数: {total_pages}\n")

            # 处理每个页数范围
            for idx, page_range in enumerate(page_ranges, start=1):
                # 确定页码范围
                if len(page_range) == 1:
                    start_page = end_page = page_range[0]
                else:
                    start_page, end_page = page_range[0], page_range[1]

                # 验证页码范围
                if start_page < 1 or end_page > total_pages:
                    print(
                        f"⚠️  范围 {idx}: 页码范围 {page_range} 超出PDF总页数 {total_pages}，跳过"
                    )
                    continue

                if start_page > end_page:
                    print(
                        f"⚠️  范围 {idx}: 起始页 {start_page} 大于结束页 {end_page}，跳过"
                    )
                    continue

                # 提取页码范围的内容
                content_parts = []
                print(f"处理范围 {idx}: 第 {start_page} 页 ~ 第 {end_page} 页")

                for page_num in range(start_page, end_page + 1):
                    try:
                        page = pdf.pages[page_num - 1]  # pdfplumber 使用0-based索引
                        text = page.extract_text_lines() or ""
                        if text:
                            # 清理页眉页脚
                            cleaned_text = clean_header_footer(text)
                            content_parts.append(cleaned_text)
                            # print(f"  ✓ 已提取第 {page_num} 页文本 ({len(cleaned_text)} 字符)")
                        else:
                            print(f"  ⚠ 第 {page_num} 页无文本内容")
                    except Exception as e:
                        print(f"  ✗ 提取第 {page_num} 页失败: {e}")

                # 合并内容
                full_content = "\n\n".join(content_parts)

                # 生成输出文件名
                if len(page_range) == 1:
                    filename = f"chunk_{idx:03d}_page_{start_page}.txt"
                else:
                    filename = f"chunk_{idx:03d}_pages_{start_page}-{end_page}.txt"

                output_file = output_dir / filename

                # 写入文件
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(full_content)

                print(f"  ✓ 已保存到: {output_file} ({len(full_content)} 字符)\n")

                results.append((str(output_file), full_content))

        print("=" * 80)
        print(f"切分完成！共生成 {len(results)} 个文件")
        print("=" * 80)

        return results

    except Exception as e:
        print(f"错误: 处理PDF时发生异常: {e}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    # 示例1: 简单的页数范围
    # page_ranges = [[1, 2], [3]]

    # 示例2: 有重叠的页数范围（TODO处理）
    # page_ranges = [[1, 2], [2, 3]]

    # 实际使用：根据延续判定结果设置页数范围
    page_ranges = [
        [1],
        [2],
        [3],
        [4, 6],
        [7],
        [8, 148],
        [149, 150],
        [151],
        [152, 168],
        [168, 225],
        [226, 227],
        [227, 233],
        [233, 242],
        [243],
        [244, 254],
        [255, 264],
    ]

    pdf_path = project_root / "test" / "gb2760" / "GB2760-2024.pdf"
    extract_pages_text(str(pdf_path), page_ranges)
