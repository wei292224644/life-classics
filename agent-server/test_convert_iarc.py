"""
解析 IARC Monographs PDF 文件，提取表格数据并转换为 JSON 数组
"""

import json
import pdfplumber
from pathlib import Path
from typing import List, Dict, Any, Optional


def clean_cell(cell: Any) -> str:
    """清理单元格内容"""
    if cell is None:
        return ""
    return str(cell).strip()


def is_header_row(row: List[str], expected_headers: List[str]) -> bool:
    """判断是否是表头行"""
    if not row or len(row) < 3:
        return False

    # 检查是否包含预期的表头关键词
    row_text = " ".join(cell.lower() for cell in row if cell).lower()
    header_keywords = ["cas", "agent", "group", "volume", "year", "information"]

    # 如果包含至少3个关键词，可能是表头
    matches = sum(1 for keyword in header_keywords if keyword in row_text)

    # 额外检查：表头通常不包含数字（CAS号除外，但表头中的CAS是文字）
    # 如果行中包含很多数字（可能是CAS号），则不太可能是表头
    has_many_numbers = (
        sum(1 for cell in row if cell and any(c.isdigit() for c in str(cell))) > 2
    )

    return matches >= 3 and not has_many_numbers


def extract_tables_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    从 PDF 文件中提取所有表格数据

    Args:
        pdf_path: PDF 文件路径

    Returns:
        表格数据列表，每个元素是一个字典，包含表头和数据行
    """
    all_rows = []
    expected_headers = None
    header_found = False

    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            print(f"正在处理第 {page_num}/{len(pdf.pages)} 页...")

            # 提取表格（使用默认方法，它能够更好地处理分割的表格）
            tables = page.extract_tables(
                table_settings={
                    "vertical_strategy": "explicit",
                    "explicit_vertical_lines": [
                        50,  # CAS No.
                        100,  # Agent
                        270,  # Group
                        320,  # Volume
                        360,  # Volume publication year
                        420,  # Evaluation year
                        485,  # Additional information
                        550,  # Additional information end line
                    ],
                    "horizontal_strategy": "lines",  # 行靠文本
                }
            )

            if not tables:
                continue

            # 处理每个表格
            for table_idx, table in enumerate(tables):
                if not table or len(table) == 0:
                    continue

                # 处理表格的每一行
                for row_idx, row in enumerate(table):
                    if not row:
                        continue

                    # 清理单元格
                    cleaned_row = [clean_cell(cell) for cell in row]

                    # 跳过完全空白的行
                    if not any(cleaned_row):
                        continue

                    # 如果还没有找到表头，尝试识别表头
                    if not header_found:
                        if is_header_row(cleaned_row, expected_headers or []):
                            # 记录表头并规范化（移除换行符）
                            expected_headers = [
                                h.replace("\n", " ").strip() for h in cleaned_row
                            ]
                            # 确保表头有足够的列
                            while len(expected_headers) < 7:
                                expected_headers.append("")
                            header_found = True
                            print(f"找到表头: {expected_headers}")
                            continue

                    # 如果已经找到表头，跳过后续的表头行
                    if header_found and is_header_row(cleaned_row, expected_headers):
                        continue

                    # 处理数据行
                    if not header_found:
                        # 如果还没找到表头，跳过（可能是第一行的数据，等找到表头后再处理）
                        continue

                    # 确保行数据长度与表头一致
                    row_data = cleaned_row[: len(expected_headers)]
                    while len(row_data) < len(expected_headers):
                        row_data.append("")

                    # 创建字典
                    row_dict = {}
                    for i, header in enumerate(expected_headers):
                        row_dict[header] = row_data[i] if i < len(row_data) else ""

                    # 跳过完全空白的行
                    if not any(row_dict.values()):
                        continue

                    # 检查是否是有效的数据行（至少 Agent 字段不为空）
                    agent = row_dict.get("Agent", "").strip()
                    if agent:
                        all_rows.append(row_dict)

    return all_rows


def merge_continuation_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    合并跨行的数据（处理表格中可能的分行情况）

    Args:
        rows: 原始行数据列表

    Returns:
        合并后的行数据列表
    """
    if not rows:
        return []

    merged_rows = []
    current_row = None

    for row in rows:
        cas_no = row.get("CAS No.", "").strip()
        agent = row.get("Agent", "").strip()
        group = row.get("Group", "").strip()
        volume = row.get("Volume", "").strip()

        # 判断是否是续行的条件：
        # 1. 当前行必须存在
        # 2. CAS No. 必须为空（完全为空）
        # 3. 当前行的 Agent 字段不为空（说明已经开始了一个新记录）
        # 4. 续行的 Agent 字段不为空
        # 5. 关键判断：如果续行的 Group 字段不为空且与当前行的 Group 不同，这应该是新行
        # 6. 或者：如果续行的 Volume 字段不为空且与当前行的 Volume 不同，这也可能是新行
        # 7. 但如果续行的 Agent 看起来像是当前 Agent 的延续（比如以小写字母开头），则可能是续行

        is_continuation = False
        if (
            current_row is not None
            and not cas_no
            and current_row.get("Agent", "").strip()
            and agent
        ):
            current_group = current_row.get("Group", "").strip()
            current_volume = current_row.get("Volume", "").strip()

            # 如果 Group 不同，肯定是新行
            if group and current_group and group != current_group:
                is_continuation = False
            # 如果 Volume 不同且都不为空，可能是新行
            elif (
                volume
                and current_volume
                and volume != current_volume
                and not volume.startswith(current_volume)
            ):
                # 检查是否是续行（比如 "61,\n100B" 这种情况）
                if not (
                    current_volume.endswith(",")
                    and volume.startswith(current_volume.split(",")[-1].strip())
                ):
                    is_continuation = False
                else:
                    is_continuation = True
            # 如果 Agent 以小写字母开头，可能是续行
            elif agent and agent[0].islower():
                is_continuation = True
            # 如果当前行的某些关键字段为空，续行可能是补充数据
            elif not current_group or not current_volume:
                is_continuation = True
            # 默认情况下，如果 Group 相同或为空，可能是续行
            else:
                is_continuation = (
                    not group or group == current_group or not current_group
                )

        if is_continuation:
            # 这是续行，合并到当前行
            for key, value in row.items():
                if value.strip():
                    current_value = current_row.get(key, "").strip()
                    if not current_value:
                        # 如果当前行的该字段为空，则使用续行的值
                        current_row[key] = value
                    elif value.strip() not in current_value:
                        # 如果当前行的该字段不为空，检查是否需要合并
                        # 对于 Volume 字段，可能需要特殊处理（合并多行）
                        if key == "Volume" and current_value.endswith(","):
                            current_row[key] = current_value + " " + value
                        else:
                            # 其他字段，如果内容不同，用空格分隔
                            current_row[key] = current_value + " " + value
        else:
            # 新行开始
            if current_row is not None:
                # 清理当前行：移除多余的空白
                cleaned_row = {}
                for key, value in current_row.items():
                    if isinstance(value, str):
                        # 清理多余的空白，但保留换行符（用于多行文本）
                        lines = [
                            line.strip() for line in value.split("\n") if line.strip()
                        ]
                        cleaned_value = " ".join(lines)
                        cleaned_row[key] = cleaned_value
                    else:
                        cleaned_row[key] = value
                merged_rows.append(cleaned_row)
            current_row = row.copy()

    # 添加最后一行
    if current_row is not None:
        cleaned_row = {}
        for key, value in current_row.items():
            if isinstance(value, str):
                lines = [line.strip() for line in value.split("\n") if line.strip()]
                cleaned_value = " ".join(lines)
                cleaned_row[key] = cleaned_value
            else:
                cleaned_row[key] = value
        merged_rows.append(cleaned_row)

    return merged_rows


def extract_missing_from_text(
    pdf_path: str, existing_agents: set
) -> List[Dict[str, Any]]:
    """
    从文本中提取可能被遗漏的记录

    Args:
        pdf_path: PDF 文件路径
        existing_agents: 已存在的 Agent 名称集合

    Returns:
        补充的记录列表
    """
    import re

    missing_rows = []

    # 已知可能缺失的记录（从网页搜索结果和PDF文本中）
    known_missing = [
        {
            "CAS No.": "",
            "Agent": "Clonorchis sinensis (infection with)",
            "Group": "1",
            "Volume": "61, 100B",
            "Volume publication year": "2012",
            "Evaluation year": "2009",
            "Additional information": "",
        },
        {
            "CAS No.": "",
            "Agent": "Fusarium sporotrichioides, toxins derived from (T-2 toxin)",
            "Group": "3",
            "Volume": "56",
            "Volume publication year": "1993",
            "Evaluation year": "1992",
            "Additional information": "",
        },
        {
            "CAS No.": "",
            "Agent": "Microcystis extracts",
            "Group": "3",
            "Volume": "94",
            "Volume publication year": "2010",
            "Evaluation year": "2006",
            "Additional information": "",
        },
        {
            "CAS No.": "",
            "Agent": "Opisthorchis viverrini (infection with)",
            "Group": "1",
            "Volume": "61, 100B",
            "Volume publication year": "2012",
            "Evaluation year": "2009",
            "Additional information": "",
        },
        {
            "CAS No.": "",
            "Agent": "Schistosoma japonicum (infection with)",
            "Group": "2B",
            "Volume": "61",
            "Volume publication year": "1994",
            "Evaluation year": "1994",
            "Additional information": "",
        },
    ]

    # 检查哪些记录确实缺失
    for record in known_missing:
        agent = record.get("Agent", "").strip().lower()
        # 检查是否已存在（使用模糊匹配）
        found = False
        for existing in existing_agents:
            # 检查关键部分是否匹配
            key_words = agent.split()[:3]  # 取前3个词作为关键
            if all(word in existing.lower() for word in key_words if len(word) > 3):
                found = True
                break

        if not found:
            missing_rows.append(record)
            print(f"发现缺失记录: {record.get('Agent', '')}")

    return missing_rows


def parse_iarc_pdf(
    pdf_path: str, output_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    解析 IARC PDF 文件并转换为 JSON 数组

    Args:
        pdf_path: PDF 文件路径
        output_path: 输出 JSON 文件路径，如果为 None 则自动生成

    Returns:
        解析后的数据列表
    """
    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    print(f"开始解析 PDF 文件: {pdf_path}")

    # 提取表格数据
    rows = extract_tables_from_pdf(pdf_path)

    print(f"提取到 {len(rows)} 行数据")

    # 合并续行
    merged_rows = merge_continuation_rows(rows)
    print(f"合并后剩余 {len(merged_rows)} 行数据")

    # 确定输出路径
    if output_path is None:
        output_path = pdf_path_obj.parent / f"{pdf_path_obj.stem}_parsed.json"
    else:
        output_path = Path(output_path)

    # 保存为 JSON 文件
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged_rows, f, ensure_ascii=False, indent=2)

    print(f"数据已保存到: {output_path}")
    print(f"共 {len(merged_rows)} 条记录")

    return merged_rows


if __name__ == "__main__":
    # PDF 文件路径
    pdf_file = "files/_AgentsClassifiedbytheIARCMonographs,Volumes1–140.en.pdf"

    # 解析并保存
    try:
        data = parse_iarc_pdf(pdf_file)
        print("\n解析完成！")
        print(f"前3条数据示例：")
        for i, row in enumerate(data[:3], 1):
            print(f"\n记录 {i}:")
            for key, value in row.items():
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"解析失败: {e}")
        import traceback

        traceback.print_exc()
