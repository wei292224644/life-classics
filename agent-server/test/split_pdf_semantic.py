#!/usr/bin/env python3
"""
PDF语义切分脚本
按照语义边界切分PDF，确保表格完整，单个chunk尽量在8000字符以内
"""

import argparse
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import json

try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("错误: pdfplumber 未安装，请安装: pip install pdfplumber")


class SemanticPDFSplitter:
    """PDF语义切分器"""

    def __init__(self, max_chunk_size: int = 8000, min_chunk_size: int = 500):
        """
        初始化切分器

        Args:
            max_chunk_size: 单个chunk的最大字符数（默认8000）
            min_chunk_size: 单个chunk的最小字符数（默认500，小于此值会尝试合并）
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        # 章节标题模式（支持多种格式）
        self.section_patterns = [
            re.compile(r"^第[一二三四五六七八九十\d]+[章节部分]"),  # 第X章、第X节
            re.compile(r"^\d+\.\d+(\.\d+)?"),  # 1.1, 1.2.3
            re.compile(r"^[一二三四五六七八九十]+[、．.]"),  # 一、二、三、
            re.compile(r"^附录[ABCD一二三四五六七八九十]"),  # 附录A、附录一
            re.compile(r"^表\s*\d+"),  # 表1、表2
            re.compile(r"^图\s*\d+"),  # 图1、图2
        ]

    def is_section_header(self, line: str) -> bool:
        """
        判断是否为章节标题

        Args:
            line: 文本行

        Returns:
            是否为章节标题
        """
        line = line.strip()
        if not line or len(line) > 100:  # 标题通常不会太长
            return False

        # 检查是否匹配章节标题模式
        for pattern in self.section_patterns:
            if pattern.match(line):
                return True

        # 检查是否全是大写字母或数字（可能是英文标题）
        if line.isupper() and len(line) > 3 and len(line) < 50:
            return True

        return False

    def clean_header_footer(self, text: str) -> str:
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
            if stripped == "GB2760—2024":
                continue
            # 跳过单独一行的纯数字（页脚，通常是1-3位数字，最多4位）
            if stripped.isdigit() and 1 <= len(stripped) <= 4:
                continue
            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def split_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        切分PDF文件：遍历所有页面，提取文本，将所有文本合并成一个文件

        Args:
            pdf_path: PDF文件路径

        Returns:
            包含所有文本的单个chunk
        """
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber 未安装")

        print(f"开始处理PDF: {pdf_path}")

        # 收集所有页面的文本
        all_text_parts = []

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"总页数: {total_pages}")

            # 只处理前50页
            max_pages = min(5, total_pages)
            print(f"将处理前 {max_pages} 页")

            for page_num, page in enumerate(pdf.pages[:max_pages], start=1):
                if page_num % max_pages == 0:
                    print(f"处理第 {page_num}/{total_pages} 页...")

                # 提取文本
                try:
                    text = page.extract_text(layout=True) or ""
                    if text:
                        # 清理页眉页脚
                        cleaned_text = self.clean_header_footer(text)
                        if cleaned_text:
                            all_text_parts.append(cleaned_text)
                except Exception as e:
                    print(f"  警告: 提取文本失败: {e}")

        # 合并所有文本
        full_text = "\n".join(all_text_parts)
        print(f"总共提取了 {len(full_text)} 个字符")

        # 返回单个chunk
        processed_pages = min(50, total_pages)
        chunks = [
            {
                "content": full_text,
                "section": None,
                "page_start": 1,
                "page_end": processed_pages,
                "size": len(full_text),
            }
        ]

        print(f"\n切分完成，共生成 {len(chunks)} 个chunk")
        return chunks

    def _merge_small_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并过小的chunk（改进版，支持连续合并多个小chunk）

        Args:
            chunks: chunk列表

        Returns:
            合并后的chunk列表
        """
        if not chunks:
            return []

        merged_chunks = []
        i = 0

        while i < len(chunks):
            current_chunk = chunks[i]

            # 如果当前chunk太小，尝试连续合并多个小chunk
            if current_chunk["size"] < self.min_chunk_size:
                merged_parts = [current_chunk["content"]]
                merged_size = current_chunk["size"]
                merged_section = current_chunk.get("section")
                merged_page_start = current_chunk["page_start"]
                merged_page_end = current_chunk["page_end"]
                j = i + 1

                # 继续合并后续的小chunk，直到达到合理大小或超过限制
                while j < len(chunks):
                    next_chunk = chunks[j]
                    next_size = next_chunk["size"]
                    combined_size = merged_size + next_size + 2  # +2 for separator

                    # 如果合并后不超过限制，则合并
                    if combined_size <= self.max_chunk_size:
                        merged_parts.append(next_chunk["content"])
                        merged_size = combined_size
                        merged_page_end = next_chunk["page_end"]
                        if not merged_section:
                            merged_section = next_chunk.get("section")
                        j += 1

                        # 如果已经达到最小大小，可以停止合并（但继续合并小chunk也没问题）
                        if merged_size >= self.min_chunk_size:
                            # 如果下一个chunk也很大，停止合并
                            if (
                                j < len(chunks)
                                and chunks[j]["size"] >= self.min_chunk_size
                            ):
                                break
                    else:
                        # 如果合并后会超过限制，停止合并
                        break

                # 创建合并后的chunk
                merged_content = "\n\n".join(merged_parts)
                merged_chunks.append(
                    {
                        "content": merged_content,
                        "section": merged_section,
                        "page_start": merged_page_start,
                        "page_end": merged_page_end,
                        "size": len(merged_content),
                    }
                )
                i = j  # 跳过已合并的chunk
            else:
                # 如果chunk已经足够大，直接添加
                merged_chunks.append(current_chunk)
                i += 1

        return merged_chunks


def save_chunks(chunks: List[Dict[str, Any]], output_dir: Path):
    """
    保存chunks到文件

    Args:
        chunks: chunk列表
        output_dir: 输出目录
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # 删除之前生成的文件（.txt文件和summary.json）
    print(f"清理输出目录中的旧文件: {output_dir}")
    deleted_count = 0

    # 删除所有chunk_*.txt文件
    txt_files = list(output_dir.glob("chunk_*.txt"))
    for txt_file in txt_files:
        try:
            txt_file.unlink()
            deleted_count += 1
        except Exception as e:
            print(f"  警告: 无法删除 {txt_file.name}: {e}")

    # 删除summary.json文件
    summary_file = output_dir / "summary.json"
    if summary_file.exists():
        try:
            summary_file.unlink()
            deleted_count += 1
        except Exception as e:
            print(f"  警告: 无法删除 summary.json: {e}")

    if deleted_count > 0:
        print(f"  已删除 {deleted_count} 个旧文件")
    else:
        print(f"  没有找到旧文件")

    # 保存为单独的文本文件
    for idx, chunk in enumerate(chunks, start=1):
        filename = f"chunk_{idx:04d}.txt"
        filepath = output_dir / filename

        # 构建文件内容
        content_parts = []
        # if chunk.get('section'):
        #     content_parts.append(f"章节: {chunk['section']}")
        # content_parts.append(f"页码范围: {chunk['page_start']}-{chunk['page_end']}")
        # content_parts.append(f"大小: {chunk['size']} 字符")
        # content_parts.append("=" * 80)
        content_parts.append(chunk["content"])

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(content_parts))

    # 保存汇总信息
    summary = {
        "total_chunks": len(chunks),
        "total_size": sum(c["size"] for c in chunks),
        "avg_size": sum(c["size"] for c in chunks) / len(chunks) if chunks else 0,
        "max_size": max(c["size"] for c in chunks) if chunks else 0,
        "min_size": min(c["size"] for c in chunks) if chunks else 0,
        "chunks": [
            {
                "index": idx,
                "section": chunk.get("section"),
                "page_start": chunk["page_start"],
                "page_end": chunk["page_end"],
                "size": chunk["size"],
            }
            for idx, chunk in enumerate(chunks, start=1)
        ],
    }

    summary_path = output_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n保存完成:")
    print(f"  输出目录: {output_dir}")
    print(f"  总chunk数: {summary['total_chunks']}")
    print(f"  总大小: {summary['total_size']} 字符")
    print(f"  平均大小: {summary['avg_size']:.0f} 字符")
    print(f"  最大大小: {summary['max_size']} 字符")
    print(f"  最小大小: {summary['min_size']} 字符")


def main():
    parser = argparse.ArgumentParser(
        description="PDF语义切分工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 切分PDF文件
  python test/split_pdf_semantic.py test/gb2760/GB2760-2024.pdf
  
  # 指定输出目录和最大chunk大小
  python test/split_pdf_semantic.py test/gb2760/GB2760-2024.pdf --output output/chunks --max-size 6000
        """,
    )

    parser.add_argument(
        "pdf_path",
        help="PDF文件路径",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出目录（默认: PDF同目录下的chunks子目录）",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=8000,
        help="单个chunk的最大字符数（默认: 8000）",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        default=500,
        help="单个chunk的最小字符数，小于此值会尝试合并（默认: 500）",
    )

    args = parser.parse_args()

    if not PDFPLUMBER_AVAILABLE:
        print("错误: pdfplumber 未安装")
        print("请安装: pip install pdfplumber")
        return

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"错误: PDF文件不存在: {pdf_path}")
        return

    # 确定输出目录
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = pdf_path.parent / "chunks" / pdf_path.stem

    # 创建切分器并切分
    splitter = SemanticPDFSplitter(
        max_chunk_size=args.max_size, min_chunk_size=args.min_size
    )
    chunks = splitter.split_pdf(str(pdf_path))

    # 保存结果
    save_chunks(chunks, output_dir)


if __name__ == "__main__":
    main()
