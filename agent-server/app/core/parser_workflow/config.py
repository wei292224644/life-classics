from typing import List

from typing_extensions import TypedDict


CHUNK_SOFT_MAX_DEFAULT = 1500
CHUNK_HARD_MAX_DEFAULT = 3000
SLICE_HEADING_LEVELS_DEFAULT = [2, 3, 4]


class ParserConfig(TypedDict, total=False):
    chunk_soft_max: int
    chunk_hard_max: int
    slice_heading_levels: List[int]
    classify_model: str
    escalate_model: str
    transform_model: str
    doc_type_llm_model: str
    llm_api_key: str
    llm_base_url: str
    confidence_threshold: float


def get_config_value(config: dict, key: str, default):
    return config.get(key, default)

