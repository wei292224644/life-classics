#!/usr/bin/env python3
"""
批量导入 files 目录下的所有 PDF 文件到向量数据库
"""
import sys
from pathlib import Path
from app.core.document_loader import document_loader
from app.core.vector_store import vector_store_manager
from app.core.config import settings


def import_pdfs_from_directory(directory_path: str = "files"):
    """
    导入目录下所有 PDF 文件到向量数据库
    
    Args:
        directory_path: PDF 文件目录路径
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
    
    print(f"找到 {len(pdf_files)} 个 PDF 文件")
    print(f"父子chunk模式: {settings.ENABLE_PARENT_CHILD}")
    if settings.ENABLE_PARENT_CHILD:
        print(f"父chunk大小: {settings.PARENT_CHUNK_SIZE}, 子chunk大小: {settings.CHILD_CHUNK_SIZE}")
    print("-" * 60)
    
    total_chunks = 0
    success_count = 0
    error_count = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}] 处理: {pdf_file.name}")
        
        try:
            # 加载文档
            documents = document_loader.load_file(str(pdf_file))
            print(f"  ✓ 加载成功，共 {len(documents)} 页")
            
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
            error_count += 1
            import traceback
            traceback.print_exc()
            continue
    
    print("\n" + "=" * 60)
    print("导入完成")
    print("=" * 60)
    print(f"成功: {success_count} 个文件")
    print(f"失败: {error_count} 个文件")
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
    directory = sys.argv[1] if len(sys.argv) > 1 else "files"
    import_pdfs_from_directory(directory)

