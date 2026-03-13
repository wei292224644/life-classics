"""文档类型推断（规则 + Agent 兜底）的单元测试"""

import importlib.util
from pathlib import Path

# 直接加载 doc_type 模块，避免触发 app.core.kb 的 document_chunk/llm 等依赖
_spec = importlib.util.spec_from_file_location(
    "doc_type",
    Path(__file__).resolve().parents[4] / "app" / "core" / "kb" / "strategy" / "doc_type.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
infer_doc_type = _mod.infer_doc_type
infer_doc_type_auto = _mod.infer_doc_type_auto


def test_infer_doc_type_single_additive():
    assert infer_doc_type(
        "GB 8821-2011 食品添加剂 β-胡萝卜素.md",
        "1 范围",
        [["1 范围"], ["附录 A"]],
    ) == "single_additive"


def test_infer_doc_type_detection_method():
    assert infer_doc_type(
        "GB 5009.33 亚硝酸盐的测定.md",
        "1 范围",
        [["第一法 液相色谱法"]],
    ) == "detection_method"


def test_infer_doc_type_microbiological():
    assert infer_doc_type(
        "MinerU_GB_4789.4_沙门氏菌检验.md",
        None,
        [["检验程序"]],
    ) == "microbiological"


def test_infer_doc_type_other():
    assert infer_doc_type(
        "硬脂酸钾.md",
        "概述",
        [["概述"]],
    ) == "other"


def test_infer_doc_type_auto_fallback_to_rule_when_chat_fails():
    """Agent 失败时应回退到规则结果。"""
    def failing_chat(_):
        raise RuntimeError("mock failure")
    result = infer_doc_type_auto(
        "硬脂酸钾.md", "概述", [["概述"]],
        chat_fn=failing_chat,
        inference_mode="agent_then_rule",
    )
    assert result == "other"


def test_infer_doc_type_auto_uses_agent_when_chat_returns_type():
    """注入的 chat_fn 返回合法类型时，应优先采用。"""
    def agent_return_single_additive(_):
        return "single_additive"
    result = infer_doc_type_auto(
        "某奇怪文件名.x.md", "某标题", [["某节"]],
        chat_fn=agent_return_single_additive,
        inference_mode="agent_then_rule",
    )
    assert result == "single_additive"
