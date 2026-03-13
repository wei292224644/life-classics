"""
文档类型分类工具：供 Agent 在对话中按需调用，判断某份标准文档属于哪一类（单添加剂/检测方法/微生物/产品/other）。
可与 knowledge_base 等配合编排：先判类型再选检索策略或直接回答「这是什么类型标准」。
"""

from langchain_core.tools import tool

from app.core.kb.strategy.doc_type import infer_document_type_for_agent


@tool
def document_type(filename: str, heading_summary: str = "") -> str:
    """
    根据文件名和可选的章节摘要，判断该标准文档的类型。适合在用户询问「这份文档是什么类型」「属于哪类标准」时使用，
    或在需要按文档类型选择检索/解释策略时先调用本工具。

    Args:
        filename: 文档文件名或标准号（如「GB 8821-2011 食品添加剂 β-胡萝卜素.md」）
        heading_summary: 可选的章节/目录摘要（如从检索结果或用户提供的目录中截取），有助于更准确分类；为空时仅根据文件名用规则推断

    Returns:
        文档类型英文标识：single_additive（单添加剂）、detection_method（检测方法）、microbiological（微生物检验）、product（产品）、other
    """
    return infer_document_type_for_agent(filename, heading_summary)
