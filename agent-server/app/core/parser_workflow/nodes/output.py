from typing import List, Literal
from pydantic import BaseModel, Field


class TransformParams(BaseModel):
    strategy: str
    prompt_template: str


class TransformOutput(BaseModel):
    content: str

class DocTypeOutput(BaseModel):
    id: str
    description: str
    detect_keywords: List[str]
    detect_heading_patterns: List[str]


class EscalateOutput(BaseModel):
    """LLM 结构化输出，需与 prompt 中的 format_example 一致。"""

    action: Literal["use_existing", "create_new"]
    id: str
    description: str
    transform: TransformParams



class SegmentItem(BaseModel):
    content: str
    content_type: str
    confidence: float = Field(
        default=0.8,
        ge=0,
        le=1
    )

class ClassifyOutput(BaseModel):
    segments: List[SegmentItem]