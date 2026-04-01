"""
验证 MiniMax reasoning_split 参数对流式响应的影响。

MiniMax 的 reasoning_split 会输出思维链/推理过程，这些内容可能以特殊
content block 形式返回，不被标准的 text 捕获逻辑处理。

运行方式：
    cd server
    uv run pytest tests/core/parser_workflow/test_minimax_reasoning_split.py -v -s
"""
from __future__ import annotations

import anthropic
from pydantic import BaseModel

from config import settings


class SimpleOutput(BaseModel):
    result: str
    confidence: float


def test_minimax_reasoning_split_stream_events():
    """
    对比 reasoning_split=True/False 时，MiniMax 返回的所有流式事件类型。

    关键问题：当 reasoning_split=True 时，MiniMax 是否会返回非 text 类型的
    content_block_delta？如果是，这些内容会被现有代码忽略（只捕获有 .text 属性的 delta），
    导致 text_response 为空或残缺。
    """
    client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        base_url=settings.ANTHROPIC_BASE_URL,
    )

    prompt = "请将以下文本分类：'这是关于食品添加剂技术要求的文档'。只返回 JSON。"

    # 收集所有事件的函数
    def collect_all_events(extra_body: dict | None) -> list[dict]:
        events = []
        create_kwargs = {
            "model": settings.DEFAULT_MODEL,
            "max_tokens": 102400,
            "temperature": 1.0,
            "system": (
                "你是结构化数据提取助手。严格按以下 JSON Schema 输出，"
                "只返回 JSON 对象，不包含任何解释或 Markdown 代码块。\n\n"
                'Schema:\n{"result": "str", "confidence": "float"}'
            ),
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }
        if extra_body:
            create_kwargs["extra_body"] = extra_body

        with client.messages.create(**create_kwargs) as stream:
            for event in stream:
                # 记录所有事件及其类型
                event_dict = {"type": event.type}
                if hasattr(event, "delta"):
                    delta = event.delta
                    delta_dict = {"delta_type": type(delta).__name__}
                    if hasattr(delta, "text"):
                        delta_dict["text"] = delta.text
                    if hasattr(delta, "thinking"):
                        delta_dict["thinking"] = delta.thinking
                    event_dict["delta"] = delta_dict
                events.append(event_dict)
        return events

    print("\n" + "=" * 60)
    print("测试 reasoning_split=False")
    print("=" * 60)
    events_false = collect_all_events({"enable_thinking": False, "reasoning_split": False})
    text_content_false = []
    non_text_events_false = []
    for ev in events_false:
        if ev["type"] == "content_block_delta":
            delta = ev.get("delta", {})
            if "text" in delta:
                text_content_false.append(delta["text"])
            else:
                non_text_events_false.append(ev)

    print(f"总事件数: {len(events_false)}")
    print(f"text 内容片段数: {len(text_content_false)}")
    print(f"非 text 类型事件数: {len(non_text_events_false)}")
    print(f"合并后 text 内容: {''.join(text_content_false)}")
    if non_text_events_false:
        print(f"非 text 事件示例: {non_text_events_false[:3]}")

    print("\n" + "=" * 60)
    print("测试 reasoning_split=True")
    print("=" * 60)
    events_true = collect_all_events({"enable_thinking": False, "reasoning_split": True})
    text_content_true = []
    non_text_events_true = []
    for ev in events_true:
        if ev["type"] == "content_block_delta":
            delta = ev.get("delta", {})
            if "text" in delta:
                text_content_true.append(delta["text"])
            else:
                non_text_events_true.append(ev)

    print(f"总事件数: {len(events_true)}")
    print(f"text 内容片段数: {len(text_content_true)}")
    print(f"非 text 类型事件数: {len(non_text_events_true)}")
    print(f"合并后 text 内容: {''.join(text_content_true)}")
    if non_text_events_true:
        print(f"非 text 事件示例: {non_text_events_true[:3]}")

    # 断言
    assert len(text_content_true) > 0, "reasoning_split=True 时应该仍有 text 内容"
    assert len(non_text_events_true) > 0, "reasoning_split=True 时应该有非 text 类型的 delta"

    print("\n" + "=" * 60)
    print("结论")
    print("=" * 60)
    print(f"reasoning_split=True 产生了 {len(non_text_events_true)} 个非 text delta")
    print("如果这些 delta 包含关键的 JSON 内容，现有代码会遗漏它们")


def test_minimax_reasoning_split_vs_json_parsing():
    """
    验证 reasoning_split=True 时，JSON 内容是否被正确捕获。

    现有代码只捕获 hasattr(delta, 'text') 的 delta，如果 MiniMax 的 reasoning
    内容不是 text 类型，就会导致 JSON 解析失败。
    """
    client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        base_url=settings.ANTHROPIC_BASE_URL,
    )

    test_cases = [
        "分类：'GB 5009.33 食品安全国家标准 食品中亚硝酸盐和硝酸盐的测定'",
        "分类：'本标准规定了食品添加剂的使用范围和限量要求'",
        "分类：'试剂：盐酸、硝酸、氢氧化钠'",
    ]

    for i, content in enumerate(test_cases):
        print(f"\n--- 测试用例 {i + 1} ---")
        print(f"输入: {content}")

        for reasoning_split in [False, True]:
            extra_body = {"enable_thinking": False, "reasoning_split": reasoning_split}

            text_chunks = []
            create_kwargs = {
                "model": settings.DEFAULT_MODEL,
                "max_tokens": 102400,
                "temperature": 1.0,
                "system": (
                    "你是结构化数据提取助手。严格按以下 JSON Schema 输出，"
                    "只返回 JSON 对象，不包含任何解释或 Markdown 代码块。\n\n"
                    'Schema:\n{"result": "str", "confidence": "float"}'
                ),
                "messages": [{"role": "user", "content": content}],
                "stream": True,
                "extra_body": extra_body,
            }

            try:
                with client.messages.create(**create_kwargs) as stream:
                    for event in stream:
                        if event.type == "content_block_delta":
                            delta = event.delta
                            if hasattr(delta, "text"):
                                text_chunks.append(delta.text)
                        elif event.type == "message_stop":
                            break

                text_response = "".join(text_chunks).strip()
                print(f"  reasoning_split={reasoning_split}: text_response={text_response[:200]!r}")

                # 尝试解析 JSON
                import json
                try:
                    parsed = json.loads(text_response)
                    print(f"  JSON 解析成功: {parsed}")
                except json.JSONDecodeError as e:
                    print(f"  JSON 解析失败: {e}")
                    if reasoning_split:
                        print(f"  >>> reasoning_split=True 时 JSON 解析失败，可能丢失了关键内容 <<<")

            except Exception as e:
                print(f"  reasoning_split={reasoning_split}: 错误 - {e}")


if __name__ == "__main__":
    test_minimax_reasoning_split_stream_events()
    print("\n\n")
    test_minimax_reasoning_split_vs_json_parsing()
