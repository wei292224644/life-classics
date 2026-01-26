"""
将PDF按页切分，使用pymupdf4llm.to_markdown提取每页为markdown，并使用LLM整理内容
"""

import json
import pymupdf.layout  # 必须先导入这个来激活布局功能
import pymupdf4llm
import pymupdf
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径，以便导入app模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import chat
from app.core.config import settings


def split_pdf_pages(
    pdf_path: str,
    start_page: int,
    end_page: int,
    chunks_dir: str = "chunks",
    forks_dir: str = "forks",
):
    """
    将Markdown按页切分，提取每页为markdown，并使用LLM整理内容

    Args:
        pdf_path: Markdown文件路径
        start_page: 开始页数（从1开始）
        end_page: 结束页数（包含）
        chunks_dir: 保存原始markdown的目录
        forks_dir: 保存LLM整理后内容的目录
    """
    # 转换为Path对象
    pdf_path = Path(pdf_path)
    chunks_dir = Path(chunks_dir)
    forks_dir = Path(forks_dir)

    # 创建输出目录
    chunks_dir.mkdir(parents=True, exist_ok=True)
    forks_dir.mkdir(parents=True, exist_ok=True)

    # 检查PDF文件是否存在
    if not pdf_path.exists():
        print(f"错误: 找不到PDF文件: {pdf_path}")
        return

    # 打开PDF
    doc = pymupdf.open(pdf_path)
    try:
        total_pages = len(doc)
        print(f"PDF总页数: {total_pages}")

        # 验证页数范围
        if start_page < 1:
            print(f"警告: 开始页数 {start_page} 小于1，将使用第1页")
            start_page = 1
        if end_page > total_pages:
            print(
                f"警告: 结束页数 {end_page} 超出PDF总页数 {total_pages}，将使用第{total_pages}页"
            )
            end_page = total_pages
        if start_page > end_page:
            print(f"错误: 开始页数 {start_page} 大于结束页数 {end_page}")
            return

        print(
            f"\n开始处理第 {start_page} 到 {end_page} 页，共 {end_page - start_page + 1} 页\n"
        )

        # 处理每一页
        for page_num in range(start_page, end_page + 1):
            print(f"正在处理第 {page_num} 页...")

            # 使用 pymupdf4llm.to_markdown 提取单页为 markdown
            # pymupdf4llm 使用 0-based 索引
            page_index = page_num - 1
            markdown_content = pymupdf4llm.to_markdown(
                doc, pages=[page_index], header=False, footer=False
            )

            # page = doc.load_page(page_index)

            # markdown_content = page.get_text_blocks()
            markdown_content = json.dumps(markdown_content, ensure_ascii=False)

            # 保存原始markdown到chunks目录
            chunk_file = chunks_dir / f"page_{page_num}.md"
            with open(chunk_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"  ✓ 已保存原始markdown到: {chunk_file}")

            # 使用LLM整理内容
            print(f"  正在使用LLM整理内容...")
            try:
                organized_content = organize_with_llm(markdown_content)

                # 保存整理后的内容到forks目录
                fork_file = forks_dir / f"page_{page_num}.md"
                with open(fork_file, "w", encoding="utf-8") as f:
                    f.write(organized_content)
                print(f"  ✓ 已保存整理后的内容到: {fork_file}")
            except Exception as e:
                print(f"  ❌ LLM整理失败: {e}")
                # 即使LLM失败，也保存原始内容到forks目录
                fork_file = forks_dir / f"page_{page_num}.md"
                with open(fork_file, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                print(f"  ⚠️  已保存原始内容到: {fork_file}")

        print(f"\n✅ 完成！共处理 {end_page - start_page + 1} 页")
        print(f"  原始markdown保存在: {chunks_dir}")
        print(f"  整理后的内容保存在: {forks_dir}")

    finally:
        doc.close()


def organize_with_llm(text: str) -> str:
    """
    使用LLM整理Markdown页面内容

    Args:
        text: PDF页面的markdown文本内容

    Returns:
        LLM整理后的内容
    """
    system_prompt = """你是一名资深的文档结构整理专家，擅长对由 PDF 自动转换得到的 Markdown 文档进行结构修复与规范化整理。

输入内容为：由 PDF 转换生成的 Markdown 原始文本，可能存在标题层级混乱、换行异常、列表或表格格式不规范、分页残留等问题。

仅输出整理后的 Markdown 内容，不输出任何说明、分析或附加文本
"""

    human_prompt = f"""请整理以下Markdown页面内容：

{text}
"""

    try:
        response = chat(
            messages=[
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ],
            provider_name=settings.DOCUMENT_STRUCTURE_PROVIDER,
            model=settings.DOCUMENT_STRUCTURE_MODEL,
            provider_config={"temperature": settings.DOCUMENT_STRUCTURE_TEMPERATURE},
        )
        return response
    except Exception as e:
        print(f"    LLM调用失败: {e}")
        raise


if __name__ == "__main__":
    # 获取脚本所在目录
    script_dir = Path(__file__).parent

    # PDF文件路径（相对于脚本所在目录）
    pdf_path = script_dir / "GB2760-2024.pdf"

    # 输出目录（相对于脚本所在目录）
    chunks_dir = script_dir / "chunks"
    forks_dir = script_dir / "forks"

    # 从命令行参数获取页数范围，如果没有则提示用户输入
    if len(sys.argv) >= 3:
        try:
            start_page = int(sys.argv[1])
            end_page = int(sys.argv[2])
        except ValueError:
            print("错误: 页数必须是整数")
            print("用法: python split.py [开始页数] [结束页数]")
            sys.exit(1)
    else:
        # 交互式输入
        print("PDF按页切分工具")
        print("=" * 50)
        try:
            start_page = int(input("请输入开始页数（从1开始）: "))
            end_page = int(input("请输入结束页数（包含）: "))
        except ValueError:
            print("错误: 页数必须是整数")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n已取消")
            sys.exit(0)

    # 执行切分
    split_pdf_pages(
        pdf_path=str(pdf_path),
        start_page=start_page,
        end_page=end_page,
        chunks_dir=str(chunks_dir),
        forks_dir=str(forks_dir),
    )
