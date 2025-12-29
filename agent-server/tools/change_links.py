"""
解析 iarc.json 文件中的 Agent 字段，提取 see 后面的链接
"""

import json
import re
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import chat


def remove_see_from_agent(agent_text: str) -> str:
    """
    从 Agent 字段中移除 see 或 see also 及其后面的内容

    Args:
        agent_text: Agent 字段的文本内容

    Returns:
        清理后的 Agent 文本
    """
    if not agent_text:
        return agent_text

    # 模式1: 移除 (see ...) 或 (see also ...)
    # 匹配括号内的 see 或 see also，移除整个括号
    pattern1 = r"\(see\s+(?:also\s+)?[^)]+\)"
    cleaned_text = re.sub(pattern1, "", agent_text, flags=re.IGNORECASE)

    # 模式2: 移除 , see ... 或 see ... (没有括号)
    # 找到不在括号内的 see，移除从 see 开始到末尾的内容
    paren_depth = 0
    see_pos = -1

    for i, char in enumerate(cleaned_text):
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
        elif paren_depth == 0:
            # 在括号外部，检查是否是 see
            remaining = cleaned_text[i:]
            # 检查是否是 "see " 或 ", see " 或开头是 "see "
            if (
                i == 0 or cleaned_text[i - 1] == "," or cleaned_text[i - 1] == " "
            ) and remaining.lower().startswith("see "):
                # 找到 see 的位置，移除从 see 开始到末尾的内容
                # 如果前面有逗号，也要移除逗号和前面的空格
                if i > 0 and cleaned_text[i - 1] == ",":
                    # 找到逗号前的位置
                    comma_pos = i - 1
                    # 移除逗号前的空格（如果有）
                    while comma_pos > 0 and cleaned_text[comma_pos - 1] == " ":
                        comma_pos -= 1
                    cleaned_text = cleaned_text[:comma_pos].rstrip()
                else:
                    cleaned_text = cleaned_text[:i].rstrip()
                break

    # 清理多余的空格和标点
    cleaned_text = cleaned_text.strip()
    # 移除末尾的逗号
    cleaned_text = re.sub(r",\s*$", "", cleaned_text)
    cleaned_text = cleaned_text.strip()

    return cleaned_text


def extract_links_from_agent(
    agent_text: str, agent_set: set = None
) -> List[Dict[str, str]]:
    """
    从 Agent 字段中提取 see 后面的链接，并标识链接类型

    Args:
        agent_text: Agent 字段的文本内容
        agent_set: 所有 Agent 名称的集合，用于验证拆分后的链接是否存在

    Returns:
        链接字典列表，每个字典包含 'link' 和 'type' 字段
        type 可以是 'see' 或 'see_also'
        如果没有找到则返回空列表
    """
    if not agent_text:
        return []

    links = []
    link_text = None
    link_type = None  # 'see' 或 'see_also'

    # 模式1: (see ...) 或 (see_also ...)
    # 匹配括号内的 see 或 see_also
    pattern1 = r"\(see\s+(also\s+)?([^)]+)\)"
    match1 = re.search(pattern1, agent_text, re.IGNORECASE)
    if match1:
        link_type = "see_also" if match1.group(1) else "see"
        link_text = match1.group(2)
    else:
        # 模式2: , see ... 或  see ... (没有括号)
        # 匹配不在括号内的 see（在逗号后或字符串开头）
        # 使用更精确的正则表达式：找到不在括号内的 see
        # 方法：找到所有 see 的位置，检查是否在括号内
        paren_depth = 0
        see_match = None

        for i, char in enumerate(agent_text):
            if char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
            elif paren_depth == 0:
                # 在括号外部，检查是否是 see
                remaining = agent_text[i:]
                # 检查是否是 "see " 或 ", see " 或开头是 "see "
                if (
                    i == 0 or agent_text[i - 1] == "," or agent_text[i - 1] == " "
                ) and remaining.lower().startswith("see "):
                    # 提取 see 后面的内容
                    if remaining.lower().startswith("see also "):
                        link_type = "see_also"
                        link_text = remaining[9:].strip()
                    else:
                        link_type = "see"
                        link_text = remaining[4:].strip()
                    see_match = True
                    break

        if not see_match:
            link_text = None
            link_type = None

    if not link_text or not link_type:
        return []

    # 分割多个链接
    # 先按逗号分割，但要小心括号内的逗号
    # 简单方法：按 ", " 和 " and " 分割
    # 但要注意 "and" 可能出现在链接名称中（如 "Cobalt(II,III) oxide"）
    # 所以先按逗号分割，然后处理每个部分

    # 智能分割：检查逗号后是否是大写字母，以及拆分后的内容是否都在数据中存在
    parts = []

    if agent_set:
        # 有 agent_set，进行智能分割
        # 先找到所有括号外的逗号位置
        paren_depth = 0
        comma_positions = []

        for i, char in enumerate(link_text):
            if char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
            elif char == "," and paren_depth == 0:
                comma_positions.append(i)

        # 如果没有逗号，直接返回整个字符串
        if not comma_positions:
            parts = [link_text.strip()]
        else:
            # 从后往前检查每个逗号，决定是否拆分
            # 这样可以正确处理多个逗号的情况
            split_points = [0]  # 记录所有分割点（包括开头）

            for comma_idx, comma_pos in enumerate(comma_positions):
                # 检查逗号后的字符
                next_char_pos = comma_pos + 1
                while (
                    next_char_pos < len(link_text) and link_text[next_char_pos] == " "
                ):
                    next_char_pos += 1

                if (
                    next_char_pos < len(link_text)
                    and link_text[next_char_pos].isupper()
                ):
                    # 逗号后是大写字母，检查是否可以拆分
                    # 提取逗号前的部分（从上一个分割点到当前逗号）
                    prev_split = split_points[-1]
                    before_comma = link_text[prev_split:comma_pos].strip()

                    # 提取逗号后的部分（到下一个逗号或字符串末尾）
                    next_comma_pos = (
                        comma_positions[comma_idx + 1]
                        if comma_idx + 1 < len(comma_positions)
                        else len(link_text)
                    )
                    after_comma = link_text[next_char_pos:next_comma_pos].strip()

                    # 检查拆分后的两部分是否都在数据中存在
                    before_exists = before_comma in agent_set if before_comma else False
                    after_exists = after_comma in agent_set if after_comma else False

                    if before_exists and after_exists:
                        # 两部分都存在，可以拆分
                        split_points.append(next_char_pos)

            # 根据 split_points 进行分割
            for i in range(len(split_points)):
                start = split_points[i]
                end = (
                    split_points[i + 1] if i + 1 < len(split_points) else len(link_text)
                )
                part = link_text[start:end].strip()
                if part:
                    parts.append(part)

            # 如果没有找到可拆分的逗号，不拆分
            if len(parts) == 0:
                parts = [link_text.strip()]
    else:
        # 没有提供 agent_set，使用原来的逻辑（按逗号分割，但保留括号内的逗号）
        current_part = ""
        paren_depth = 0

        for char in link_text:
            if char == "(":
                paren_depth += 1
                current_part += char
            elif char == ")":
                paren_depth -= 1
                current_part += char
            elif char == "," and paren_depth == 0:
                # 只有在括号外部的逗号才分割
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ""
            else:
                current_part += char

        # 添加最后一部分
        if current_part.strip():
            parts.append(current_part.strip())

    # 如果没有找到逗号分割，尝试整个字符串
    if not parts:
        parts = [link_text.strip()]

    # 处理每个部分，检查是否包含 " and "
    link_names = []
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # 去除开头的 "and "（如果存在）
        part = re.sub(r"^\s*and\s+", "", part, flags=re.IGNORECASE).strip()
        if not part:
            continue

        # 检查是否包含 " and "（注意空格，避免匹配单词中的 and）
        if re.search(r"\s+and\s+", part, re.IGNORECASE):
            # 按 " and " 分割
            and_parts = re.split(r"\s+and\s+", part, flags=re.IGNORECASE)
            for and_part in and_parts:
                and_part = and_part.strip()
                # 再次去除可能的 "and " 前缀
                and_part = re.sub(
                    r"^\s*and\s+", "", and_part, flags=re.IGNORECASE
                ).strip()
                if and_part:
                    link_names.append(and_part)
        else:
            link_names.append(part)

    # 清理链接：去除首尾空格和多余的标点
    cleaned_link_names = []
    for link_name in link_names:
        link_name = link_name.strip()
        # 去除末尾的句号、逗号等（但保留括号内的）
        link_name = re.sub(r"[.,;]+$", "", link_name)
        link_name = link_name.strip()
        if link_name:
            cleaned_link_names.append(link_name)

    # 去重并保持顺序，同时创建包含类型的字典列表
    seen = set()
    unique_links = []
    for link_name in cleaned_link_names:
        if link_name not in seen:
            seen.add(link_name)
            unique_links.append({"link": link_name, "type": link_type})

    return unique_links


def process_iarc_json(input_file: str, output_file: str = None):
    """
    处理 iarc.json 文件，为每个条目添加 Links 字段

    Args:
        input_file: 输入 JSON 文件路径
        output_file: 输出 JSON 文件路径，如果为 None 则覆盖原文件

    每个条目的 Links 字段是一个数组，包含字典对象，每个字典包含：
    - 'link': 链接名称
    - 'type': 链接类型，'see' 或 'see_also'
    """
    # 读取 JSON 文件
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 构建所有 Agent 名称的集合，用于验证拆分后的链接是否存在
    agent_set = set()
    for item in data:
        agent_text = item.get("Agent", "")
        if agent_text:
            # 先清理 see/see also 内容，获取原始 Agent 名称
            cleaned_agent = remove_see_from_agent(agent_text)
            if cleaned_agent:
                agent_set.add(cleaned_agent)
            # 也添加原始 Agent（可能包含 see 的内容，用于匹配）
            agent_set.add(agent_text)

    # 处理每个条目
    for item in data:
        agent_text = item.get("Agent", "")
        if agent_text:
            # 提取链接（传入 agent_set 用于智能分割）
            links = extract_links_from_agent(agent_text, agent_set)
            item["Links"] = links if links else []

            # 移除 Agent 字段中的 see/see also 内容
            cleaned_agent = remove_see_from_agent(agent_text)
            item["Agent"] = cleaned_agent
        else:
            item["Links"] = []

    # 保存结果
    output_path = output_file or input_file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"处理完成，共处理 {len(data)} 条记录")
    print(f"结果已保存到: {output_path}")


def translate_agent(
    item: Dict[str, Any], index: int, total: int, lock: Lock
) -> tuple[int, Dict[str, Any], str]:
    """
    翻译单个 Agent 名称

    Args:
        item: 包含 Agent 字段的字典
        index: 当前项的索引
        total: 总项数
        lock: 用于线程安全的锁

    Returns:
        (index, item, error_message) 元组，如果成功 error_message 为 None
    """
    system_prompt = """
    你是一名食品安全领域的专业翻译助手。
    你的任务是将英文的 Agent 名称翻译为中文。
    请直接输出翻译结果，不要添加任何其他内容。
    """

    agent = item["Agent"]
    human_message = f"请将以下英文名称翻译为中文：{agent}，不要添加任何其他内容。"

    try:
        response = chat(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_message)],
            provider_name="ollama",
            provider_config={
                "model": "qwen3",
                "temperature": 0.4,
                "reasoning": False,
            },
        )
        item["Agent_Chinese"] = response

        with lock:
            print(f"[{index + 1}/{total}] 翻译完成: {agent} -> {response}")

        return (index, item, None)
    except Exception as e:
        error_msg = f"翻译失败: {agent} - {str(e)}"
        with lock:
            print(f"[{index + 1}/{total}] {error_msg}")
        return (index, item, error_msg)


def process_agent_chinese(
    input_file: str, output_file: str = None, max_workers: int = 10
):
    """
    处理 agent_chinese.json 文件，为每个条目添加 Agent_Chinese 字段（多线程版本）

    Args:
        input_file: 输入 JSON 文件路径
        output_file: 输出 JSON 文件路径，如果为 None 则覆盖原文件
        max_workers: 最大线程数，默认为 10
    """
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"开始处理 {len(data)} 条记录，使用 {max_workers} 个线程...")

    # 创建线程锁用于打印进度
    lock = Lock()

    # 使用线程池并行处理
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = {
            executor.submit(translate_agent, item, i, len(data), lock): i
            for i, item in enumerate(data)
        }

        # 收集结果
        results = {}
        errors = []

        for future in as_completed(futures):
            try:
                index, item, error_msg = future.result()
                results[index] = item
                if error_msg:
                    errors.append((index, error_msg))
            except Exception as e:
                original_index = futures[future]
                error_msg = f"处理异常: {str(e)}"
                errors.append((original_index, error_msg))
                print(f"任务异常: {error_msg}")

    # 按原始顺序重新排列结果
    sorted_results = [results[i] for i in sorted(results.keys())]

    # 更新原始数据
    for i, item in enumerate(sorted_results):
        if i < len(data):
            data[i]["Agent_Chinese"] = item.get("Agent_Chinese", "")

    # 保存结果
    output_path = output_file or input_file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n处理完成！")
    print(f"成功: {len(results)} 条")
    if errors:
        print(f"失败: {len(errors)} 条")
        print("错误详情:")
        for idx, error_msg in errors:
            print(f"  [{idx + 1}] {error_msg}")
    print(f"结果已保存到: {output_path}")


def normalize_agent_name(agent_name: str) -> str:
    """
    标准化 Agent 名称，用于匹配（去除大小写、多余空格等）
    
    Args:
        agent_name: 原始 Agent 名称
        
    Returns:
        标准化后的名称
    """
    if not agent_name:
        return ""
    # 转换为小写
    normalized = agent_name.lower()
    # 去除首尾空格
    normalized = normalized.strip()
    # 将多个连续空格替换为单个空格
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def find_matching_agent(agent_name: str, agent_list: List[str]) -> str:
    """
    在 agent_list 中查找与 agent_name 匹配的项（考虑大小写和空格差异）
    
    Args:
        agent_name: 要查找的 Agent 名称
        agent_list: Agent 名称列表
        
    Returns:
        匹配的 Agent 名称，如果未找到则返回 None
    """
    normalized_target = normalize_agent_name(agent_name)
    if not normalized_target:
        return None
    
    # 首先尝试精确匹配（标准化后）
    for agent in agent_list:
        if normalize_agent_name(agent) == normalized_target:
            return agent
    
    # 如果精确匹配失败，尝试模糊匹配
    # 计算相似度，选择最相似的匹配
    best_match = None
    best_similarity = 0.0
    similarity_threshold = 0.85  # 相似度阈值
    
    for agent in agent_list:
        normalized_agent = normalize_agent_name(agent)
        if not normalized_agent:
            continue
        
        # 计算相似度：使用简单的字符重叠比例
        # 方法1: 如果一个是另一个的子串，且长度差异小，认为相似
        if normalized_target == normalized_agent:
            return agent  # 应该不会到这里，但保险起见
        
        # 方法2: 计算共同字符的比例
        target_chars = set(normalized_target)
        agent_chars = set(normalized_agent)
        
        if not target_chars or not agent_chars:
            continue
        
        # 计算 Jaccard 相似度（交集/并集）
        intersection = len(target_chars & agent_chars)
        union = len(target_chars | agent_chars)
        similarity = intersection / union if union > 0 else 0.0
        
        # 如果相似度足够高，且长度差异不大，认为是匹配
        if similarity >= similarity_threshold:
            length_diff_ratio = abs(len(normalized_target) - len(normalized_agent)) / max(len(normalized_target), len(normalized_agent))
            if length_diff_ratio < 0.3:  # 长度差异不超过30%
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = agent
    
    return best_match


def merge_links_and_cancer_sites(links_file: str, cancer_sites_file: str, output_file: str = None):
    """
    将 cancer_site.json 的数据合并到 link_chinese.json 中
    
    Args:
        links_file: links_chinese.json 文件路径
        cancer_sites_file: cancer_site.json 文件路径
        output_file: 输出文件路径，如果为 None 则覆盖 links_file
    """
    with open(links_file, "r", encoding="utf-8") as f:
        links_data = json.load(f)
    with open(cancer_sites_file, "r", encoding="utf-8") as f:
        cancer_sites_data = json.load(f)
    
    # 构建 Agent 到癌症部位的映射
    # 格式: {agent_name: [{"cancer_site": "...", "evidence_type": "sufficient"/"limited"}, ...]}
    agent_to_cancer_sites = {}
    
    for cancer_site_item in cancer_sites_data:
        cancer_site = cancer_site_item.get("cancer_site", "")
        
        # 处理充分证据的 Agent
        for agent in cancer_site_item.get("sufficient_evidence_agents", []):
            if agent not in agent_to_cancer_sites:
                agent_to_cancer_sites[agent] = []
            agent_to_cancer_sites[agent].append({
                "cancer_site": cancer_site,
                "evidence_type": "sufficient"
            })
        
        # 处理有限证据的 Agent
        for agent in cancer_site_item.get("limited_evidence_agents", []):
            if agent not in agent_to_cancer_sites:
                agent_to_cancer_sites[agent] = []
            agent_to_cancer_sites[agent].append({
                "cancer_site": cancer_site,
                "evidence_type": "limited"
            })
    
    # 为 links_data 中的每个条目添加癌症部位信息
    matched_count = 0
    unmatched_agents = []
    
    for link_item in links_data:
        agent_name = link_item.get("Agent", "")
        if not agent_name:
            link_item["Cancer_Sites"] = []
            continue
        
        # 尝试在 agent_to_cancer_sites 中查找匹配的 Agent
        matched_agent = find_matching_agent(agent_name, list(agent_to_cancer_sites.keys()))
        
        if matched_agent:
            # 找到匹配，添加癌症部位信息
            link_item["Cancer_Sites"] = agent_to_cancer_sites[matched_agent]
            matched_count += 1
        else:
            # 未找到匹配
            link_item["Cancer_Sites"] = []
            unmatched_agents.append(agent_name)
    
    # 保存结果
    output_path = output_file or links_file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(links_data, f, ensure_ascii=False, indent=2)
    
    print(f"合并完成！")
    print(f"总条目数: {len(links_data)}")
    print(f"成功匹配: {matched_count} 条")
    print(f"未匹配: {len(unmatched_agents)} 条")
    if unmatched_agents:
        print(f"\n未匹配的 Agent 示例（前10个）:")
        for agent in unmatched_agents[:10]:
            print(f"  - {agent}")
    print(f"结果已保存到: {output_path}")
  


if __name__ == "__main__":
    # 处理 iarc.json 文件
    # process_agent_chinese("tools/iarc_links.json", "tools/iarc_links_chinese.json")
    merge_links_and_cancer_sites(
        "tools/iarc_links_chinese.json", "tools/iarc_cancer_site.json"
    )
