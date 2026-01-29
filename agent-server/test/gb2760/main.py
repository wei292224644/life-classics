"""
从 forks 文件夹读取所有 markdown 文件，逐个处理并导入到知识库

处理流程：
1. 从 forks 文件夹读取所有 markdown 文件
2. 对每个文件单独处理（避免内容过长导致 LLM 处理失败）
3. 每个文件使用相同的 doc_id "GB2760-2024"，但有不同的 markdown_id
4. 使用框架的 convert_to_structured 处理并保存到 markdown_db
5. 使用框架的 split_structured 切分文档
6. 将所有 chunks 导入到知识库
"""

import sys
import uuid
import re
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# 添加项目根目录到路径，以便导入app模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.document_chunk import DocumentChunk, ContentType
from app.core.kb.pre_parse.convert_to_structured import convert_to_structured
from app.core.kb.strategy.structured_strategy import split_structured
from app.core.kb.vector_store import vector_store_manager


def natural_sort_key(path: Path) -> tuple:
    """
    自然排序键函数，用于按数字顺序排序文件名
    例如: page_1.md < page_2.md < page_10.md < page_100.md
    
    Args:
        path: 文件路径
        
    Returns:
        排序键元组
    """
    # 提取文件名中的数字部分
    name = path.name
    # 使用正则表达式分割文件名，将数字和非数字部分分开
    parts = re.split(r'(\d+)', name)
    # 将数字部分转换为整数，非数字部分保持原样
    key_parts = []
    for part in parts:
        if part.isdigit():
            key_parts.append(int(part))
        else:
            key_parts.append(part.lower())
    return tuple(key_parts)


def get_markdown_files(forks_dir: Path) -> List[Path]:
    """
    获取 forks 文件夹中的所有 markdown 文件

    Args:
        forks_dir: forks 文件夹路径

    Returns:
        markdown 文件路径列表
    """
    if not forks_dir.exists():
        raise FileNotFoundError(f"forks 文件夹不存在: {forks_dir}")

    # 获取所有 .md 文件，按自然排序（确保数字顺序正确）
    # 例如: page_1.md, page_2.md, ..., page_10.md, page_100.md
    markdown_files = sorted(forks_dir.glob("*.md"), key=natural_sort_key)
    
    if not markdown_files:
        raise ValueError(f"forks 文件夹中没有找到 markdown 文件: {forks_dir}")

    return markdown_files


def import_forks_to_kb(forks_dir: Path, start: Optional[int] = None, end: Optional[int] = None):
    """
    从 forks 文件夹读取所有 markdown 文件，逐个处理并导入到知识库
    每个文件单独处理，但使用相同的 doc_id "GB2760-2024"

    Args:
        forks_dir: forks 文件夹路径
        start: 起始索引（从1开始，包含），None 表示从第一个文件开始
        end: 结束索引（包含），None 表示处理到最后一个文件
    """
    print("\n📋 开始处理 forks 文件夹...")
    start_time = datetime.now()
    
    # 获取所有 markdown 文件（已按自然排序）
    all_markdown_files = get_markdown_files(forks_dir)
    print(f"\n📂 找到 {len(all_markdown_files)} 个 markdown 文件")
    # 显示文件列表（前10个和后10个，如果文件太多）
    if len(all_markdown_files) <= 20:
        print("📋 文件列表:")
        for i, f in enumerate(all_markdown_files, 1):
            print(f"   [{i:3d}] {f.name}")
    else:
        print("📋 文件列表（前10个和后10个）:")
        for i, f in enumerate(all_markdown_files[:10], 1):
            print(f"   [{i:3d}] {f.name}")
        print(f"   ... (省略 {len(all_markdown_files) - 20} 个文件) ...")
        for i, f in enumerate(all_markdown_files[-10:], len(all_markdown_files) - 9):
            print(f"   [{i:3d}] {f.name}")
    
    # 根据 start 和 end 切片文件列表
    if start is not None or end is not None:
        # start 和 end 是从1开始的索引，需要转换为从0开始的索引
        start_idx = (start - 1) if start is not None else 0
        end_idx = end if end is not None else len(all_markdown_files)
        
        # 验证索引范围
        if start_idx < 0:
            start_idx = 0
        if end_idx > len(all_markdown_files):
            end_idx = len(all_markdown_files)
        if start_idx >= end_idx:
            print(f"⚠️  无效的索引范围: start={start}, end={end}")
            return
        
        markdown_files = all_markdown_files[start_idx:end_idx]
        print(f"📌 处理范围: [{start_idx + 1}-{end_idx}] / [1-{len(all_markdown_files)}]")
    else:
        markdown_files = all_markdown_files
    
    all_chunks = []
    
    # 逐个处理每个文件
    # 计算实际的文件索引（用于显示）
    actual_start_idx = (start - 1) if start is not None else 0
    for local_idx, md_file in enumerate(markdown_files):
        # 计算文件在总列表中的索引（从1开始）
        global_idx = actual_start_idx + local_idx + 1
        file_start_time = datetime.now()
        print(f"\n{'='*60}")
        print(f"[{global_idx}/{len(all_markdown_files)}] 正在处理: {md_file.name}")
        print(f"{'='*60}")
        
        try:
            # 读取文件内容
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            if not content or not content.strip():
                print(f"  ⚠️  文件内容为空，跳过")
                continue
            
            print(f"  📄 文件大小: {len(content):,} 字符")
            
            # 为每个文件生成独立的 markdown_id
            markdown_id = uuid.uuid4().hex[:16]
            
            # 创建 DocumentChunk
            # 所有文件使用相同的 doc_id "GB2760-2024"
            document_chunk = DocumentChunk(
                doc_id="GB2760-2024",
                doc_title="GB2760-2024",
                section_path=[],
                content_type=ContentType.NOTE,
                content=content,
                meta={
                    "file_name": md_file.name,
                    "file_path": str(md_file),
                    "source_format": "markdown",
                },
                markdown_id=markdown_id,
            )

            # 使用框架的 convert_to_structured 处理（这会生成 markdown_cache 并保存到 markdown_db）
            print(f"  💾 正在转换为结构化格式...")
            document_chunk = convert_to_structured(document_chunk)
            print(f"  ✓ 结构化转换完成，内容已保存到 markdown_db")

            # 使用框架的 split_structured 切分
            print(f"  ✂️  正在切分文档...")
            chunks = split_structured([document_chunk])
            print(f"  ✓ 切分完成，生成 {len(chunks)} 个 chunks")
            
            all_chunks.extend(chunks)
            
            file_end_time = datetime.now()
            file_duration = (file_end_time - file_start_time).total_seconds()
            print(f"  ✅ 文件处理完成，耗时: {file_duration:.2f} 秒")
            
        except Exception as e:
            print(f"  ❌ 处理文件失败 {md_file.name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # 将所有 chunks 导入到知识库
    if all_chunks:
        print(f"\n{'='*60}")
        print(f"📚 正在导入 {len(all_chunks)} 个 chunks 到知识库...")
        vector_store_manager.add_chunks(all_chunks)
        print(f"  ✓ 成功导入到知识库")
    else:
        print(f"\n⚠️  没有生成任何 chunks")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"\n{'='*60}")
    print(f"✅ 全部完成！")
    print(f"   - 处理文件数: {len(markdown_files)}")
    print(f"   - 生成 chunks 数: {len(all_chunks)}")
    print(f"   - 总耗时: {duration:.2f} 秒")
    print(f"{'='*60}")


if __name__ == "__main__":
    import argparse
    
    # 获取脚本所在目录
    script_dir = Path(__file__).parent

    # forks 文件夹路径（相对于脚本所在目录）
    forks_dir = script_dir / "forks"

    # 检查文件夹是否存在
    if not forks_dir.exists():
        print(f"错误: 找不到 forks 文件夹: {forks_dir}")
        exit(1)

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="从 forks 文件夹导入 markdown 文件到知识库")
    parser.add_argument(
        "--start",
        type=int,
        default=None,
        help="起始文件索引（从1开始，包含）",
    )
    parser.add_argument(
        "--end",
        type=int,
        default=None,
        help="结束文件索引（包含）",
    )
    args = parser.parse_args()

    # 导入到知识库
    import_forks_to_kb(forks_dir, start=args.start, end=args.end)
