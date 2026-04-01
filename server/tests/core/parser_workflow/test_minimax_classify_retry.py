"""
真实业务场景测试：验证 classify_node 对真实 chunk 内容的 LLM 调用行为。

使用真实的 GB 标准 markdown 文件和规则文件，模拟 classify_node 的行为，
重点观察：
1. 是否有重试发生
2. 重试的原因是什么

运行方式：
    cd server
    uv run pytest tests/core/parser_workflow/test_minimax_classify_retry.py -v -s
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import anthropic
from pydantic import BaseModel

# ── 配置 ──────────────────────────────────────────────────────────────────────
# 使用与 classify_node 相同的配置
RULES_DIR = Path(__file__).resolve().parents[3] / "app" / "core" / "parser_workflow" / "rules"

# ── 测试用的真实 markdown 文件 ─────────────────────────────────────────────────
TEST_ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"


class SegmentItem(BaseModel):
    content: str
    structure_type: str
    semantic_type: str
    confidence: float = 0.8


class ClassifyOutput(BaseModel):
    segments: list[SegmentItem]


def load_rules(rules_dir: Path) -> tuple[list[dict], list[dict]]:
    """加载结构类型和语义类型规则。"""
    content_type_file = rules_dir / "content_type_rules.json"
    with open(content_type_file, encoding="utf-8") as f:
        rules = json.load(f)
    return rules.get("structure_types", []), rules.get("semantic_types", [])


def _build_type_desc(types: list[dict]) -> str:
    lines = []
    for t in types:
        lines.append(f"- {t['id']}: {t['description']}")
        if t.get("examples"):
            examples_str = " / ".join(t["examples"])
            lines.append(f"  示例：{examples_str}")
    return "\n".join(lines)


def _escape_for_json_prompt(text: str) -> str:
    return text.replace('"', '\\"')


def build_classify_prompt(chunk_content: str, structure_types: list[dict], semantic_types: list[dict]) -> str:
    """构建与 classify_node 相同的 prompt。"""
    structure_desc = "\n".join(f"- {t['id']}: {t['description']}" for t in structure_types)
    semantic_desc = _build_type_desc(semantic_types)

    return f"""请将以下文本拆分为语义独立的片段，并对每个片段进行双维度分类。

【结构类型（structure_type）】——描述内容的呈现形式：
{structure_desc}

【语义类型（semantic_type）】——描述内容对读者的用途：
{semantic_desc}

分类规则（按优先级从高到低）：

【强制规则，这些情况下必须合并且不得拆分】
1. 公式块：文本中出现 $$...$$ 公式时，公式及其前导引导句（如"按下式计算："）、变量说明（"式中：X——..."格式）、注释（"注："格式）必须合并为同一个 segment，structure_type=formula，semantic_type=calculation。
2. 步骤链：编号呈递进的相邻步骤（如 A.2.2.1 → A.2.2.2，或 3.1 → 3.2），且后一步引用前一步产物（如"取上一步溶液"、"将前述沉淀..."、"按 A.X.X.1 方法..."），必须合并为单一 procedure segment。
3. 标题行不得单独成段：章节标题（如 ## A.2、### A.2.2）必须与其后的首个内容片段合并；纯标题无内容时则保留。

【切分原则】
4. 极保守切分：只有在以下情况才切分——相邻内容属于截然不同的 semantic_type（如 limit → procedure，或 material → procedure），且各自内容足够独立。满足以下任一条件时禁止切分：同一检测方法的 试剂/步骤/仪器/结果计算、连续步骤之间存在数据或引用传递、"见第X条"等内部引用。
5. 双维度先推断结构再推断用途：structure_type 决定内容呈现形式，semantic_type 决定读者用途，两者非独立——formula 必然是 calculation，header 仅用于 metadata，procedure 可包含 limit 注释（如"注：..."）。
6. confidence 反映综合把握程度（0-1），低于阈值（0.7）的 segment 会进入人工审核。

文本内容：
{_escape_for_json_prompt(chunk_content)}
"""


def call_classify_llm_with_retry_tracking(
    chunk_content: str,
    structure_types: list[dict],
    semantic_types: list[dict],
) -> tuple[ClassifyOutput, list[dict]]:
    """
    调用 MiniMax 的 classify LLM，跟踪每次 attempt 的结果。

    返回：(ClassifyOutput, attempt_logs)
    attempt_logs 包含每次 attempt 的详细信息
    """
    from config import settings

    client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        base_url=settings.ANTHROPIC_BASE_URL,
    )

    prompt = build_classify_prompt(chunk_content, structure_types, semantic_types)
    schema_str = json.dumps(ClassifyOutput.model_json_schema(), ensure_ascii=False, indent=2)
    system_message = (
        "你是结构化数据提取助手。严格按以下 JSON Schema 输出，"
        "只返回 JSON 对象，不包含任何解释或 Markdown 代码块。\n\n"
        f"Schema:\n{schema_str}"
    )

    attempt_logs: list[dict] = []
    max_retries = 2  # PARSER_STRUCTURED_MAX_RETRIES 默认值

    for attempt in range(max_retries + 1):
        text_chunks: list[str] = []
        thinking_chunks: list[str] = []
        error_reason = None

        create_kwargs = {
            "model": settings.DEFAULT_MODEL,
            "max_tokens": 15000,
            "temperature": 1.0,
            "system": system_message,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "extra_body": {"enable_thinking": False, "reasoning_split": True},
        }

        try:
            with client.messages.create(**create_kwargs) as stream:
                for event in stream:
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "text"):
                            text_chunks.append(delta.text)
                        elif hasattr(delta, "thinking"):
                            thinking_chunks.append(delta.thinking)
                    elif event.type == "message_stop":
                        break

            text_response = "".join(text_chunks).strip()

            # 尝试解析 JSON
            if text_response:
                parsed = json.loads(text_response)
                result = ClassifyOutput.model_validate(parsed)
                attempt_logs.append({
                    "attempt": attempt,
                    "success": True,
                    "text_response": text_response[:500],
                    "thinking_count": len(thinking_chunks),
                })
                return result, attempt_logs
            else:
                error_reason = "空响应"
                raise json.JSONDecodeError("空响应", text_response, 0)

        except Exception as e:
            error_reason = str(e)[:100]
            attempt_logs.append({
                "attempt": attempt,
                "success": False,
                "error": error_reason,
                "text_response": text_response[:500] if text_response else "",
                "thinking_count": len(thinking_chunks),
            })
            continue

    # 所有重试都失败
    return ClassifyOutput(segments=[]), attempt_logs


def test_real_chunks_classification():
    """
    使用真实 markdown 文件，提取 chunks 并测试 classify 行为。
    """
    # 加载规则
    structure_types, semantic_types = load_rules(RULES_DIR)
    print(f"\n加载了 {len(structure_types)} 个结构类型, {len(semantic_types)} 个语义类型")

    # 选择一个有代表性的测试文件
    test_files = [
        TEST_ASSETS_DIR / "GB 1886.3-2021 食品安全国家标准 食品添加剂 磷酸氢钙.md",
        TEST_ASSETS_DIR / "GB 5009.211-2022 食品安全国家标准 食品中叶酸的测定.md",
    ]

    for test_file in test_files:
        if not test_file.exists():
            print(f"文件不存在: {test_file}")
            continue

        print(f"\n{'='*60}")
        print(f"测试文件: {test_file.name}")
        print(f"{'='*60}")

        with open(test_file, encoding="utf-8") as f:
            content = f.read()

        # 简单按章节切分 chunks（模拟 parse_node 的行为）
        # 实际上 parse_node 会按 ## 标题切分
        import re
        sections = re.split(r"(?=^#{1,2}\s)", content, flags=re.MULTILINE)

        # 取前 10 个有内容的 section 进行测试
        test_sections = [s.strip() for s in sections if s.strip() and len(s.strip()) > 50][:10]

        print(f"文档总章节数: {len(sections)}, 测试章节数: {len(test_sections)}")

        total_llm_calls = 0
        retry_count = 0
        failed_sections = []

        for i, section in enumerate(test_sections):
            section_preview = section[:100].replace("\n", " ")
            print(f"\n--- Chunk {i+1}/{len(test_sections)} ---")
            print(f"内容预览: {section_preview}...")
            print(f"内容长度: {len(section)} 字符")

            start = time.time()
            result, attempt_logs = call_classify_llm_with_retry_tracking(
                section, structure_types, semantic_types
            )
            elapsed = time.time() - start

            total_llm_calls += len(attempt_logs)
            chunk_retry_count = sum(1 for log in attempt_logs if not log["success"])
            retry_count += chunk_retry_count

            print(f"Attempt 次数: {len(attempt_logs)}, 重试次数: {chunk_retry_count}, 耗时: {elapsed:.1f}s")

            for log in attempt_logs:
                if log["success"]:
                    print(f"  ✓ Attempt {log['attempt']}: 成功 (thinking_count={log['thinking_count']})")
                else:
                    print(f"  ✗ Attempt {log['attempt']}: 失败 - {log.get('error', 'unknown')}")
                    print(f"    text_response: {log.get('text_response', '')[:200]!r}")

            if not result.segments:
                failed_sections.append((i+1, attempt_logs[-1].get('error', 'unknown') if attempt_logs else 'no logs'))

            # 打印分类结果
            if result.segments:
                print(f"  分类结果: {len(result.segments)} 个 segments")
                for seg in result.segments[:3]:
                    print(f"    - [{seg.structure_type}/{seg.semantic_type}] {seg.content[:50]}... (conf={seg.confidence})")

        print(f"\n{'='*60}")
        print(f"汇总: 文件 {test_file.name}")
        print(f"  总 LLM 调用次数: {total_llm_calls}")
        print(f"  总 重试次数: {retry_count}")
        print(f"  失败 sections: {len(failed_sections)}")
        if failed_sections:
            print(f"  失败详情: {failed_sections}")


def test_single_chunk_with_retry_detail():
    """
    对单个 chunk 进行详细的重试测试，观察 ThinkingDelta 的影响。
    """
    from config import settings

    structure_types, semantic_types = load_rules(RULES_DIR)

    # 使用一个典型的 GB 标准内容
    test_content = """
## A.3 硫酸酯的测定

### A.3.1 试剂和材料

A.3.1.1 硫酸溶液：c(H₂SO₄) = 0.5 mol/L

A.3.1.2 氯化钡溶液：100 g/L

### A.3.2 仪器和设备

A.3.2.1 分光光度计

### A.3.3 分析步骤

称取试样约 2g（精确至 0.001g），置于 100mL 锥形瓶中。

### A.3.4 结果计算

硫酸酯含量 w₁，以质量分数计，按式(A.1)计算：

$$w_1 = \frac{m_1 - m_0}{m} \times 100\\%$$

式中：
m₁——坩埚加残渣质量，单位为克(g)
m₀——坩埚质量，单位为克(g)
m——试样质量，单位为克(g)
    """

    print(f"\n{'='*60}")
    print("详细重试测试：观察 ThinkingDelta 对解析的影响")
    print(f"{'='*60}")

    client = anthropic.Anthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        base_url=settings.ANTHROPIC_BASE_URL,
    )

    prompt = build_classify_prompt(test_content, structure_types, semantic_types)
    schema_str = json.dumps(ClassifyOutput.model_json_schema(), ensure_ascii=False, indent=2)
    system_message = (
        "你是结构化数据提取助手。严格按以下 JSON Schema 输出，"
        "只返回 JSON 对象，不包含任何解释或 Markdown 代码块。\n\n"
        f"Schema:\n{schema_str}"
    )

    # 测试 reasoning_split = True 的情况（模拟 invoke_structured 的重试逻辑）
    print("\n--- reasoning_split=True ---")
    max_retries = 2  # PARSER_STRUCTURED_MAX_RETRIES 默认值
    all_attempts = []

    for attempt in range(max_retries + 1):
        text_chunks = []
        thinking_chunks = []
        error = None

        try:
            create_kwargs = {
                "model": settings.DEFAULT_MODEL,
                "max_tokens": 15000,
                "temperature": 1.0,
                "system": system_message,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "extra_body": {"enable_thinking": False, "reasoning_split": True},
            }

            with client.messages.create(**create_kwargs) as stream:
                for event in stream:
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "text"):
                            text_chunks.append(delta.text)
                        elif hasattr(delta, "thinking"):
                            thinking_chunks.append(delta.thinking)
                    elif event.type == "message_stop":
                        break

            text_response = "".join(text_chunks).strip()
            all_attempts.append({
                "attempt": attempt,
                "success": True,
                "text_len": len(text_response),
                "thinking_count": len(thinking_chunks),
            })

            # 尝试解析
            if text_response:
                parsed = json.loads(text_response)
                result = ClassifyOutput.model_validate(parsed)
                print(f"Attempt {attempt}: ✓ JSON 解析成功，segments: {len(result.segments)}, text_len={len(text_response)}, thinking_count={len(thinking_chunks)}")
                break
            else:
                print(f"Attempt {attempt}: ✗ 空响应")
                error = "空响应"

        except Exception as e:
            error = str(e)[:100]
            all_attempts.append({
                "attempt": attempt,
                "success": False,
                "error": error,
            })
            print(f"Attempt {attempt}: ✗ 错误 - {error}")

    print(f"总计: {len(all_attempts)} attempts, 重试 {len([a for a in all_attempts if not a.get('success')])} 次")

    # 测试 reasoning_split = False 的情况（模拟 invoke_structured 的重试逻辑）
    print("\n--- reasoning_split=False ---")
    all_attempts = []

    for attempt in range(max_retries + 1):
        text_chunks = []
        thinking_chunks = []
        error = None

        try:
            create_kwargs["extra_body"] = {"enable_thinking": False, "reasoning_split": False}

            with client.messages.create(**create_kwargs) as stream:
                for event in stream:
                    if event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "text"):
                            text_chunks.append(delta.text)
                        elif hasattr(delta, "thinking"):
                            thinking_chunks.append(delta.thinking)
                    elif event.type == "message_stop":
                        break

            text_response = "".join(text_chunks).strip()
            all_attempts.append({
                "attempt": attempt,
                "success": True,
                "text_len": len(text_response),
                "thinking_count": len(thinking_chunks),
            })

            # 尝试解析
            if text_response:
                parsed = json.loads(text_response)
                result = ClassifyOutput.model_validate(parsed)
                print(f"Attempt {attempt}: ✓ JSON 解析成功，segments: {len(result.segments)}, text_len={len(text_response)}, thinking_count={len(thinking_chunks)}")
                break
            else:
                print(f"Attempt {attempt}: ✗ 空响应")
                error = "空响应"

        except Exception as e:
            error = str(e)[:100]
            all_attempts.append({
                "attempt": attempt,
                "success": False,
                "error": error,
            })
            print(f"Attempt {attempt}: ✗ 错误 - {error}")

    print(f"总计: {len(all_attempts)} attempts, 重试 {len([a for a in all_attempts if not a.get('success')])} 次")


if __name__ == "__main__":
    test_single_chunk_with_retry_detail()
    print("\n\n")
    test_real_chunks_classification()
