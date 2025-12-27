#!/usr/bin/env python3
"""
解析 IARC Cancer Site PDF 文件，提取按癌症部位分类的致癌物质数据并转换为 JSON

PDF 结构：
- 表格包含三列：
  1. Cancer site（癌症部位）
  2. Carcinogenic agents with sufficient evidence in humans（有充分证据的致癌物质）
  3. Agents with limited evidence in humans（有有限证据的致癌物质）
"""

import json
import re
import pdfplumber
from pathlib import Path
from typing import List, Dict, Any, Optional


def clean_text(text: Any) -> str:
    """清理文本内容"""
    if text is None:
        return ""
    if isinstance(text, (int, float)):
        return str(text)
    return str(text).strip()


def split_agents(text: str) -> List[str]:
    """
    将致癌物质文本分割成多个独立的项目

    规则：
    1. 如果在一行内（没有换行符），一定是一个 Agent
    2. 如果换行了：
       - 如果有缩进（行首有空格或制表符），那么一定和上一个 Agent 是一体的（续行）
       - 如果首字母是大写，那么一定是一个新的 Agent
    """
    if not text:
        return []

    # 检查是否包含换行符
    if "\n" not in text:
        # 如果在一行内，一定是一个 Agent
        text = text.strip()
        return [text] if text else []

    # 如果有换行，按行处理
    lines = text.split("\n")
    agents = []
    current_agent = None

    for line in lines:
        # 检查是否有缩进（行首有空格或制表符）
        has_indent = line and (line[0] == " " or line[0] == "\t")

        # 去除首尾空白，但保留用于判断缩进的信息
        stripped_line = line.strip()

        if not stripped_line:
            continue

        # 检查首字母是否大写
        first_char_upper = stripped_line and stripped_line[0].isupper()

        # 判断是否是续行
        is_continuation = has_indent

        if is_continuation and current_agent is not None:
            # 有缩进，是续行，合并到当前 Agent
            current_agent = current_agent + " " + stripped_line
        elif first_char_upper:
            # 首字母大写，是新 Agent
            # 保存之前的 Agent
            if current_agent is not None:
                agents.append(current_agent)
            # 开始新 Agent
            current_agent = stripped_line
        else:
            # 首字母不是大写，但有换行，可能是续行（没有缩进但以小写开头）
            # 根据规则，这种情况应该也是续行
            if current_agent is not None:
                current_agent = current_agent + " " + stripped_line
            else:
                # 如果没有当前 Agent，即使首字母小写也作为新 Agent
                current_agent = stripped_line

    # 添加最后一个 Agent
    if current_agent is not None:
        agents.append(current_agent)

    # 清理和去重
    cleaned_agents = []
    seen = set()
    for agent in agents:
        agent = agent.strip()
        if agent and agent not in seen:
            cleaned_agents.append(agent)
            seen.add(agent)

    return cleaned_agents


def parse_cancer_site_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    从 PDF 文件中提取癌症部位和致癌物质数据

    Args:
        pdf_path: PDF 文件路径

    Returns:
        解析后的数据列表，每个元素包含癌症部位和对应的致癌物质
    """
    results = []

    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF 总页数: {len(pdf.pages)}")

        current_cancer_site = None
        current_sufficient_agents = []
        current_limited_agents = []

        for page_num, page in enumerate(pdf.pages, start=1):
            print(f"正在处理第 {page_num} 页...")

            # 提取表格
            tables = page.extract_tables()

            if not tables:
                # 如果没有表格，尝试提取文本
                text = page.extract_text()
                if text:
                    # 可以在这里处理纯文本内容
                    continue
                continue

            # 处理每个表格
            for table in tables:
                if not table or len(table) == 0:
                    continue

                # 跳过表头行（通常第一行或包含 "Cancer site" 的行）
                start_idx = 0
                for i, row in enumerate(table):
                    if row and len(row) >= 3:
                        row_text = " ".join(str(cell) for cell in row if cell).lower()
                        if (
                            "cancer site" in row_text
                            or "carcinogenic agents" in row_text
                        ):
                            start_idx = i + 1
                            break

                # 处理数据行
                for row_idx in range(start_idx, len(table)):
                    row = table[row_idx]
                    if not row or len(row) < 3:
                        continue

                    # 清理单元格
                    cancer_site = clean_text(row[0])
                    sufficient_agents = clean_text(row[1])
                    limited_agents = clean_text(row[2])

                    # 如果癌症部位不为空，开始新的记录
                    if cancer_site:
                        # 保存之前的记录（如果有）
                        if current_cancer_site:
                            results.append(
                                {
                                    "cancer_site": current_cancer_site,
                                    "sufficient_evidence_agents": current_sufficient_agents,
                                    "limited_evidence_agents": current_limited_agents,
                                }
                            )

                        # 开始新记录
                        current_cancer_site = cancer_site
                        current_sufficient_agents = []
                        current_limited_agents = []

                        # 如果同一行有致癌物质数据，添加到列表中
                        if sufficient_agents:
                            agents = split_agents(sufficient_agents)
                            current_sufficient_agents.extend(agents)

                        if limited_agents:
                            agents = split_agents(limited_agents)
                            current_limited_agents.extend(agents)
                    else:
                        # 这是续行，添加到当前记录
                        if sufficient_agents:
                            agents = split_agents(sufficient_agents)
                            current_sufficient_agents.extend(agents)

                        if limited_agents:
                            agents = split_agents(limited_agents)
                            current_limited_agents.extend(agents)

        # 保存最后一条记录
        if current_cancer_site:
            results.append(
                {
                    "cancer_site": current_cancer_site,
                    "sufficient_evidence_agents": current_sufficient_agents,
                    "limited_evidence_agents": current_limited_agents,
                }
            )

    return results


def parse_cancer_site_pdf_advanced(pdf_path: str) -> List[Dict[str, Any]]:
    """
    使用更高级的方法解析 PDF，处理复杂的表格结构

    Args:
        pdf_path: PDF 文件路径

    Returns:
        解析后的数据列表
    """
    results = []

    with pdfplumber.open(pdf_path) as pdf:
        print(f"PDF 总页数: {len(pdf.pages)}")

        current_cancer_site = None
        current_sufficient_agents = []
        current_limited_agents = []
        is_first_data_row_in_table = False  # 标记是否是新表的第一行数据

        for page_num, page in enumerate(pdf.pages, start=1):
            print(f"正在处理第 {page_num} 页...")

            # 提取表格，使用默认设置
            tables = page.extract_tables()

            if not tables:
                # 尝试使用文本提取作为备选方案
                text = page.extract_text()
                if text:
                    # 可以在这里添加文本解析逻辑
                    pass
                continue

            # 处理每个表格
            for table_idx, table in enumerate(tables):
                if not table or len(table) == 0:
                    continue

                # 查找表头
                header_row_idx = -1
                for i, row in enumerate(table):
                    if row and len(row) >= 3:
                        row_text = " ".join(str(cell) for cell in row if cell).lower()
                        if (
                            "cancer site" in row_text
                            or "list of classifications" in row_text
                        ):
                            header_row_idx = i
                            break

                # 从表头之后开始处理数据
                start_idx = header_row_idx + 1 if header_row_idx >= 0 else 0

                # 标记这是新表的第一行数据
                is_first_data_row_in_table = True

                for row_idx in range(start_idx, len(table)):
                    row = table[row_idx]
                    if not row:
                        continue

                    # 确保行有足够的列
                    while len(row) < 3:
                        row.append(None)

                    cancer_site = clean_text(row[0])
                    sufficient_agents = clean_text(row[1])
                    limited_agents = clean_text(row[2])

                    # 跳过完全空白的行
                    if not cancer_site and not sufficient_agents and not limited_agents:
                        continue

                    # 跳过标题行
                    if cancer_site and cancer_site.lower() in [
                        "cancer site",
                        "carcinogenic agents",
                    ]:
                        continue

                    # 特殊处理：如果是新表的第一行数据，且 Cancer site 为空，合并到上一行
                    if is_first_data_row_in_table and not cancer_site:
                        # 这是上一张表遗留的数据，合并到上一行
                        if current_cancer_site:
                            # 合并到上一行
                            if sufficient_agents:
                                agents = split_agents(sufficient_agents)
                                current_sufficient_agents.extend(agents)

                            if limited_agents:
                                agents = split_agents(limited_agents)
                                current_limited_agents.extend(agents)

                            # 标记已处理，不再作为新记录
                            is_first_data_row_in_table = False
                            continue

                    # 如果癌症部位不为空，开始新记录
                    if cancer_site:
                        # 保存之前的记录
                        if current_cancer_site:
                            results.append(
                                {
                                    "cancer_site": current_cancer_site,
                                    "sufficient_evidence_agents": current_sufficient_agents,
                                    "limited_evidence_agents": current_limited_agents,
                                }
                            )

                        # 开始新记录
                        current_cancer_site = cancer_site
                        current_sufficient_agents = []
                        current_limited_agents = []

                        # 添加当前行的数据
                        if sufficient_agents:
                            agents = split_agents(sufficient_agents)
                            current_sufficient_agents.extend(agents)

                        if limited_agents:
                            agents = split_agents(limited_agents)
                            current_limited_agents.extend(agents)

                        # 标记已处理第一行
                        is_first_data_row_in_table = False
                    else:
                        # 续行，添加到当前记录
                        if sufficient_agents:
                            agents = split_agents(sufficient_agents)
                            current_sufficient_agents.extend(agents)

                        if limited_agents:
                            agents = split_agents(limited_agents)
                            current_limited_agents.extend(agents)

                        # 标记已处理第一行
                        is_first_data_row_in_table = False

        # 保存最后一条记录
        if current_cancer_site:
            results.append(
                {
                    "cancer_site": current_cancer_site,
                    "sufficient_evidence_agents": current_sufficient_agents,
                    "limited_evidence_agents": current_limited_agents,
                }
            )

    return results


def save_to_json(data: List[Dict[str, Any]], output_path: str):
    """保存数据到 JSON 文件"""
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n数据已保存到: {output_path}")
    print(f"共 {len(data)} 条记录")


def main():
    """主函数"""
    pdf_path = "tools/iarc_cancer_site.pdf"
    output_path = "tools/iarc_cancer_site.json"

    pdf_path_obj = Path(pdf_path)
    if not pdf_path_obj.exists():
        print(f"错误: PDF 文件不存在: {pdf_path}")
        return

    print(f"开始解析 PDF 文件: {pdf_path}")

    try:
        # 首先尝试高级解析方法
        data = parse_cancer_site_pdf_advanced(pdf_path)

        if not data or len(data) == 0:
            print("高级解析方法未提取到数据，尝试基础方法...")
            data = parse_cancer_site_pdf(pdf_path)

        if not data:
            print("警告: 未能提取到任何数据")
            return

        print(f"\n成功提取 {len(data)} 条记录")

        # 过滤掉两个列表都为空的记录，以及以 "© IARC 2025" 开头的记录
        filtered_data = [
            record
            for record in data
            if not (record.get("cancer_site", "").startswith("© IARC 2025"))
            and  not (record.get("cancer_site", "").startswith("IARC, 25 avenue"))
        ]

        empty_count = len(
            [
                r
                for r in data
                if not (
                    r.get("sufficient_evidence_agents")
                    or r.get("limited_evidence_agents")
                )
            ]
        )
        copyright_count = len(
            [r for r in data if r.get("cancer_site", "").startswith("© IARC 2025")]
        )
        print(
            f"过滤后剩余 {len(filtered_data)} 条记录（已忽略 {empty_count} 条空记录，{copyright_count} 条版权信息记录）"
        )

        # 显示前几条记录作为示例
        print("\n前3条记录示例:")
        for i, record in enumerate(filtered_data[:3], 1):
            print(f"\n记录 {i}:")
            print(f"  癌症部位: {record['cancer_site']}")
            print(
                f"  充分证据的致癌物质数量: {len(record['sufficient_evidence_agents'])}"
            )
            print(f"  有限证据的致癌物质数量: {len(record['limited_evidence_agents'])}")
            if record["sufficient_evidence_agents"]:
                print(f"  示例（充分证据）: {record['sufficient_evidence_agents'][0]}")
            if record["limited_evidence_agents"]:
                print(f"  示例（有限证据）: {record['limited_evidence_agents'][0]}")

        # 保存到 JSON
        save_to_json(filtered_data, output_path)

        print("\n解析完成！")

    except Exception as e:
        print(f"解析失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
