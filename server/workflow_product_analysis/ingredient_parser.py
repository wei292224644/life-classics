"""组件 2：LLM 成分解析 — 从 OCR 文字提取成分名列表和商品品名。"""
from __future__ import annotations

from pydantic import BaseModel

from config import Settings
from worflow_parser_kb.structured_llm.client_factory import get_structured_client


class NoIngredientsFoundError(Exception):
    """OCR 文字中找不到配料表，管道捕获后写入 error='no_ingredients_found'。"""


class ParseResult:
    def __init__(self, ingredients: list[str], product_name: str | None):
        self.ingredients = ingredients
        self.product_name = product_name


# ── Instructor 输出模型 ──────────────────────────────────────────────────────

class IngredientParseOutput(BaseModel):
    ingredients: list[str]
    """
    提取的成分名列表。去掉括号内功能说明。
    例：["燕麦粉", "麦芽糊精", "阿斯巴甜"]（不是 "阿斯巴甜（甜味剂）"）
    """
    product_name: str | None = None
    """商品品名，从包装文字提取，可能为 None。"""


# ── 核心函数 ─────────────────────────────────────────────────────────────────

async def parse_ingredients(ocr_text: str, settings: Settings) -> ParseResult:
    """
    用 LLM + 结构化输出从 OCR 文字中提取成分名列表和商品品名。

    入参：
        ocr_text: 原始 OCR 文字（含配料表、品名、营养成分等所有文字）
        settings: 配置（含 LLM 连接信息）

    出参：
        ParseResult: .ingredients（成分名列表）和 .product_name（商品品名，可 None）

    异常：
        NoIngredientsFoundError: LLM 返回空成分列表时抛出
    """
    provider = "anthropic"
    model = settings.DEFAULT_MODEL

    # get_structured_client 返回同步 callable：
    # create(model=..., messages=..., response_model=..., temperature=...) -> BaseModel
    create_fn = get_structured_client(provider=provider, model=model)

    prompt = f"""从以下食品包装 OCR 文字中提取信息：

OCR 文字：
{ocr_text}

请提取：
1. 配料表中的所有成分名（去掉括号内的功能说明，如"阿斯巴甜（甜味剂）"→"阿斯巴甜"）
2. 商品品名（产品名称，若能识别）

若找不到配料表，返回空列表。"""

    result: IngredientParseOutput = create_fn(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_model=IngredientParseOutput,
    )

    if not result.ingredients:
        raise NoIngredientsFoundError("No ingredients found in OCR text")

    return ParseResult(
        ingredients=result.ingredients,
        product_name=result.product_name,
    )
