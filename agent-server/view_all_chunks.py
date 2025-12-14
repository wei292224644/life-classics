#!/usr/bin/env python3
"""
批量查看多个PDF文档的分割结果
"""
import sys
from pathlib import Path
from app.core.document_loader import DocumentLoader


def view_all_chunks(pdf_dir: str = "test", output_dir: str = "chunks_output"):
    """
    查看目录中所有PDF的分割结果
    
    Args:
        pdf_dir: PDF文件目录
        output_dir: 输出目录
    """
    pdf_dir_path = Path(pdf_dir)
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(exist_ok=True)
    
    # 查找所有PDF文件
    pdf_files = list(pdf_dir_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"在 {pdf_dir} 目录中未找到PDF文件")
        return
    
    print(f"找到 {len(pdf_files)} 个PDF文件\n")
    
    loader = DocumentLoader(split_strategy='structured')
    
    for pdf_file in pdf_files:
        print(f"处理: {pdf_file.name}")
        try:
            # 加载和分割
            documents = loader.load_file(str(pdf_file))
            split_docs = loader.split_documents(documents)
            
            # 统计
            content_types = {}
            for doc in split_docs:
                ct = doc.metadata.get('content_type', 'unknown')
                content_types[ct] = content_types.get(ct, 0) + 1
            
            # 保存结果
            output_file = output_dir_path / f"{pdf_file.stem}_chunks.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"PDF文档: {pdf_file.name}\n")
                f.write("=" * 80 + "\n\n")
                f.write(f"总块数: {len(split_docs)}\n\n")
                f.write("内容类型统计:\n")
                for ct, count in sorted(content_types.items()):
                    f.write(f"  {ct}: {count} 个块\n")
                f.write("\n" + "=" * 80 + "\n")
                f.write("详细内容\n")
                f.write("=" * 80 + "\n\n")
                
                for i, doc in enumerate(split_docs, 1):
                    f.write(f"\n{'='*80}\n")
                    f.write(f"块 #{i}\n")
                    f.write(f"{'='*80}\n\n")
                    f.write(f"类型: {doc.metadata.get('content_type', 'N/A')}\n")
                    f.write(f"章节: {doc.metadata.get('section', 'N/A')}\n")
                    f.write(f"页面: {doc.metadata.get('page_number', 'N/A')}\n")
                    f.write(f"字符数: {len(doc.text)}\n\n")
                    f.write("内容:\n")
                    f.write("-" * 80 + "\n")
                    f.write(doc.text)
                    f.write("\n" + "-" * 80 + "\n")
            
            print(f"  ✓ 分割成 {len(split_docs)} 个块")
            print(f"  ✓ 已保存到: {output_file}")
            print(f"    内容类型: {', '.join(f'{k}({v})' for k, v in sorted(content_types.items()))}\n")
            
        except Exception as e:
            print(f"  ✗ 处理失败: {e}\n")
    
    print(f"\n✅ 所有结果已保存到: {output_dir_path}/")


if __name__ == "__main__":
    pdf_dir = sys.argv[1] if len(sys.argv) > 1 else "test"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "chunks_output"
    
    view_all_chunks(pdf_dir, output_dir)
