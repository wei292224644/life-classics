#!/usr/bin/env python3
"""
批量导入 files 目录下的所有 PDF 文件到向量数据库（多线程版本）
"""
import sys
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from app.core.document_loader import document_loader
from app.core.vector_store import vector_store_manager
from app.core.config import settings


# 全局锁，用于保护共享资源（打印输出和统计信息）
print_lock = Lock()
stats_lock = Lock()


def process_single_file(
    pdf_file: Path,
    file_index: int,
    total_files: int,
    start_index: int,
    stats: dict,
):
    """
    处理单个 PDF 文件
    
    Args:
        pdf_file: PDF 文件路径
        file_index: 文件在当前批次中的索引（从1开始）
        total_files: 总文件数
        start_index: 起始索引
        stats: 共享统计字典，包含 success_count, error_count, total_chunks
    """
    actual_index = start_index + file_index
    file_name = pdf_file.name
    
    with print_lock:
        print(f"\n[{file_index}/{total_files}] (总第 {actual_index}) 处理: {file_name}")
    
    try:
        # 加载文档
        documents = document_loader.load_file(str(pdf_file))
        
        with print_lock:
            print(f"  [{file_name}] ✓ 加载成功，共 {len(documents)} 页")

        if settings.ENABLE_PARENT_CHILD:
            # 父子模式：由 VectorStoreManager 生成父/子结构（父->SQLite，子->Chroma）
            vector_store_manager.add_documents(documents)
            with print_lock:
                print(f"  [{file_name}] ✓ 父子模式已入库（父->SQLite，子->Chroma）")
        else:
            # 分割文档
            split_docs = document_loader.split_documents(documents)
            with print_lock:
                print(f"  [{file_name}] ✓ 分割成功，共 {len(split_docs)} 个块")

            # 添加到向量存储
            vector_store_manager.add_documents(split_docs)
            with print_lock:
                print(f"  [{file_name}] ✓ 已添加到向量数据库")

            with stats_lock:
                stats['total_chunks'] += len(split_docs)
        
        with stats_lock:
            stats['success_count'] += 1
        
    except Exception as e:
        with print_lock:
            print(f"  [{file_name}] ✗ 处理失败: {e}")
            import traceback
            traceback.print_exc()
        
        with stats_lock:
            stats['error_count'] += 1


def import_pdfs_from_directory(
    directory_path: str = "files",
    start_index: int = 0,
    batch_size: int = 10,
    max_workers: int = 4,
):
    """
    导入目录下所有 PDF 文件到向量数据库（多线程版本）
    
    Args:
        directory_path: PDF 文件目录路径
        start_index: 从第几个文件开始（从0开始计数）
        batch_size: 每次处理多少个文件，如果为 None 则处理所有剩余文件
        max_workers: 最大线程数（默认: 4）
    """
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
    print(f"线程数: {max_workers}")
    print(f"父子chunk模式: {settings.ENABLE_PARENT_CHILD}")
    if settings.ENABLE_PARENT_CHILD:
        print(f"父chunk大小: {settings.PARENT_CHUNK_SIZE}, 子chunk大小: {settings.CHILD_CHUNK_SIZE}")
    print("-" * 60)
    
    # 共享统计信息
    stats = {
        'success_count': 0,
        'error_count': 0,
        'total_chunks': 0,
    }
    
    # 使用线程池并发处理文件
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = []
        for i, pdf_file in enumerate(pdf_files, 1):
            future = executor.submit(
                process_single_file,
                pdf_file,
                i,
                len(pdf_files),
                start_index,
                stats,
            )
            futures.append(future)
        
        # 等待所有任务完成
        for future in as_completed(futures):
            try:
                future.result()  # 获取结果，如果有异常会在这里抛出
            except Exception as e:
                # 这个异常应该已经在 process_single_file 中处理了
                pass
    
    print("\n" + "=" * 60)
    print("导入完成")
    print("=" * 60)
    print(f"成功: {stats['success_count']} 个文件")
    print(f"失败: {stats['error_count']} 个文件")
    print(f"总块数: {stats['total_chunks']} 个")
    
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
  # 处理所有文件（使用4个线程）
  python import_files.py
  
  # 从第5个文件开始处理
  python import_files.py --start 4
  
  # 只处理前10个文件，使用8个线程
  python import_files.py --batch-size 10 --workers 8
  
  # 从第5个文件开始，处理10个文件，使用2个线程
  python import_files.py --start 4 --batch-size 10 --workers 2
  
  # 指定目录
  python import_files.py files --start 0 --batch-size 5 --workers 4
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
        "--workers",
        type=int,
        default=4,
        help="最大线程数（默认: 4）",
    )
    
    args = parser.parse_args()
    
    import_pdfs_from_directory(
        directory_path=args.directory,
        start_index=args.start,
        batch_size=args.batch_size,
        max_workers=args.workers,
    )

