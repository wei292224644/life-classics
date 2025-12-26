import json
import time
from typing import Any, List
from enum import Enum

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.llm import chat, get_llm


class ContentType(Enum):
    METADATA = "metadata"  # 文档元信息（标准号、适用对象等）
    SCOPE = "scope"  # 适用范围
    DEFINITION = "definition"  # 概念 / 常数 / 术语定义
    CHEMICAL_FORMULA = "chemical_formula"  # 分子式
    CHEMICAL_STRUCTURE = "chemical_structure"  # 结构式说明
    MOLECULAR_WEIGHT = "molecular_weight"  # 相对分子质量
    SPECIFICATION_TABLE = "specification_table"  # 技术指标 / 限量表格
    SPECIFICATION_TEXT = "specification_text"  # 技术要求（非表格）
    TEST_METHOD = "test_method"  # 检验 / 测定方法
    INSTRUMENT = "instrument"  # 仪器设备
    REAGENT = "reagent"  # 试剂与材料
    CALCULATION_FORMULA = "calculation_formula"  # 计算公式
    GENERAL_RULE = "general_rule"  # 一般规定
    NOTE = "note"  # 注释 / 说明
    CHROMATOGRAPHIC_METHOD = "chromatographic_method"  # 色谱 / 光谱类方法
    IDENTIFICATION_TEST = "identification_test"  # 鉴别试验


class DocumentChunk:
    doc_id: str
    doc_title: str
    section_path: List[str]
    content_type: ContentType
    content: Any
    meta: dict

    def __init__(
        self,
        doc_id: str,
        doc_title: str,
        section_path: List[str],
        content_type: ContentType,
        content: Any,
        meta: dict,
    ):
        self.doc_id = doc_id
        self.doc_title = doc_title
        self.section_path = section_path
        self.content_type = content_type
        self.content = content
        self.meta = meta

    def to_documents(self) -> List[Document]:
        """
        根据 content_type 将 content 转换为 Document 列表

        特殊处理：
        - SPECIFICATION_TABLE: content 是 {"title": "...", "rows": [...]}，每行生成一个 Document
        - CALCULATION_FORMULA: content 是 {"expression": "...", "variables": {...}}，生成一个包含完整公式的 Document
        - REAGENT/INSTRUMENT: content 可能是数组，转换为字符串
        - 其他类型: content 是字符串，直接使用
        """
        content = self.content
        documents = []

        metadata = {
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "section_path": self.section_path,
            "content_type": self.content_type,
            "meta": self.meta,
        }

        # 特殊处理：表格类型
        if self.content_type == ContentType.SPECIFICATION_TABLE:
            return self.specification_table_to_documents(content, metadata)

        # 特殊处理：计算公式类型
        elif self.content_type == ContentType.CALCULATION_FORMULA:
            return self.calculation_formula_to_documents(content, metadata)

        # 处理数组类型（reagent, instrument 等）
        elif isinstance(content, list):
            # 将数组转换为字符串
            page_content = "\n".join(str(item) for item in content)
            document = Document(
                page_content=page_content,
                metadata={
                    **metadata,
                    "raw_content": content,  # 保留原始数组内容
                },
            )
            documents.append(document)

        # 处理字典类型（其他结构化内容）
        elif isinstance(content, dict):
            # 将字典转换为 JSON 字符串
            page_content = json.dumps(content, ensure_ascii=False, indent=2)
            document = Document(
                page_content=page_content,
                metadata={
                    **metadata,
                    "raw_content": content,  # 保留原始字典内容
                },
            )
            documents.append(document)

        # 默认处理：字符串类型
        else:
            # 确保 content 是字符串
            page_content = str(content) if content is not None else ""
            document = Document(
                page_content=page_content,
                metadata={
                    **metadata,
                },
            )
            documents.append(document)

        return documents

    def specification_table_to_documents(
        self, content: dict, metadata: dict
    ) -> List[Document]:
        """
        将表格内容转换为 Document 列表

        Args:
            content: 表格内容，格式为 {"title": "...", "rows": [...]}
            metadata: 文档元数据

        Returns:
            Document 列表，每个表格行生成一个 Document
        """
        if not isinstance(content, dict):
            # 如果不是字典，尝试转换为字符串
            return [
                Document(
                    page_content=str(content),
                    metadata=metadata,
                )
            ]

        rows = content.get("rows", [])
        table_title = content.get("title", "")
        documents = []

        for row in rows:
            # 构建表格行的 JSON 字符串
            row_content_str = json.dumps(
                {"title": table_title, **row}, ensure_ascii=False
            )

            # 使用 LLM 将表格行转换为自然语言描述
            human_prompt = f"""请将这份数据转换为自然语言描述，直接输出结果，不要过分解读和理解。内容为:{row_content_str}"""
            page_content = chat(
                messages=[HumanMessage(content=human_prompt)],
                provider_name="ollama",
                provider_config={
                    "model": "qwen3:1.7b",
                    "temperature": 0.1,
                    "reasoning": False,
                },
            )
            documents.append(
                Document(
                    page_content=page_content,
                    metadata={
                        **metadata,
                        "raw_output": row_content_str,
                        "table_title": table_title,
                    },
                )
            )
        return documents

    def calculation_formula_to_documents(
        self, content: dict, metadata: dict
    ) -> List[Document]:
        """
        将计算公式内容转换为 Document 列表

        Args:
            content: 公式内容，格式为 {"expression": "...", "variables": {...}}
            metadata: 文档元数据

        Returns:
            Document 列表，通常只包含一个 Document（完整的公式和变量说明）
        """
        if not isinstance(content, dict):
            # 如果不是字典，尝试转换为字符串
            return [
                Document(
                    page_content=str(content),
                    metadata=metadata,
                )
            ]

        expression = content.get("expression", "")
        variables = content.get("variables", {})

        # 构建完整的公式文本
        formula_parts = [expression]

        # 如果有变量定义，添加到公式文本中
        if variables:
            var_lines = []
            for symbol, meaning in variables.items():
                var_lines.append(f"- {symbol}: {meaning}")
            if var_lines:
                formula_parts.append("\n变量说明：\n" + "\n".join(var_lines))

        page_content = "\n".join(formula_parts)

        document = Document(
            page_content=page_content,
            metadata={
                **metadata,
                "raw_content": content,  # 保留原始结构化内容
                "expression": expression,
                "variables": variables,
            },
        )

        return [document]


# test

# {
#     "chunk_id": "95bf7c2f090e1b2c",
#     "doc_id": "20120518_10_analysis",
#     "doc_title": "20120518_10_analysis",
#     "section_path": [
#       "3 技术要求",
#       "3.1 感官要求：应符合表1 的规定。",
#       "表1 感官要求"
#     ],
#     "content_type": "specification_table",
#     "content": {
#       "title": "表1 感官要求",
#       "rows": [
#         {
#           "项目": "色泽",
#           "要求": "暗红色至棕红色",
#           "检验方法": "取适量样品置于清洁、干燥的白瓷盘中，在自然光线下，观察其色泽和状态"
#         },
#         {
#           "项目": "状态",
#           "要求": "结晶或结晶性粉末",
#           "检验方法": "取适量样品置于清洁、干燥的白瓷盘中，在自然光线下，观察其色泽和状态"
#         }
#       ]
#     },
#     "meta": {
#       "standard_type": "国家标准",
#       "source": "20120518_10_analysis.md"
#     }
#   }
if __name__ == "__main__":
    document_chunk = DocumentChunk(
        doc_id="20120518_10_analysis",
        doc_title="20120518_10_analysis",
        section_path=["3 技术要求", "3.1 感官要求：应符合表1 的规定。", "表1 感官要求"],
        content_type=ContentType.SPECIFICATION_TABLE,
        content={
            "title": "表1 感官要求",
            "rows": [
                {
                    "项目": "色泽",
                    "要求": "暗红色至棕红色",
                    "检验方法": "取适量样品置于清洁、干燥的白瓷盘中，在自然光线下，观察其色泽和状态",
                },
                {
                    "项目": "状态",
                    "要求": "结晶或结晶性粉末",
                    "检验方法": "取适量样品置于清洁、干燥的白瓷盘中，在自然光线下，观察其色泽和状态",
                },
            ],
        },
        meta={"standard_type": "国家标准", "source": "20120518_10_analysis.md"},
    )
    start_time = time.time()
    documents = document_chunk.to_documents()
    print("=" * 20)
    for document in documents:
        print(document.page_content)
        print("=" * 10)
    print("=" * 20)
    end_time = time.time()
    print("耗时：", end_time - start_time)
    print("文档数量：", len(documents))
