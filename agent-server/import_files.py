#!/usr/bin/env python3
"""
批量导入文件到知识库
支持 PDF、Markdown、Text 等格式
使用当前知识库导入体系
"""
import sys
import argparse
from pathlib import Path
from typing import List, Optional

from app.core.kb import import_file_step
from app.core.kb.vector_store import vector_store_manager
from app.core.config import settings


def check_document_exists(doc_id: str) -> bool:
    """
    检查文档是否已存在于知识库中
    
    Args:
        doc_id: 文档 ID
        
    Returns:
        是否存在
    """
    try:
        # 查询向量存储中是否存在该 doc_id
        results = vector_store_manager.vector_store._collection.get(
            where={"doc_id": doc_id},
            limit=1,
        )
        return len(results.get("ids", [])) > 0
    except Exception as e:
        print(f"  检查文档是否存在时出错: {e}")
        return False


def get_supported_extensions() -> List[str]:
    """获取支持的文件扩展名列表"""
    return [".pdf", ".md", ".markdown", ".txt"]


def import_files_from_directory(
    directory_path: str = "files",
    start_index: int = 0,
    batch_size: Optional[int] = None,
    single_file: Optional[str] = None,
    skip_existing: bool = False,
    strategy: str = "text",
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
):
    """
    导入目录下所有支持的文件到知识库
    
    Args:
        directory_path: 文件目录路径
        start_index: 从第几个文件开始（从0开始计数）
        batch_size: 每次处理多少个文件，如果为 None 则处理所有剩余文件
        single_file: 如果指定，则只处理这个文件（可以是文件名或完整路径）
        skip_existing: 是否跳过已经存在于知识库中的文件
        strategy: 切分策略（text, structured, table, heading, parent_child）
        chunk_size: 切分大小（仅对 text 策略有效）
        chunk_overlap: 切分重叠大小（仅对 text 策略有效）
    """
    supported_extensions = get_supported_extensions()
    
    # 如果指定了单个文件，优先处理单个文件
    if single_file:
        file_path = Path(single_file)
        
        # 如果文件路径不是绝对路径，尝试在指定目录中查找
        if not file_path.is_absolute():
            directory = Path(directory_path)
            file_path = directory / file_path
        
        if not file_path.exists():
            print(f"错误: 文件 {file_path} 不存在")
            return
        
        file_ext = file_path.suffix.lower()
        if file_ext not in supported_extensions:
            print(f"错误: 文件 {file_path} 不是支持的文件格式（支持: {', '.join(supported_extensions)}）")
            return
        
        files = [file_path]
        print(f"处理单个文件: {file_path.name}")
        print(f"文件路径: {file_path}")
        print(f"切分策略: {strategy}")
        if chunk_size:
            print(f"切分大小: {chunk_size}")
        if chunk_overlap:
            print(f"切分重叠: {chunk_overlap}")
        print(f"跳过已存在文件: {skip_existing}")
        
        # 检查单个文件是否已存在
        if skip_existing:
            doc_id = file_path.stem  # 使用文件名（不含扩展名）作为 doc_id
            if check_document_exists(doc_id):
                print(f"\n文件 {file_path.name} 已存在于知识库中（doc_id: {doc_id}），跳过处理")
                return
        
        print("-" * 60)
        start_index = 0
    else:
        directory = Path(directory_path)
        
        if not directory.exists():
            print(f"错误: 目录 {directory_path} 不存在")
            return
        
        # 查找所有支持的文件
        files = []
        for ext in supported_extensions:
            files.extend(directory.glob(f"*{ext}"))
        
        if not files:
            print(f"在 {directory_path} 目录中未找到支持的文件（支持: {', '.join(supported_extensions)}）")
            return
        
        # 按文件名排序，确保处理顺序一致
        files.sort(key=lambda x: x.name)
        
        total_files = len(files)
        print(f"找到 {total_files} 个文件")
        
        # 应用起始索引和批量大小
        if start_index >= total_files:
            print(f"错误: 起始索引 {start_index} 超出文件总数 {total_files}")
            return
        
        end_index = start_index + batch_size if batch_size else total_files
        files = files[start_index:end_index]
        
        print(f"处理范围: 第 {start_index + 1} 到第 {min(end_index, total_files)} 个文件（共 {len(files)} 个）")
        print(f"切分策略: {strategy}")
        if chunk_size:
            print(f"切分大小: {chunk_size}")
        if chunk_overlap:
            print(f"切分重叠: {chunk_overlap}")
        print(f"跳过已存在文件: {skip_existing}")
        print("-" * 60)
    
    total_chunks = 0
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    # 准备导入参数
    import_kwargs = {}
    if chunk_size:
        import_kwargs["chunk_size"] = chunk_size
    if chunk_overlap:
        import_kwargs["chunk_overlap"] = chunk_overlap
    
    # 顺序处理文件
    for i, file_path in enumerate(files, 1):
        actual_index = start_index + i - 1
        file_name = file_path.name
        doc_id = file_path.stem  # 使用文件名（不含扩展名）作为 doc_id
        
        # 检查文件是否已存在
        if skip_existing and check_document_exists(doc_id):
            print(f"\n[{i}/{len(files)}] (总第 {actual_index + 1}) 跳过: {file_name} (doc_id: {doc_id}, 已存在于知识库)")
            skipped_count += 1
            continue
        
        print(f"\n[{i}/{len(files)}] (总第 {actual_index + 1}) 处理: {file_name}")
        print(f"  文件路径: {file_path}")
        print(f"  文档 ID: {doc_id}")
        
        try:
            # 调用导入函数
            documents = import_file_step(
                file_path=str(file_path),
                strategy=strategy,
                original_filename=file_name,
                **import_kwargs,
            )
            
            if not documents:
                print(f"  ⚠ 未能从文件中提取到内容，跳过此文件")
                error_count += 1
                continue
            
            print(f"  ✓ 成功导入 {len(documents)} 个文档块")
            total_chunks += len(documents)
            success_count += 1
            
        except NotImplementedError as e:
            print(f"  ⚠ 格式暂不支持: {e}")
            error_count += 1
            continue
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
            continue
    
    print("\n" + "=" * 60)
    print("导入完成")
    print("=" * 60)
    print(f"成功: {success_count} 个文件")
    print(f"失败: {error_count} 个文件")
    if skip_existing:
        print(f"跳过: {skipped_count} 个文件（已存在）")
    print(f"总块数: {total_chunks} 个")
    
    # 显示向量数据库信息
    try:
        all_results = vector_store_manager.vector_store._collection.get(include=[])
        total_docs = len(all_results.get("ids", []) or [])
        print(f"\n向量数据库信息:")
        print(f"  集合名称: {settings.CHROMA_COLLECTION_NAME}")
        print(f"  总文档块数: {total_docs}")
    except Exception as e:
        print(f"  获取数据库信息失败: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="批量导入文件到知识库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理所有文件（使用默认 text 策略）
  uv run import_files.py
  
  # 只处理单个文件
  uv run import_files.py --file example.pdf
  uv run import_files.py --file files/example.pdf
  
  # 使用 structured 策略处理单个文件
  uv run import_files.py --file example.pdf --strategy structured
  
  # 从第5个文件开始处理
  uv run import_files.py --start 4
  
  # 只处理前10个文件
  uv run import_files.py --batch-size 10
  
  # 从第5个文件开始，处理10个文件
  uv run import_files.py --start 4 --batch-size 10
  
  # 指定目录和策略
  uv run import_files.py files --start 0 --batch-size 5 --strategy structured
  
  # 跳过已存在的文件
  uv run import_files.py --skip-existing
  
  # 使用自定义切分参数（仅对 text 策略有效）
  uv run import_files.py --strategy text --chunk-size 512 --chunk-overlap 100
        """,
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="files",
        help="文件目录路径（默认: files）",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="从第几个文件开始（从0开始计数，默认: 0）",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="每次处理多少个文件（默认: 处理所有剩余文件）",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="只处理指定的单个文件（可以是文件名或完整路径）",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="跳过已经存在于知识库中的文件",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="text",
        choices=["text", "structured", "table", "heading", "parent_child"],
        help="切分策略（默认: text）",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="切分大小（仅对 text 策略有效，默认使用配置中的值）",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help="切分重叠大小（仅对 text 策略有效，默认使用配置中的值）",
    )
    
    args = parser.parse_args()
    
    import_files_from_directory(
        directory_path=args.directory,
        start_index=args.start,
        batch_size=args.batch_size,
        single_file=args.file,
        skip_existing=args.skip_existing,
        strategy=args.strategy,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
    )
