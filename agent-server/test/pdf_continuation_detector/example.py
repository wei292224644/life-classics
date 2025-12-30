#!/usr/bin/env python3
"""
使用示例：对 GB2760-2024.pdf 的前 20 页进行是否延续的分析
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("警告: pdfplumber 未安装，请安装: pip install pdfplumber")

from core.detector import detect_page_continuation
from core.models import PageContext
from core.config import CONTINUATION_THRESHOLD


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


def analyze_pdf_continuation(pdf_path: str, max_pages: int = 20):
    """
    分析 PDF 前 N 页，判断每一页是否是上一页的延续
    
    Args:
        pdf_path: PDF 文件路径
        max_pages: 要处理的最大页数
    """
    if not PDFPLUMBER_AVAILABLE:
        print("错误: pdfplumber 未安装，无法读取 PDF 文件")
        print("请安装: pip install pdfplumber")
        return
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"错误: PDF 文件不存在: {pdf_path}")
        return
    
    print("=" * 80)
    print(f"PDF 跨页延续判定分析")
    print(f"文件: {pdf_path}")
    print(f"处理页数: 前 {max_pages} 页")
    print(f"判定阈值: {CONTINUATION_THRESHOLD}")
    print("=" * 80)
    print()
    
    # 存储每一页的文本和行
    page_data = []  # [(page_num, text, lines), ...]
    
    try:
        with pdfplumber.open(str(pdf_file)) as pdf:
            total_pages = len(pdf.pages)
            pages_to_process = min(max_pages, total_pages)
            
            print(f"PDF 总页数: {total_pages}")
            print(f"将处理前 {pages_to_process} 页\n")
            
            # 提取每一页的文本
            for page_num in range(1, pages_to_process + 1):
                try:
                    page = pdf.pages[page_num - 1]
                    text = page.extract_text(layout=True) or ""
                    if text:
                        # 清理页眉页脚
                        cleaned_text = clean_header_footer(text)
                        # 分割为行
                        lines = [line.strip() for line in cleaned_text.split('\n') if line.strip()]
                        page_data.append((page_num, cleaned_text, lines))
                        print(f"✓ 已提取第 {page_num} 页文本 ({len(cleaned_text)} 字符, {len(lines)} 行)")
                    else:
                        page_data.append((page_num, "", []))
                        print(f"⚠ 第 {page_num} 页无文本内容")
                except Exception as e:
                    print(f"✗ 提取第 {page_num} 页失败: {e}")
                    page_data.append((page_num, "", []))
        
        print()
        print("=" * 80)
        print("开始判定跨页延续...")
        print("=" * 80)
        print()
        
        # 统计信息
        continuation_count = 0
        non_continuation_count = 0
        
        # 对每一页（从第 2 页开始）判断是否是上一页的延续
        for i in range(1, len(page_data)):
            prev_page_num, prev_text, prev_lines = page_data[i - 1]
            curr_page_num, curr_text, curr_lines = page_data[i]
            
            if not prev_text or not curr_text:
                print(f"第 {curr_page_num} 页: 跳过（上一页或当前页无文本）")
                continue
            
            # 构建 PageContext
            context = PageContext(
                page_index=i,  # 当前页索引（从 0 开始）
                current_page_text=curr_text,
                previous_page_text=prev_text,
                current_page_lines=curr_lines,
                previous_page_lines=prev_lines,
                embedding_similarity=None,  # 暂时不使用嵌入向量
            )
            
            # 判定是否为延续
            result = detect_page_continuation(context)
            
            # 更新统计
            if result.is_continuation:
                continuation_count += 1
            else:
                non_continuation_count += 1
            
            # 显示结果
            status = "✓ 延续" if result.is_continuation else "✗ 不延续"
            print(f"第 {prev_page_num} 页 → 第 {curr_page_num} 页: {status}")
            print(f"  分数: {result.score} (阈值: {CONTINUATION_THRESHOLD})")
            
            # 显示判定原因（如果有）
            if result.reasons:
                print(f"  判定原因:")
                for reason in result.reasons:
                    print(f"    - {reason}")
            else:
                print(f"  判定原因: 无规则匹配")
            
            # 显示上一页的最后几行和当前页的前几行（用于调试）
            prev_last = '\n'.join(prev_lines[-3:]) if prev_lines else ""
            curr_first = '\n'.join(curr_lines[:3]) if curr_lines else ""
            
            if prev_last and curr_first:
                # 截断过长的文本
                prev_preview = prev_last[:80] + "..." if len(prev_last) > 80 else prev_last
                curr_preview = curr_first[:80] + "..." if len(curr_first) > 80 else curr_first
                print(f"  上一页结尾: {prev_preview}")
                print(f"  当前页开头: {curr_preview}")
            
            print()
        
        # 显示统计信息
        print("=" * 80)
        print("统计信息")
        print("=" * 80)
        total_judgments = continuation_count + non_continuation_count
        if total_judgments > 0:
            continuation_rate = continuation_count / total_judgments * 100
            non_continuation_rate = non_continuation_count / total_judgments * 100
            print(f"总判定次数: {total_judgments}")
            print(f"判定为延续: {continuation_count} 次 ({continuation_rate:.1f}%)")
            print(f"判定为不延续: {non_continuation_count} 次 ({non_continuation_rate:.1f}%)")
        else:
            print("没有进行任何判定")
        print()
        
    except Exception as e:
        print(f"错误: 处理 PDF 时发生异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 运行 PDF 分析
    pdf_path = project_root / "test" / "gb2760" / "GB2760-2024.pdf"
    analyze_pdf_continuation(str(pdf_path), max_pages=20)
