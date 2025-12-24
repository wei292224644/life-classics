"""
PDF 文件导入模块
"""

from langchain_core.documents import Document


def import_pdf(file_path: str, strategy: str) -> Document:
    """
    导入 PDF 文件

    Args:
        file_path: PDF 文件路径
        strategy: 切分策略，默认为 text

    Returns:
        知识库通用数据结构列表
    """
    # TODO: 实现 PDF 导入逻辑
    # 判断当前strategy是否为structured
    # 检测是否都为图片，如果是，则使用ocr识别图片内容，然后进行切分
    # 如果为structured，则需要通过LLM分析文档结构，再转化为Markdown格式，然后进行切分
    # 如果不是则进入下一流程
    pass
