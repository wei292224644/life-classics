"""
法规文档处理脚本

用于处理PDF文档，提取规范性规则和问答对。

使用方法:
    python process_regulatory_document.py files/20120518_10.pdf
    python process_regulatory_document.py files/ --output results.json
"""

import json
import sys
import re
from pathlib import Path
from typing import Optional, Dict, Any
from app.core.pdf_structure_extractor import pdf_structure_extractor
from app.core.regulatory_semantic_analyzer import RegulatorySemanticAnalyzer


def extract_standard_ref(file_path: str) -> Optional[str]:
    """
    从文件路径、文件名或PDF内容中提取标准编号

    Args:
        file_path: 文件路径

    Returns:
        标准编号（如 "GB 28310-2012"）或None
    """
    file_name = Path(file_path).name

    # 匹配标准编号模式（支持中文破折号"—"和英文连字符"-"）
    patterns = [
        r"GB\s*[/T]?\s*\d+[—\-]\d{4}",  # GB 28310-2012 或 GB 28310—2012
        r"GB\s*[/T]?\s*\d+\s+\d{4}",  # GB 28310 2012 (空格分隔)
        r"NY\s*\d+[—\-]\d{4}",  # NY 1234-2020
        r"QB\s*\d+[—\-]\d{4}",  # QB 1234-2020
    ]

    # 1. 先从文件名中提取
    for pattern in patterns:
        match = re.search(pattern, file_name, re.IGNORECASE)
        if match:
            standard_ref = match.group(0).strip()
            # 将中文破折号替换为英文连字符，统一格式
            standard_ref = standard_ref.replace("—", "-")
            return standard_ref

    # 2. 如果文件名中没有，尝试从PDF内容中提取
    try:
        import pdfplumber

        with pdfplumber.open(file_path) as pdf:
            # 只检查前3页（标准编号通常在封面或前几页）
            pages_to_check = min(3, len(pdf.pages))
            found_refs = []

            for page_num in range(pages_to_check):
                page = pdf.pages[page_num]
                text = page.extract_text()
                if not text:
                    continue

                # 在文本中查找标准编号
                for pattern in patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        standard_ref = match.group(0).strip()
                        # 将中文破折号替换为英文连字符，统一格式
                        standard_ref = standard_ref.replace("—", "-")
                        # 记录找到的位置和页码
                        found_refs.append(
                            {
                                "ref": standard_ref,
                                "page": page_num,
                                "position": match.start(),
                                "text_length": len(text),
                            }
                        )

                # 也尝试查找"标准编号"、"标准号"等关键词附近的标准编号
                standard_keywords = [
                    r"标准编号[：:]\s*",
                    r"标准号[：:]\s*",
                    r"标准[：:]\s*",
                    r"Standard[：:]\s*",
                ]
                for keyword_pattern in standard_keywords:
                    keyword_match = re.search(keyword_pattern, text, re.IGNORECASE)
                    if keyword_match:
                        # 在关键词后查找标准编号
                        start_pos = keyword_match.end()
                        remaining_text = text[
                            start_pos : start_pos + 50
                        ]  # 检查关键词后50个字符
                        for pattern in patterns:
                            match = re.search(pattern, remaining_text, re.IGNORECASE)
                            if match:
                                standard_ref = match.group(0).strip()
                                standard_ref = standard_ref.replace("—", "-")
                                return standard_ref

            # 如果找到多个标准编号，优先选择：
            # 1. 第一页的
            # 2. 文本开头的（前30%）
            if found_refs:
                # 优先第一页
                first_page_refs = [r for r in found_refs if r["page"] == 0]
                if first_page_refs:
                    # 在第一页中，优先选择位置靠前的
                    first_page_refs.sort(key=lambda x: x["position"])
                    return first_page_refs[0]["ref"]
                # 否则返回第一个找到的
                return found_refs[0]["ref"]

    except Exception as e:
        print(f"  警告: 从PDF内容提取标准编号失败: {e}")

    return None


def process_pdf_file(
    file_path: str, output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理单个PDF文件

    Args:
        file_path: PDF文件路径
        output_file: 输出文件路径（可选，如果提供则保存JSON结果）

    Returns:
        处理结果字典
    """
    print(f"\n{'='*60}")
    print(f"处理文件: {file_path}")
    print(f"{'='*60}\n")

    # 提取标准编号
    standard_ref = extract_standard_ref(file_path)
    if not standard_ref:
        print("⚠️  未能从文件名提取标准编号，使用默认值")
        standard_ref = "未知标准"
    else:
        print(f"✓ 提取到标准编号: {standard_ref}")

    try:
        # Step 1: 提取结构单元
        print("\n[Step 1] 提取结构单元...")
        units = pdf_structure_extractor.extract_structure(file_path)
        print(f"  ✓ 提取了 {len(units)} 个结构单元")

        if not units:
            return {
                "file_path": file_path,
                "standard_ref": standard_ref,
                "success": False,
                "error": "未能提取到结构单元",
                "units_count": 0,
                "rules_count": 0,
                "qas_count": 0,
                "ignored_count": 0,
            }

        # 显示结构单元统计
        unit_types = {}
        for unit in units:
            unit_types[unit.unit_type] = unit_types.get(unit.unit_type, 0) + 1
        print(f"  结构单元类型分布: {unit_types}")

        # Step 2: 法规语义解析
        print("\n[Step 2] 法规语义解析...")
        analyzer = RegulatorySemanticAnalyzer(standard_ref=standard_ref)
        results = analyzer.analyze_units(units)

        rules = results["rules"]
        qas = results["qas"]
        ignored_count = results["ignored_count"]

        print(f"  ✓ 提取了 {len(rules)} 条规范性规则")
        print(f"  ✓ 生成了 {len(qas)} 个问答对")
        print(f"  ✓ 忽略了 {ignored_count} 个结构单元")

        # 构建结果
        result = {
            "file_path": file_path,
            "standard_ref": standard_ref,
            "success": True,
            "error": None,
            "units_count": len(units),
            "rules_count": len(rules),
            "qas_count": len(qas),
            "ignored_count": ignored_count,
            "rules": [
                {
                    "document": rule.document,
                    "item": rule.item,
                    "limit_type": rule.limit_type,
                    "limit_value": rule.limit_value,
                    "unit": rule.unit,
                    "condition": rule.condition,
                    "standard_ref": rule.standard_ref,
                }
                for rule in rules
            ],
            "qas": [
                {
                    "question": qa.question,
                    "answer": qa.answer,
                    "standard_ref": qa.standard_ref,
                }
                for qa in qas
            ],
        }

        # 保存结果
        if output_file:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n✓ 结果已保存到: {output_file}")

        # 显示示例
        if rules:
            print("\n[示例规则]")
            for i, rule in enumerate(rules[:3], 1):
                print(f"  {i}. {rule.document}")
                print(
                    f"     约束对象: {rule.item}, 类型: {rule.limit_type}, 值: {rule.limit_value}, 单位: {rule.unit}"
                )

        if qas:
            print("\n[示例问答]")
            for i, qa in enumerate(qas[:3], 1):
                print(f"  {i}. Q: {qa.question}")
                print(f"     A: {qa.answer[:100]}...")

        return result

    except Exception as e:
        import traceback

        error_msg = f"处理文件失败: {str(e)}\n{traceback.format_exc()}"
        print(f"\n✗ {error_msg}")
        return {
            "file_path": file_path,
            "standard_ref": standard_ref,
            "success": False,
            "error": error_msg,
            "units_count": 0,
            "rules_count": 0,
            "qas_count": 0,
            "ignored_count": 0,
        }


def process_directory(
    directory_path: str, output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理目录中的所有PDF文件

    Args:
        directory_path: 目录路径
        output_file: 输出文件路径（可选）

    Returns:
        处理结果汇总
    """
    directory = Path(directory_path)
    pdf_files = list(directory.rglob("*.pdf"))

    if not pdf_files:
        print(f"在目录 {directory_path} 中未找到PDF文件")
        return {
            "total_files": 0,
            "success_files": 0,
            "failed_files": 0,
            "total_rules": 0,
            "total_qas": 0,
            "results": [],
        }

    print(f"找到 {len(pdf_files)} 个PDF文件")

    results = []
    total_rules = 0
    total_qas = 0

    for pdf_file in pdf_files:
        result = process_pdf_file(str(pdf_file))
        results.append(result)

        if result["success"]:
            total_rules += result["rules_count"]
            total_qas += result["qas_count"]

    success_count = sum(1 for r in results if r["success"])
    failed_count = len(results) - success_count

    summary = {
        "total_files": len(pdf_files),
        "success_files": success_count,
        "failed_files": failed_count,
        "total_rules": total_rules,
        "total_qas": total_qas,
        "results": results,
    }

    # 保存汇总结果
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(f"\n✓ 汇总结果已保存到: {output_file}")

    # 显示汇总
    print(f"\n{'='*60}")
    print(f"处理完成")
    print(f"{'='*60}")
    print(f"总文件数: {len(pdf_files)}")
    print(f"成功: {success_count}")
    print(f"失败: {failed_count}")
    print(f"总规则数: {total_rules}")
    print(f"总问答数: {total_qas}")
    print(f"{'='*60}\n")

    return summary


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python process_regulatory_document.py <文件路径或目录> [输出文件]")
        print("\n示例:")
        print("  python process_regulatory_document.py files/20120518_10.pdf")
        print(
            "  python process_regulatory_document.py files/20120518_10.pdf results.json"
        )
        print("  python process_regulatory_document.py files/ --output results.json")
        sys.exit(1)

    input_path = sys.argv[1]
    output_file = None

    # 解析输出文件参数
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    elif len(sys.argv) > 2 and not sys.argv[2].startswith("--"):
        output_file = sys.argv[2]

    input_path_obj = Path(input_path)

    if input_path_obj.is_file():
        # 处理单个文件
        process_pdf_file(input_path, output_file)
    elif input_path_obj.is_dir():
        # 处理目录
        process_directory(input_path, output_file)
    else:
        print(f"错误: 路径不存在: {input_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
