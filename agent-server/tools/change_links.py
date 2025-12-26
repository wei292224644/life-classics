"""
解析 iarc.json 文件中的 Agent 字段，提取 see 后面的链接
"""

import json
import re
from typing import List, Dict, Any


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
    pattern1 = r'\(see\s+(?:also\s+)?[^)]+\)'
    cleaned_text = re.sub(pattern1, '', agent_text, flags=re.IGNORECASE)
    
    # 模式2: 移除 , see ... 或 see ... (没有括号)
    # 找到不在括号内的 see，移除从 see 开始到末尾的内容
    paren_depth = 0
    see_pos = -1
    
    for i, char in enumerate(cleaned_text):
        if char == '(':
            paren_depth += 1
        elif char == ')':
            paren_depth -= 1
        elif paren_depth == 0:
            # 在括号外部，检查是否是 see
            remaining = cleaned_text[i:]
            # 检查是否是 "see " 或 ", see " 或开头是 "see "
            if (i == 0 or cleaned_text[i-1] == ',' or cleaned_text[i-1] == ' ') and remaining.lower().startswith('see '):
                # 找到 see 的位置，移除从 see 开始到末尾的内容
                # 如果前面有逗号，也要移除逗号和前面的空格
                if i > 0 and cleaned_text[i-1] == ',':
                    # 找到逗号前的位置
                    comma_pos = i - 1
                    # 移除逗号前的空格（如果有）
                    while comma_pos > 0 and cleaned_text[comma_pos - 1] == ' ':
                        comma_pos -= 1
                    cleaned_text = cleaned_text[:comma_pos].rstrip()
                else:
                    cleaned_text = cleaned_text[:i].rstrip()
                break
    
    # 清理多余的空格和标点
    cleaned_text = cleaned_text.strip()
    # 移除末尾的逗号
    cleaned_text = re.sub(r',\s*$', '', cleaned_text)
    cleaned_text = cleaned_text.strip()
    
    return cleaned_text


def extract_links_from_agent(agent_text: str, agent_set: set = None) -> List[Dict[str, str]]:
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
    pattern1 = r'\(see\s+(also\s+)?([^)]+)\)'
    match1 = re.search(pattern1, agent_text, re.IGNORECASE)
    if match1:
        link_type = 'see_also' if match1.group(1) else 'see'
        link_text = match1.group(2)
    else:
        # 模式2: , see ... 或  see ... (没有括号)
        # 匹配不在括号内的 see（在逗号后或字符串开头）
        # 使用更精确的正则表达式：找到不在括号内的 see
        # 方法：找到所有 see 的位置，检查是否在括号内
        paren_depth = 0
        see_match = None
        
        for i, char in enumerate(agent_text):
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif paren_depth == 0:
                # 在括号外部，检查是否是 see
                remaining = agent_text[i:]
                # 检查是否是 "see " 或 ", see " 或开头是 "see "
                if (i == 0 or agent_text[i-1] == ',' or agent_text[i-1] == ' ') and remaining.lower().startswith('see '):
                    # 提取 see 后面的内容
                    if remaining.lower().startswith('see also '):
                        link_type = 'see_also'
                        link_text = remaining[9:].strip()
                    else:
                        link_type = 'see'
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
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == ',' and paren_depth == 0:
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
                while next_char_pos < len(link_text) and link_text[next_char_pos] == ' ':
                    next_char_pos += 1
                
                if next_char_pos < len(link_text) and link_text[next_char_pos].isupper():
                    # 逗号后是大写字母，检查是否可以拆分
                    # 提取逗号前的部分（从上一个分割点到当前逗号）
                    prev_split = split_points[-1]
                    before_comma = link_text[prev_split:comma_pos].strip()
                    
                    # 提取逗号后的部分（到下一个逗号或字符串末尾）
                    next_comma_pos = comma_positions[comma_idx + 1] if comma_idx + 1 < len(comma_positions) else len(link_text)
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
                end = split_points[i + 1] if i + 1 < len(split_points) else len(link_text)
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
            if char == '(':
                paren_depth += 1
                current_part += char
            elif char == ')':
                paren_depth -= 1
                current_part += char
            elif char == ',' and paren_depth == 0:
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
        part = re.sub(r'^\s*and\s+', '', part, flags=re.IGNORECASE).strip()
        if not part:
            continue
        
        # 检查是否包含 " and "（注意空格，避免匹配单词中的 and）
        if re.search(r'\s+and\s+', part, re.IGNORECASE):
            # 按 " and " 分割
            and_parts = re.split(r'\s+and\s+', part, flags=re.IGNORECASE)
            for and_part in and_parts:
                and_part = and_part.strip()
                # 再次去除可能的 "and " 前缀
                and_part = re.sub(r'^\s*and\s+', '', and_part, flags=re.IGNORECASE).strip()
                if and_part:
                    link_names.append(and_part)
        else:
            link_names.append(part)
    
    # 清理链接：去除首尾空格和多余的标点
    cleaned_link_names = []
    for link_name in link_names:
        link_name = link_name.strip()
        # 去除末尾的句号、逗号等（但保留括号内的）
        link_name = re.sub(r'[.,;]+$', '', link_name)
        link_name = link_name.strip()
        if link_name:
            cleaned_link_names.append(link_name)
    
    # 去重并保持顺序，同时创建包含类型的字典列表
    seen = set()
    unique_links = []
    for link_name in cleaned_link_names:
        if link_name not in seen:
            seen.add(link_name)
            unique_links.append({
                'link': link_name,
                'type': link_type
            })
    
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
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 构建所有 Agent 名称的集合，用于验证拆分后的链接是否存在
    agent_set = set()
    for item in data:
        agent_text = item.get('Agent', '')
        if agent_text:
            # 先清理 see/see also 内容，获取原始 Agent 名称
            cleaned_agent = remove_see_from_agent(agent_text)
            if cleaned_agent:
                agent_set.add(cleaned_agent)
            # 也添加原始 Agent（可能包含 see 的内容，用于匹配）
            agent_set.add(agent_text)
    
    # 处理每个条目
    for item in data:
        agent_text = item.get('Agent', '')
        if agent_text:
            # 提取链接（传入 agent_set 用于智能分割）
            links = extract_links_from_agent(agent_text, agent_set)
            item['Links'] = links if links else []
            
            # 移除 Agent 字段中的 see/see also 内容
            cleaned_agent = remove_see_from_agent(agent_text)
            item['Agent'] = cleaned_agent
        else:
            item['Links'] = []
    
    # 保存结果
    output_path = output_file or input_file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"处理完成，共处理 {len(data)} 条记录")
    print(f"结果已保存到: {output_path}")


if __name__ == '__main__':
    # 处理 iarc.json 文件
    process_iarc_json('tools/iarc.json', 'tools/iarc_links.json')

