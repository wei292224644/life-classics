"""
检查 forks 目录中缺失的页码，与 chunks 目录对比
"""

import re
from pathlib import Path
from typing import Set


def extract_page_number(filename: str) -> int:
    """从文件名中提取页码，例如 'page_123.md' -> 123"""
    match = re.search(r'page_(\d+)\.md', filename)
    if match:
        return int(match.group(1))
    return 0


def get_page_numbers(directory: Path) -> Set[int]:
    """获取目录中所有文件的页码集合"""
    pages = set()
    if not directory.exists():
        return pages
    
    for file_path in directory.glob("page_*.md"):
        page_num = extract_page_number(file_path.name)
        if page_num > 0:
            pages.add(page_num)
    
    return pages


def main():
    """主函数：对比两个目录，找出缺失的页码"""
    script_dir = Path(__file__).parent
    chunks_dir = script_dir / "chunks"
    forks_dir = script_dir / "forks"
    
    print("=" * 60)
    print("检查 forks 目录中缺失的页码")
    print("=" * 60)
    print(f"\nchunks 目录: {chunks_dir}")
    print(f"forks 目录: {forks_dir}\n")
    
    # 获取两个目录中的页码集合
    chunks_pages = get_page_numbers(chunks_dir)
    forks_pages = get_page_numbers(forks_dir)
    
    print(f"chunks 目录中的页码数量: {len(chunks_pages)}")
    print(f"forks 目录中的页码数量: {len(forks_pages)}\n")
    
    # 找出缺失的页码
    missing_pages = sorted(chunks_pages - forks_pages)
    
    if not missing_pages:
        print("✅ 没有缺失的页码！forks 目录包含所有 chunks 目录中的页码。")
        return
    
    print(f"❌ 发现 {len(missing_pages)} 个缺失的页码：\n")
    
    # 按范围分组显示（更易读）
    if len(missing_pages) <= 50:
        # 如果缺失的页码不多，直接列出
        print("缺失的页码列表：")
        print(", ".join(map(str, missing_pages)))
    else:
        # 如果缺失的页码很多，按范围显示
        print("缺失的页码（按范围显示）：")
        ranges = []
        start = missing_pages[0]
        end = missing_pages[0]
        
        for page in missing_pages[1:]:
            if page == end + 1:
                end = page
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = page
                end = page
        
        # 添加最后一个范围
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
        
        print(", ".join(ranges))
    
    print(f"\n\n缺失页码总数: {len(missing_pages)}")
    print(f"缺失页码范围: {min(missing_pages)} - {max(missing_pages)}")
    
    # 额外检查：是否有 forks 中存在但 chunks 中不存在的页码
    extra_pages = sorted(forks_pages - chunks_pages)
    if extra_pages:
        print(f"\n⚠️  注意：forks 目录中有 {len(extra_pages)} 个页码在 chunks 目录中不存在：")
        print(", ".join(map(str, extra_pages[:20])))  # 只显示前20个
        if len(extra_pages) > 20:
            print(f"... 还有 {len(extra_pages) - 20} 个")


if __name__ == "__main__":
    main()
