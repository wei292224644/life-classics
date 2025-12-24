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
from app.core.config import settings
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

    system_prompt = """你是一名资深的【文档解析与知识工程专家】，
擅长将标准类 PDF 文档转化为可直接用于知识库（RAG / Agent / 推理系统）的结构化文本。

你将收到一份 PDF 文档内容，请严格按照以下规则解析并输出结果。

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

【content_type: <type>】

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

====================
【六、表格处理规则】
====================
1. 表格必须作为一个完整的语义块，不得拆分为多段。
2. 使用标准 Markdown 表格格式。
3. 保留表头、单位、数值、注释、来源说明。
4. 表格下方如存在“注”“说明”“备注”，必须单独保留。

====================
【七、输出格式要求】
====================
1. 使用 Markdown 作为最终输出格式。
2. 仅输出解析后的结构化内容，不输出解析过程、思考说明或免责声明。
3. 不添加总结、评价或推论性内容。
"""

    human_prompt = f"""这是 PDF 文档的内容，请按照要求进行解析：{text}"""

    try:
        print("\n正在调用LLM分析...")
        llm = get_llm("dashscope", {"model": settings.DASHSCOPE_MODEL})
        response = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
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

    # 可选：保存结果到文件
    output_file = pdf_file.stem + "_analysis.md"
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
