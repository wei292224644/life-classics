#!/usr/bin/env python3
"""
查看PDF文档分割后的所有块内容
"""
import sys
from pathlib import Path
from app.core.document_loader import DocumentLoader


def view_chunks(pdf_path: str, output_file: str = None):
    """
    查看PDF分割后的所有块
    
    Args:
        pdf_path: PDF文件路径
        output_file: 可选，输出文件路径（如果不提供，则输出到控制台）
    """
    if not Path(pdf_path).exists():
        print(f"错误: 文件 {pdf_path} 不存在")
        return
    
    print(f"正在处理: {pdf_path}")
    loader = DocumentLoader(split_strategy='structured')
    
    # 加载文档
    print("加载PDF文档...")
    documents = loader.load_file(pdf_path)
    print(f"✓ 加载成功，共 {len(documents)} 页")
    
    # 分割文档
    print("分割文档...")
    split_docs = loader.split_documents(documents)
    print(f"✓ 分割成功，共 {len(split_docs)} 个块\n")
    
    # 统计信息
    content_types = {}
    sections = set()
    for doc in split_docs:
        ct = doc.metadata.get('content_type', 'unknown')
        content_types[ct] = content_types.get(ct, 0) + 1
        section = doc.metadata.get('section')
        if section:
            sections.add(section)
    
    # 准备输出内容
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append(f"PDF文档分割结果: {Path(pdf_path).name}")
    output_lines.append("=" * 80)
    output_lines.append(f"\n总块数: {len(split_docs)}")
    output_lines.append(f"\n内容类型统计:")
    for ct, count in sorted(content_types.items()):
        output_lines.append(f"  {ct}: {count} 个块")
    
    if sections:
        output_lines.append(f"\n章节列表 ({len(sections)} 个):")
        for section in sorted(sections):
            output_lines.append(f"  - {section}")
    
    output_lines.append("\n" + "=" * 80)
    output_lines.append("详细内容")
    output_lines.append("=" * 80 + "\n")
    
    # 输出每个块的详细信息
    for i, doc in enumerate(split_docs, 1):
        output_lines.append(f"\n{'='*80}")
        output_lines.append(f"块 #{i}")
        output_lines.append(f"{'='*80}")
        
        # 元数据
        metadata = doc.metadata
        output_lines.append(f"\n元数据:")
        output_lines.append(f"  内容类型: {metadata.get('content_type', 'N/A')}")
        output_lines.append(f"  章节: {metadata.get('section', 'N/A')}")
        output_lines.append(f"  页面: {metadata.get('page_number', 'N/A')}")
        if 'table_id' in metadata:
            output_lines.append(f"  表格ID: {metadata.get('table_id')}")
        output_lines.append(f"  块ID: {metadata.get('chunk_id', i-1)}")
        output_lines.append(f"  字符数: {len(doc.text)}")
        
        # 内容
        output_lines.append(f"\n内容:")
        output_lines.append("-" * 80)
        # 如果是表格，保持原样；否则每行显示
        if metadata.get('content_type') == 'table':
            output_lines.append(doc.text)
        else:
            # 按行显示，每行最多80字符
            lines = doc.text.split('\n')
            for line in lines:
                if len(line) > 80:
                    # 长行自动换行
                    words = line.split()
                    current_line = ""
                    for word in words:
                        if len(current_line + word) > 80:
                            if current_line:
                                output_lines.append(current_line)
                            current_line = word + " "
                        else:
                            current_line += word + " "
                    if current_line:
                        output_lines.append(current_line)
                else:
                    output_lines.append(line)
        output_lines.append("-" * 80)
    
    # 输出结果
    output_text = "\n".join(output_lines)
    
    if output_file:
        # 保存到文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_text)
        print(f"\n✓ 结果已保存到: {output_file}")
    else:
        # 输出到控制台
        print(output_text)
        
        # 如果内容太长，提示可以保存到文件
        if len(split_docs) > 10:
            print(f"\n提示: 内容较多，可以使用以下命令保存到文件:")
            print(f"  python view_chunks.py {pdf_path} output.txt")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python view_chunks.py <pdf文件路径> [输出文件路径]")
        print("\n示例:")
        print("  python view_chunks.py test/20120518_2.pdf")
        print("  python view_chunks.py test/20120518_2.pdf output.txt")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    view_chunks(pdf_path, output_file)
