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


def extract_pdf_text(pdf_path: str) -> str:
    """
    从PDF中提取所有文本

    Args:
        pdf_path: PDF文件路径

    Returns:
        提取的文本内容
    """
    text_parts = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            print(f"PDF总页数: {len(pdf.pages)}")

            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    text_parts.append(f"=== 第 {page_num} 页 ===\n{text}\n")
                    print(f"  第 {page_num} 页: 提取了 {len(text)} 个字符")

            full_text = "\n".join(text_parts)
            print(f"\n总共提取了 {len(full_text)} 个字符")
            return full_text

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

    prompt = f"""你是一个“文档结构抽取助手”，你的任务是将 {standard_info} PDF 文档转换为
一种“面向法规规则抽取的中间文本格式”，用于后续自动化规则解析与知识库构建。

这是一个中间数据阶段，不是给人阅读的最终文档。

【重要约束（必须严格遵守）】

1. 不要输出 Markdown。
2. 不要使用 Markdown 表格、列表、标题层级或任何排版格式。
3. 不要总结、解释、改写或推断文档含义。
4. 不要合并内容，也不要拆分原有的结构单元。
5. 不要生成“美观”的文档，只保留结构信息。
6. 不要判断是否为规则，这一步只做结构抽取。

【你的输出将被下游程序和模型使用，而不是给人直接阅读。】

【允许使用的结构标签（只能使用以下几种）】

[SECTION] 章节标题  
[TABLE] 表格标题  
[ROW] 表格中的一行（一行 = 一个逻辑行）  
[NOTE] 注释或备注（如以“注：”开头的内容）  
[TEXT] 其他普通文本（不属于以上类型）

【输出规则】

- 每一个结构单元单独输出一行
- 不得合并多行内容
- 不得自行补充缺失信息
- [ROW] 中只包含原表格的一行原始文本
- 不要使用编号、项目符号、缩进

【输出示例】

[SECTION] 4 理化指标
[TABLE] 表2 理化指标
[ROW] 总β-胡萝卜素含量（以CH计），w/% ≥ 96.0
[ROW] 吸光度比值 A/A455 483 1.14～1.19
[ROW] 灼烧残渣，w/% ≤ 0.2
[NOTE] 注：商品化的β-胡萝卜素产品可添加符合食品添加剂质量规格要求的明胶、抗氧化剂和（或）食用植物油、糊精、淀粉。

【开始任务】

请从 PDF 内容中按上述要求抽取结构化中间文本。

{standard_info}PDF内容：
{text}
"""

    try:
        print("\n正在调用LLM分析...")
        llm = get_llm()
        response = llm.invoke([SystemMessage(content=prompt)])

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

    # Step 1: 提取PDF文本
    print("\n[Step 1] 提取PDF文本...")
    pdf_text = extract_pdf_text(str(pdf_file))

    if not pdf_text or not pdf_text.strip():
        print("错误: 未能从PDF中提取到文本")
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

    # 可选：保存结果到文件
    output_file = pdf_file.stem + "_analysis.txt"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"文件: {pdf_file.name}\n")
            f.write(f"标准编号: {standard_ref or '未知'}\n")
            f.write("=" * 60 + "\n\n")
            f.write("LLM分析结果:\n")
            f.write("=" * 60 + "\n")
            f.write(result)
        print(f"\n✓ 结果已保存到: {output_file}")
    except Exception as e:
        print(f"\n⚠ 保存结果失败: {e}")


if __name__ == "__main__":
    main()
