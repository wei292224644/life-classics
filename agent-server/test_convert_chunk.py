"""
知识库工程系统
将带有 content_type 的 Markdown 文档解析并转换为可直接写入知识库的 Chunk JSON 数组
"""

import re
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

try:
    from unidecode import unidecode
except ImportError:
    # 如果没有 unidecode，使用简单的 ASCII 转换
    # 注意：这个方法会移除非 ASCII 字符，建议安装 unidecode 库
    import unicodedata

    def unidecode(text: str) -> str:
        """将 Unicode 文本转换为 ASCII（回退方案）"""
        # 这个方法会移除非 ASCII 字符，不是最佳方案
        # 建议安装 unidecode 库以获得更好的中文转换效果（pip install unidecode）
        normalized = unicodedata.normalize("NFKD", text)
        return "".join(
            c
            for c in normalized
            if unicodedata.category(c) != "Mn" and (c.isascii() or c in "._-")
        )


# 允许的 content_type 枚举值
ALLOWED_CONTENT_TYPES = {
    "metadata",
    "scope",
    "definition",
    "chemical_formula",
    "chemical_structure",
    "molecular_weight",
    "specification_table",
    "specification_text",
    "test_method",
    "instrument",
    "reagent",
    "calculation_formula",
    "chromatographic_method",
    "identification_test",
    "general_rule",
    "note",
}


@dataclass
class Chunk:
    """Chunk 数据结构"""

    chunk_id: str
    doc_id: str
    doc_title: str
    section_path: List[str]
    content_type: str
    content: Any
    meta: Dict[str, Any]


class MarkdownChunkParser:
    """Markdown 文档解析器"""

    def __init__(self):
        self.current_section_path: List[str] = []
        self.chunk_counter: Dict[Tuple[str, ...], int] = (
            {}
        )  # (section_path, content_type) -> count

    def parse_markdown(
        self, markdown_content: str, doc_id: str, doc_title: str, source: str
    ) -> List[Dict[str, Any]]:
        """
        解析 Markdown 文档并生成 Chunk JSON 数组

        Args:
            markdown_content: Markdown 文档内容
            doc_id: 文档 ID
            doc_title: 文档标题
            source: 原始文件名或来源标识

        Returns:
            Chunk JSON 数组
        """
        self.current_section_path = []
        self.chunk_counter = {}
        chunks: List[Chunk] = []

        lines = markdown_content.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i]

            # 解析标题，更新 section_path
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                self._update_section_path(level, title)
                i += 1
                continue

            # 解析 content_type 标记（支持两种格式）
            # 格式1: [content_type: xxx]（英文方括号）
            # 格式2: ```xxx ... ```
            content_type = None
            block_content = None
            next_i = i

            # 尝试格式1: [content_type: xxx]
            bracket_match = re.match(r"^\[content_type:\s*(\w+)\]", line.strip())
            if bracket_match:
                content_type = bracket_match.group(1)
                # 提取内容（从下一行开始，直到下一个 content_type 标记或标题）
                block_lines = []
                next_i = i + 1
                while next_i < len(lines):
                    next_line = lines[next_i].strip()
                    # 遇到新的 content_type 标记或标题，停止
                    if (
                        re.match(r"^\[content_type:\s*\w+\]", next_line)
                        or re.match(r"^#{1,6}\s+", next_line)
                        or re.match(r"^```\w+$", next_line)
                    ):
                        break
                    block_lines.append(lines[next_i])
                    next_i += 1
                block_content = "\n".join(block_lines).strip()

            # 尝试格式2: ```xxx ... ```
            if content_type is None:
                fenced_match = re.match(r"^```(\w+)$", line.strip())
                if fenced_match:
                    content_type = fenced_match.group(1)
                    # 提取 block 内容
                    block_lines = []
                    next_i = i + 1
                    while next_i < len(lines):
                        if lines[next_i].strip() == "```":
                            next_i += 1
                            break
                        block_lines.append(lines[next_i])
                        next_i += 1
                    block_content = "\n".join(block_lines).strip()

            # 如果找到 content_type，处理内容
            if content_type and content_type in ALLOWED_CONTENT_TYPES:
                # 处理特殊合并规则
                if content_type == "calculation_formula":
                    # 检查后面是否有变量定义
                    next_content_type, next_content = self._peek_next_content(
                        lines, next_i
                    )
                    if next_content_type == "note" and self._is_variable_definition(
                        next_content
                    ):
                        block_content = self._merge_formula_with_variables(
                            block_content, next_content
                        )
                        # 跳过下一个 content block
                        next_i = self._skip_next_content(lines, next_i)

                # 解析内容（对于 specification_table，传入 section_path 的最后一项作为 title）
                parsed_content = self._parse_content(
                    content_type, block_content, section_path=self.current_section_path
                )

                # 生成 chunk
                chunk = self._create_chunk(
                    doc_id=doc_id,
                    doc_title=doc_title,
                    content_type=content_type,
                    content=parsed_content,
                    source=source,
                )
                chunks.append(chunk)
                i = next_i
                continue

            i += 1

        # 转换为 JSON 格式
        return [self._chunk_to_dict(chunk) for chunk in chunks]

    def _update_section_path(self, level: int, title: str):
        """更新 section_path"""

        target_length = level - 1
        while len(self.current_section_path) >= target_length:
            self.current_section_path.pop()
        self.current_section_path.append(title)

    def _peek_next_content(
        self, lines: List[str], start_idx: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """查看下一个 content block 的内容类型和内容（支持两种格式）"""
        i = start_idx
        while i < len(lines):
            line = lines[i].strip()
            # 跳过空行和标题
            if not line or re.match(r"^#{1,6}\s+", line):
                i += 1
                continue

            # 格式1: [content_type: xxx]
            bracket_match = re.match(r"^\[content_type:\s*(\w+)\]", line)
            if bracket_match:
                content_type = bracket_match.group(1)
                block_lines = []
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if (
                        re.match(r"^\[content_type:\s*\w+\]", next_line)
                        or re.match(r"^#{1,6}\s+", next_line)
                        or re.match(r"^```\w+$", next_line)
                    ):
                        break
                    block_lines.append(lines[i])
                    i += 1
                return content_type, "\n".join(block_lines).strip()

            # 格式2: ```xxx ... ```
            fenced_match = re.match(r"^```(\w+)$", line)
            if fenced_match:
                content_type = fenced_match.group(1)
                block_lines = []
                i += 1
                while i < len(lines):
                    if lines[i].strip() == "```":
                        i += 1
                        break
                    block_lines.append(lines[i])
                    i += 1
                return content_type, "\n".join(block_lines).strip()

            i += 1

        return None, None

    def _skip_next_content(self, lines: List[str], start_idx: int) -> int:
        """跳过下一个 content block，返回新的索引（支持两种格式）"""
        i = start_idx
        while i < len(lines):
            line = lines[i].strip()
            if not line or re.match(r"^#{1,4}\s+", line):
                i += 1
                continue

            # 格式1: [content_type: xxx]
            if re.match(r"^\[content_type:\s*\w+\]", line):
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if (
                        re.match(r"^\[content_type:\s*\w+\]", next_line)
                        or re.match(r"^#{1,6}\s+", next_line)
                        or re.match(r"^```\w+$", next_line)
                    ):
                        return i
                    i += 1
                return i

            # 格式2: ```xxx ... ```
            if line.startswith("```"):
                i += 1
                while i < len(lines):
                    if lines[i].strip() == "```":
                        return i + 1
                    i += 1
                return i

            i += 1

        return i

    def _is_variable_definition(self, content: str) -> bool:
        """判断内容是否是变量定义（包含变量说明）"""
        content_lower = content.lower()
        return "：" in content or ":" in content

    def _merge_formula_with_variables(self, formula: str, variables: str) -> str:
        """合并公式和变量定义"""
        return f"{formula}\n\n{variables}"

    def _parse_content(
        self, content_type: str, content: str, section_path: Optional[List[str]] = None
    ) -> Any:
        """根据 content_type 解析内容"""
        if content_type == "metadata":
            return self._parse_metadata(content)
        elif content_type == "specification_table":
            # 对于表格，使用 section_path 的最后一项作为 title
            table_title = None
            if section_path and len(section_path) > 0:
                table_title = section_path[-1]
            return self._parse_table(content, title=table_title)
        elif content_type == "calculation_formula":
            return self._parse_formula(content)
        elif content_type in ["reagent", "instrument"]:
            # 对于 reagent 和 instrument，尝试解析为数组
            parsed_list = self._parse_simple_list(content)
            if parsed_list is not None:
                return parsed_list
            # 如果不是简单列表，返回原始字符串
            return content.strip()
        else:
            # 其他类型直接返回字符串
            return content.strip()

    def _parse_metadata(self, content: str) -> Dict[str, str]:
        """解析 metadata（key-value 格式）"""
        metadata = {}
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 支持 "key: value" 或 "key=value" 格式
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
            elif "=" in line:
                key, value = line.split("=", 1)
                metadata[key.strip()] = value.strip()
        return metadata

    def _parse_table(self, content: str, title: Optional[str] = None) -> Dict[str, Any]:
        """解析表格为结构化格式"""
        lines = [line.rstrip() for line in content.split("\n")]

        if not lines:
            return {"title": title, "rows": []}

        # 如果传入了 title（来自 section_path），优先使用它
        # 否则，尝试从内容第一行提取标题（如果第一行不是表格行）
        table_start = 0
        if title is None:
            if lines and not lines[0].strip().startswith("|"):
                title = lines[0].strip()
                table_start = 1

        # 解析表格
        rows = []
        headers = None
        separator_found = False

        for i in range(table_start, len(lines)):
            line = lines[i].strip()
            if not line:
                continue

            if not line.startswith("|"):
                # 如果不是表格行，可能是标题的延续或其他内容，跳过
                continue

            # 跳过分隔行（如 | --- | --- |）
            if re.match(r"^\|\s*[-:]+(\s*[-:]+)*\s*\|", line):
                separator_found = True
                continue

            # 解析单元格（移除首尾的 |）
            cells = [cell.strip() for cell in line.split("|")[1:-1]]

            if not separator_found:
                # 第一行是表头
                headers = cells
            else:
                # 数据行
                if headers:
                    row_dict = {}
                    for j, header in enumerate(headers):
                        # 确保所有列都有值，不足的用空字符串填充
                        value = cells[j] if j < len(cells) else ""
                        row_dict[header] = value
                    rows.append(row_dict)

        return {"title": title, "rows": rows}

    def _parse_formula(self, content: str) -> Dict[str, Any]:
        """解析计算公式"""
        lines = content.split("\n")
        formula_lines = []
        variables = {}

        in_variables = False
        for line in lines:
            original_line = line
            line = line.strip()
            if not line:
                if in_variables:
                    continue
                else:
                    formula_lines.append("")
                    continue

            # 检测变量定义部分（[__calculation_formula_note__]开头）
            if line.startswith("[__calculation_formula_note__]"):
                in_variables = True
                # 提取变量定义
                var_line = line.replace("[__calculation_formula_note__]", "").strip()
                if var_line:
                    self._parse_variable_line(var_line, variables)
                continue

            # 如果已经进入变量定义部分，且行中包含冒号，认为是变量定义
            if in_variables:
                if "：" in line or ":" in line:
                    self._parse_variable_line(line, variables)
                else:
                    # 如果变量定义部分结束（没有冒号），停止解析变量
                    # 但这里我们继续，因为可能有多行变量定义
                    pass
            else:
                # 公式本体
                formula_lines.append(original_line.rstrip())

        expression = "\n".join(formula_lines).strip()

        return {
            "expression": expression,
            "variables": variables,
        }

    def _parse_variable_line(self, line: str, variables: Dict[str, str]):
        """解析变量定义行"""
        # 支持 "符号: 含义（单位）" 或 "符号：含义（单位）" 格式
        if "：" in line:
            parts = line.split("：", 1)
        elif ":" in line:
            parts = line.split(":", 1)
        else:
            return

        if len(parts) == 2:
            symbol = parts[0].strip()
            meaning = parts[1].strip()
            variables[symbol] = meaning

    def _parse_simple_list(
        self, content: str, max_item_length: int = 200
    ) -> Optional[List[str]]:
        """
        解析简单的列表结构（连续使用 - 开头，无二级结构）

        Args:
            content: 内容文本
            max_item_length: 每个列表项的最大长度，超过此长度不转换为数组

        Returns:
            如果是简单列表，返回字符串数组；否则返回 None
        """
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        if not lines:
            return None

        # 检查是否所有非空行都是列表项（以 - 开头）
        list_items = []
        has_nested = False

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue

            # 检查是否是列表项（以 - 开头，可能前面有空格）
            if line_stripped.startswith("-"):
                # 提取列表项内容（移除开头的 - 和空格）
                item_content = line_stripped[1:].strip()

                # 检查是否有二级结构（以 -- 开头表示嵌套）
                if line_stripped.startswith("--"):
                    has_nested = True
                    break

                # 检查项目长度
                if len(item_content) > max_item_length:
                    return None

                list_items.append(item_content)
            else:
                # 如果有非列表项的行，不转换为数组
                return None

        # 如果有嵌套结构，不转换为数组
        if has_nested:
            return None

        # 如果列表项少于2个，不转换为数组（保持原样）
        if len(list_items) < 1:
            return None

        return list_items

    def _create_chunk(
        self,
        doc_id: str,
        doc_title: str,
        content_type: str,
        content: Any,
        source: str,
    ) -> Chunk:
        """创建 Chunk 对象"""
        # 生成 chunk_id
        section_key = tuple(self.current_section_path)
        key = (section_key, content_type)
        count = self.chunk_counter.get(key, 0) + 1
        self.chunk_counter[key] = count

        # 生成全局唯一的 chunk_id（使用 hash）
        # 基于 doc_id, section_path, content_type, count 和 content 的前100个字符生成 hash
        # 这样可以确保全局唯一性
        section_path_str = (
            ".".join(self.current_section_path) if self.current_section_path else ""
        )

        # 构建用于 hash 的唯一标识字符串
        content_preview = (
            str(content)[:100] if content else ""
        )  # 使用内容的前100个字符增加唯一性
        unique_string = (
            f"{doc_id}||{section_path_str}||{content_type}||{count}||{content_preview}"
        )

        # 使用 SHA256 生成 hash（取前16个字符，足够唯一且不会太长）
        hash_obj = hashlib.sha256(unique_string.encode("utf-8"))
        chunk_id = hash_obj.hexdigest()[:16]  # 使用前16个字符（64位，足够唯一）

        return Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            doc_title=doc_title,
            section_path=self.current_section_path.copy(),
            content_type=content_type,
            content=content,
            meta={
                "standard_type": "国家标准",
                "source": source,
            },
        )

    def _chunk_to_dict(self, chunk: Chunk) -> Dict[str, Any]:
        """将 Chunk 转换为字典"""
        return {
            "chunk_id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "doc_title": chunk.doc_title,
            "section_path": chunk.section_path,
            "content_type": chunk.content_type,
            "content": chunk.content,
            "meta": chunk.meta,
        }


def convert_markdown_to_chunks(
    markdown_file: str,
    doc_id: Optional[str] = None,
    doc_title: Optional[str] = None,
    source: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    将 Markdown 文件转换为 Chunk JSON 数组

    Args:
        markdown_file: Markdown 文件路径
        doc_id: 文档 ID（如果为 None，使用文件名）
        doc_title: 文档标题（如果为 None，使用文件名）
        source: 来源标识（如果为 None，使用文件名）

    Returns:
        Chunk JSON 数组
    """
    file_path = Path(markdown_file)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {markdown_file}")

    with open(file_path, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    if doc_id is None:
        doc_id = file_path.stem
    if doc_title is None:
        doc_title = file_path.stem
    if source is None:
        source = file_path.name

    parser = MarkdownChunkParser()
    chunks = parser.parse_markdown(markdown_content, doc_id, doc_title, source)

    return chunks


def main():
    """主函数"""
    import sys

    if len(sys.argv) < 2:
        print("用法: python test_convert_chunk.py <markdown_file> [output_file]")
        print("示例: python test_convert_chunk.py input.md output.json")
        sys.exit(1)

    markdown_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if output_file is None:
        output_file = Path(markdown_file).stem + "_chunks.json"

    try:
        # 转换
        chunks = convert_markdown_to_chunks(markdown_file)

        # 保存 JSON
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        print(f"✓ 成功解析 {len(chunks)} 个 chunks")
        print(f"✓ 已保存到: {output_file}")

        # 统计信息
        content_type_stats = {}
        for chunk in chunks:
            ct = chunk["content_type"]
            content_type_stats[ct] = content_type_stats.get(ct, 0) + 1

        print("\n内容类型统计:")
        for ct, count in sorted(content_type_stats.items()):
            print(f"  {ct}: {count} 个")

    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
