import json
from typing import Any, List
from enum import Enum

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.llm import chat, get_llm


class ContentType(Enum):
    METADATA = "metadata"
    SCOPE = "scope"
    DEFINITION = "definition"
    CHEMICAL_FORMULA = "chemical_formula"
    CHEMICAL_STRUCTURE = "chemical_structure"
    MOLECULAR_WEIGHT = "molecular_weight"
    SPECIFICATION_TABLE = "specification_table"
    SPECIFICATION_TEXT = "specification_text"
    TEST_METHOD = "test_method"
    INSTRUMENT = "instrument"
    REAGENT = "reagent"
    CALCULATION_FORMULA = "calculation_formula"
    GENERAL_RULE = "general_rule"
    NOTE = "note"
    CHROMATOGRAPHIC_METHOD = "chromatographic_method"
    IDENTIFICATION_TEST = "identification_test"


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

        content = self.content
        documents = []

        metadata = {
            "doc_id": self.doc_id,
            "doc_title": self.doc_title,
            "section_path": self.section_path,
            "content_type": self.content_type,
            "meta": self.meta,
        }

        if self.content_type == ContentType.SPECIFICATION_TABLE:
            return self.specification_table_to_documents(content, metadata)
        else:
            document = Document(
                page_content=content,
                metadata={
                    **metadata,
                },
            )
            documents.append(document)

        return documents

    def specification_table_to_documents(
        self, content: dict, metadata: dict
    ) -> List[Document]:
        rows = content.get("rows", [])
        documents = []

        for row in rows:
            row_content_str = json.dumps(
                {"title": content.get("title", "表中："), **row}, ensure_ascii=False
            )
            human_prompt = f"""请将这份数据转换为自然语言描述，直接输出结果，不要过分解读和理解。内容为:{row_content_str}"""
            page_content = chat(
                messages=[HumanMessage(content=human_prompt)],
                provider_name="ollama",
                provider_config={"model": "qwen3:0.6b"},
            )
            documents.append(
                Document(
                    page_content=page_content,
                    metadata={
                        **metadata,
                        "raw_output": row_content_str,
                    },
                )
            )
        return documents


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
    print(document_chunk.to_documents())
