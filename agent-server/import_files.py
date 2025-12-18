#!/usr/bin/env python3
"""
批量导入 files 目录下的所有 PDF 文件到向量数据库
"""
import sys
import argparse
from pathlib import Path
from app.core.document_loader import document_loader
from app.core.vector_store import vector_store_manager
from app.core.config import settings


def import_pdfs_from_directory(
    directory_path: str = "files",
    start_index: int = 0,
    batch_size: int = 10,
    single_file: str = None,
    skip_existing: bool = False,
):
    """
    导入目录下所有 PDF 文件到向量数据库
    
    Args:
        directory_path: PDF 文件目录路径
        start_index: 从第几个文件开始（从0开始计数）
        batch_size: 每次处理多少个文件，如果为 None 则处理所有剩余文件
        single_file: 如果指定，则只处理这个文件（可以是文件名或完整路径）
        skip_existing: 是否跳过已经存在于知识库中的文件
    """
    # 如果指定了单个文件，优先处理单个文件
    if single_file:
        pdf_file = Path(single_file)
        
        # 如果文件路径不是绝对路径，尝试在指定目录中查找
        if not pdf_file.is_absolute():
            directory = Path(directory_path)
            pdf_file = directory / pdf_file
        
        # 如果文件不存在，尝试添加 .pdf 扩展名
        if not pdf_file.exists() and not pdf_file.suffix:
            pdf_file = pdf_file.with_suffix('.pdf')
        
        if not pdf_file.exists():
            print(f"错误: 文件 {pdf_file} 不存在")
            return
        
        if not pdf_file.suffix.lower() == '.pdf':
            print(f"错误: 文件 {pdf_file} 不是 PDF 文件")
            return
        
        pdf_files = [pdf_file]
        print(f"处理单个文件: {pdf_file.name}")
        print(f"文件路径: {pdf_file}")
        print(f"父子chunk模式: {settings.ENABLE_PARENT_CHILD}")
        if settings.ENABLE_PARENT_CHILD:
            print(f"父chunk大小: {settings.PARENT_CHUNK_SIZE}, 子chunk大小: {settings.CHILD_CHUNK_SIZE}")
        print(f"跳过已存在文件: {skip_existing}")
        
        # 检查单个文件是否已存在
        if skip_existing and vector_store_manager.file_exists(pdf_file.name):
            print(f"\n文件 {pdf_file.name} 已存在于知识库中，跳过处理")
            return
        
        print("-" * 60)
        start_index = 0
    else:
        directory = Path(directory_path)
        
        if not directory.exists():
            print(f"错误: 目录 {directory_path} 不存在")
            return
        
        # 查找所有 PDF 文件
        pdf_files = list(directory.glob("*.pdf"))
        
        if not pdf_files:
            print(f"在 {directory_path} 目录中未找到 PDF 文件")
            return
        
        # 按文件名排序，确保处理顺序一致
        pdf_files.sort(key=lambda x: x.name)
        
        total_files = len(pdf_files)
        print(f"找到 {total_files} 个 PDF 文件")
        
        # 应用起始索引和批量大小
        if start_index >= total_files:
            print(f"错误: 起始索引 {start_index} 超出文件总数 {total_files}")
            return
        
        end_index = start_index + batch_size if batch_size else total_files
        pdf_files = pdf_files[start_index:end_index]
        
        print(f"处理范围: 第 {start_index + 1} 到第 {min(end_index, total_files)} 个文件（共 {len(pdf_files)} 个）")
        print(f"父子chunk模式: {settings.ENABLE_PARENT_CHILD}")
        if settings.ENABLE_PARENT_CHILD:
            print(f"父chunk大小: {settings.PARENT_CHUNK_SIZE}, 子chunk大小: {settings.CHILD_CHUNK_SIZE}")
        print(f"跳过已存在文件: {skip_existing}")
        print("-" * 60)
    
    total_chunks = 0
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    # 顺序处理文件
    for i, pdf_file in enumerate(pdf_files, 1):
        actual_index = start_index + i
        file_name = pdf_file.name
        
        # 检查文件是否已存在
        if skip_existing and vector_store_manager.file_exists(file_name):
            print(f"\n[{i}/{len(pdf_files)}] (总第 {actual_index}) 跳过: {file_name} (已存在于知识库)")
            skipped_count += 1
            continue
        
        print(f"\n[{i}/{len(pdf_files)}] (总第 {actual_index}) 处理: {file_name}")
        
        try:
            # 加载文档
            documents = document_loader.load_file(str(pdf_file))
            print(f"  ✓ 加载成功，共 {len(documents)} 页")

            if settings.ENABLE_PARENT_CHILD:
                # 父子模式：由 VectorStoreManager 生成父/子结构（父->SQLite，子->Chroma）
                vector_store_manager.add_documents(documents)
                print("  ✓ 父子模式已入库（父->SQLite，子->Chroma）")
            else:
                # 分割文档
                split_docs = document_loader.split_documents(documents)
                print(f"  ✓ 分割成功，共 {len(split_docs)} 个块")

                # 添加到向量存储
                vector_store_manager.add_documents(split_docs)
                print(f"  ✓ 已添加到向量数据库")

                total_chunks += len(split_docs)
            success_count += 1
            
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
        info = vector_store_manager.get_collection_info()
        print(f"\n向量数据库信息:")
        print(f"  集合名称: {info['collection_name']}")
        print(f"  文档总数: {info['document_count']}")
    except Exception as e:
        print(f"  获取数据库信息失败: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="批量导入 PDF 文件到向量数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 处理所有文件
  python import_files.py
  
  # 只处理单个文件
  python import_files.py --file example.pdf
  python import_files.py --file files/example.pdf
  python import_files.py files --file example.pdf
  
  # 从第5个文件开始处理
  python import_files.py --start 4
  
  # 只处理前10个文件
  python import_files.py --batch-size 10
  
  # 从第5个文件开始，处理10个文件
  python import_files.py --start 4 --batch-size 10
  
  # 指定目录
  python import_files.py files --start 0 --batch-size 5
  
  # 跳过已存在的文件
  python import_files.py --skip-existing
        """,
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="files",
        help="PDF 文件目录路径（默认: files）",
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
        help="只处理指定的单个 PDF 文件（可以是文件名或完整路径）",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="跳过已经存在于知识库中的文件",
    )
    
    args = parser.parse_args()
    
    import_pdfs_from_directory(
        directory_path=args.directory,
        start_index=args.start,
        batch_size=args.batch_size,
        single_file=args.file,
        skip_existing=args.skip_existing,
    )

