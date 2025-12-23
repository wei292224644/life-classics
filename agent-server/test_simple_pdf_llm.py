#!/usr/bin/env python3
"""
最简单的PDF解析和LLM处理实验

功能：
1. 将PDF解析成字符串
2. 将字符串传给LLM
3. 让LLM解析PDF内容
"""

import sys
from pathlib import Path
import pdfplumber
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm import get_llm
from process_regulatory_document import extract_standard_ref


def extract_pdf_text(pdf_path: str, page_num: int = 1) -> str:
    """
    从PDF中提取指定页面的文本

    Args:
        pdf_path: PDF文件路径
        page_num: 页码（从1开始，默认第1页）

    Returns:
        提取的文本内容
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"PDF总页数: {total_pages}")
            
            if page_num < 1 or page_num > total_pages:
                print(f"错误: 页码 {page_num} 超出范围（1-{total_pages}）")
                return ""
            
            # 只提取第一页
            page = pdf.pages[page_num - 1]
            text = page.extract_text()
            
            if text:
                print(f"  第 {page_num} 页: 提取了 {len(text)} 个字符")
                return text
            else:
                print(f"  第 {page_num} 页: 未能提取到文本")
                return ""

    except Exception as e:
        print(f"PDF解析失败: {e}")
        import traceback

        traceback.print_exc()
        return ""


def analyze_with_llm(text: str, standard_ref: str = None) -> str:
    """
    使用LLM分析PDF文本

    Args:
        text: PDF文本内容
        standard_ref: 标准编号（可选）

    Returns:
        LLM的分析结果
    """
    # 限制文本长度（避免超出token限制）
    max_length = 8000  # 可以根据模型调整
    if len(text) > max_length:
        print(f"\n⚠️  文本过长（{len(text)}字符），截取前{max_length}字符")
        text = text[:max_length] + "\n\n[文本已截断...]"

    # 构建prompt
    standard_info = f"\n标准编号: {standard_ref}\n" if standard_ref else ""

    prompt = f"""你将收到一个国家食品安全标准 PDF 的文本内容（可能存在分页、中断、页眉页脚）。

你的任务是将其转换为“结构化文本”，要求如下：

【基本规则】
1. 不进行总结、解释或推理，不引入任何原文中不存在的信息。
2. 严格保持原文语义与数值，不允许改写数值、单位、化学名称。
3. 删除页眉、页脚、页码、重复的页标题。
4. 合并被分页或换行打断的连续语句。
5. 表格内的内容，去掉\n换行符。保证表格内的内容是连续的。

【结构规则】
5. 识别并保留章节结构，使用以下标签表示：
   - <section level="1"> 一级章节标题 </section>
   - <section level="2"> 二级章节标题 </section>
   - <section level="3"> 三级章节标题 </section>

6. 正文内容使用 <p> 标签包裹。

7. 表格使用如下结构表示，不使用 Markdown 表格：
   <table>
     <row>
       <col>列名1</col>
       <col>列名2</col>
     </row>
     <row>
       <col>值1</col>
       <col>值2</col>
     </row>
   </table>

【输出要求】
8. 输出为纯文本结构化内容，不使用 Markdown 语法。
9. 保留原文中的公式、单位、化学式。
10. 要求输出完整内容，不要只输出结构化框架。


以下为PDF原文内容：
{text}
 
"""

    try:
        print("\n正在调用LLM分析...")
        llm = get_llm()
        response = llm.invoke([HumanMessage(content=prompt)])

        if hasattr(response, "content"):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    except Exception as e:
        print(f"LLM调用失败: {e}")
        import traceback

        traceback.print_exc()
        return f"错误: {str(e)}"


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python test_simple_pdf_llm.py <PDF文件路径>")
        print("\n示例:")
        print("  python test_simple_pdf_llm.py files/20120518_10.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    pdf_file = Path(pdf_path)

    if not pdf_file.exists():
        print(f"错误: 文件不存在: {pdf_path}")
        sys.exit(1)

    if not pdf_file.suffix.lower() == ".pdf":
        print(f"错误: 不是PDF文件: {pdf_path}")
        sys.exit(1)

    print("=" * 60)
    print(f"处理文件: {pdf_file.name}")
    print("=" * 60)

    # Step 1: 提取PDF第一页文本
    print("\n[Step 1] 提取PDF第一页文本...")
    pdf_text = extract_pdf_text(str(pdf_file), page_num=2)

    if not pdf_text or not pdf_text.strip():
        print("错误: 未能从PDF第一页提取到文本")
        sys.exit(1)

    # Step 2: 提取标准编号（可选）
    print("\n[Step 2] 提取标准编号...")
    standard_ref = extract_standard_ref(str(pdf_file))
    if standard_ref:
        print(f"  ✓ 提取到标准编号: {standard_ref}")
    else:
        print("  ⚠ 未能提取到标准编号")

    # Step 3: 使用LLM分析
    print("\n[Step 3] 使用LLM分析PDF内容...")
    result = analyze_with_llm(pdf_text, standard_ref)

    # Step 4: 输出结果
    print("\n" + "=" * 60)
    print("LLM分析结果:")
    print("=" * 60)
    print(result)
    print("=" * 60)

    # 保存结果到Markdown文件
    output_file = pdf_file.stem + "_page1.md"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# {pdf_file.name} - 第一页结构化内容\n\n")
            f.write(f"**标准编号**: {standard_ref or '未知'}\n\n")
            f.write("---\n\n")
            f.write(result)
        print(f"\n✓ 结果已保存到: {output_file}")
    except Exception as e:
        print(f"\n⚠ 保存结果失败: {e}")


if __name__ == "__main__":
    main()
