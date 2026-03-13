"""文档类型推断：支持规则与 Agent（LLM）两种方式，Agent 可覆盖更多非标情况，规则作兜底。"""

import re
from typing import Callable, Optional

# 允许的类型，与规范 3.1～3.3 一致
DOC_TYPES = ("single_additive", "detection_method", "microbiological", "product", "other")


def infer_doc_type(
    filename: str,
    first_heading: str | None,
    section_paths: list[list[str]],
) -> str:
    """仅用规则根据文件名与章节路径推断类型，难以覆盖所有情况。"""
    name_lower = (filename + " " + (first_heading or "")).lower()
    paths_str = " ".join(" ".join(p) for p in section_paths).lower()

    if "4789" in name_lower or "微生物" in name_lower or "沙门" in name_lower or "检验程序" in paths_str:
        return "microbiological"
    if (
        any(x in name_lower for x in ["5009", "23200", "31604", "31659"])
        or "测定" in name_lower
        or "检测" in name_lower
        or "第一法" in paths_str
        or "液相色谱" in paths_str
    ):
        return "detection_method"
    if (
        any(x in name_lower for x in ["1886", "8821", "29972"])
        or "食品添加剂" in name_lower
        or ("附录 a" in paths_str and "鉴别" in paths_str)
    ):
        return "single_additive"
    if "31636" in name_lower or "花粉" in name_lower or "产品" in name_lower:
        return "product"
    return "other"


def _build_heading_summary(first_heading: str | None, section_paths: list[list[str]], max_items: int = 30) -> str:
    """把首标题与章节路径拼成一段摘要，供 Agent 判断。"""
    parts = []
    if first_heading:
        parts.append(f"首标题: {first_heading}")
    if section_paths:
        flat = [p for path in section_paths[:max_items] for p in path]
        parts.append("章节: " + " | ".join(flat[:max_items]))
    return "\n".join(parts) if parts else ""


def _parse_agent_type(text: str) -> Optional[str]:
    """从 LLM 回复中解析出文档类型（必须为 DOC_TYPES 之一）。"""
    t = text.strip().lower()
    for candidate in DOC_TYPES:
        if candidate in t or candidate.replace("_", " ") in t:
            return candidate
    # 常见中文/混写
    if "单添加剂" in t or "添加剂" in t and "产品" not in t:
        return "single_additive"
    if "检测方法" in t or "测定" in t:
        return "detection_method"
    if "微生物" in t or "检验" in t and "程序" in t:
        return "microbiological"
    if "产品" in t or "花粉" in t:
        return "product"
    return "other"


def infer_doc_type_with_agent(
    filename: str,
    first_heading: str | None,
    section_paths: list[list[str]],
    chat_fn: Optional[Callable[..., str]] = None,
) -> Optional[str]:
    """
    用 LLM 根据文件名与章节摘要判断文档类型，能覆盖规则难以处理的非标命名、修改单等。
    失败（超时、解析不出）时返回 None，由调用方用规则兜底。
    """
    summary = _build_heading_summary(first_heading, section_paths)
    prompt = f"""你是一个文档分类助手。根据「文件名」和「章节摘要」判断这份文档属于以下哪一种类型，只回复类型英文标识，不要解释。

类型说明：
- single_additive：单添加剂/食品添加剂类标准（如某一种添加剂的质量规格、检验方法）
- detection_method：检测/测定方法标准（如某成分的测定、液相色谱法）
- microbiological：微生物检验/流程类标准（如沙门氏菌检验、检验程序）
- product：产品标准（如花粉、某类食品产品）
- other：以上都不是

文件名：{filename}

{summary}

只回复一个类型标识："""

    try:
        from langchain_core.messages import HumanMessage

        if chat_fn is None:
            from app.core.config import settings
            from app.core.llm import chat

            provider = getattr(settings, "CHAT_PROVIDER", "dashscope")
            model = getattr(settings, "DOC_TYPE_AGENT_MODEL", "") or getattr(settings, "CHAT_MODEL", "")
            timeout = getattr(settings, "DOC_TYPE_AGENT_TIMEOUT", 15)
            raw = chat(
                [HumanMessage(content=prompt)],
                provider_name=provider,
                model=model,
                provider_config={"request_timeout": timeout} if timeout else {},
            )
        else:
            raw = chat_fn(prompt)

        if isinstance(raw, list):
            raw = raw[0] if raw and isinstance(raw[0], str) else str(raw)
        result = _parse_agent_type(str(raw))
        return result if result in DOC_TYPES else "other"
    except Exception:
        return None


def infer_doc_type_auto(
    filename: str,
    first_heading: str | None,
    section_paths: list[list[str]],
    chat_fn: Optional[Callable[..., str]] = None,
    inference_mode: Optional[str] = None,
) -> str:
    """
    统一入口：按配置优先用 Agent 判断，失败或未配置则用规则兜底，保证总能返回一个类型。
    inference_mode 不为 None 时优先使用（单测可传 "agent_then_rule" 等，避免依赖 config）。
    """
    if inference_mode is None:
        from app.core.config import settings
        mode = getattr(settings, "DOC_TYPE_INFERENCE", "agent_then_rule").strip().lower()
    else:
        mode = inference_mode.strip().lower()

    if mode == "rule":
        return infer_doc_type(filename, first_heading, section_paths)

    if mode in ("agent", "agent_then_rule"):
        t = infer_doc_type_with_agent(filename, first_heading, section_paths, chat_fn=chat_fn)
        if t is not None:
            return t

    return infer_doc_type(filename, first_heading, section_paths)


def infer_document_type_for_agent(filename: str, heading_summary: str = "") -> str:
    """
    供 Agent 作为 tool 调用：根据文件名与可选「章节/摘要」判断文档类型。
    当 heading_summary 非空时优先用 LLM 判断，失败则用规则（仅文件名）；空时仅用规则。
    """
    if not (heading_summary or "").strip():
        return infer_doc_type(filename, None, [])
    try:
        from langchain_core.messages import HumanMessage

        from app.core.config import settings
        from app.core.llm import chat

        prompt = f"""你是一个文档分类助手。根据「文件名」和「章节摘要」判断这份文档属于以下哪一种类型，只回复类型英文标识，不要解释。

类型说明：
- single_additive：单添加剂/食品添加剂类标准（如某一种添加剂的质量规格、检验方法）
- detection_method：检测/测定方法标准（如某成分的测定、液相色谱法）
- microbiological：微生物检验/流程类标准（如沙门氏菌检验、检验程序）
- product：产品标准（如花粉、某类食品产品）
- other：以上都不是

文件名：{filename}

章节摘要：
{heading_summary.strip()[:2000]}

只回复一个类型标识："""

        provider = getattr(settings, "CHAT_PROVIDER", "dashscope")
        model = getattr(settings, "DOC_TYPE_AGENT_MODEL", "") or getattr(settings, "CHAT_MODEL", "")
        timeout = getattr(settings, "DOC_TYPE_AGENT_TIMEOUT", 15)
        raw = chat(
            [HumanMessage(content=prompt)],
            provider_name=provider,
            model=model,
            provider_config={"request_timeout": timeout} if timeout else {},
        )
        if isinstance(raw, list):
            raw = raw[0] if raw and isinstance(raw[0], str) else str(raw)
        result = _parse_agent_type(str(raw))
        if result in DOC_TYPES:
            return result
    except Exception:
        pass
    return infer_doc_type(filename, None, [])
