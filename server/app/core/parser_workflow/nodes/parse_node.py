from __future__ import annotations

import uuid

from app.core.parser_workflow.models import WorkflowState


def parse_node(state: WorkflowState) -> dict:
    """验证并规范化 doc_metadata，从 MD 首行标题补全缺失的 title。"""
    meta = dict(state["doc_metadata"])
    errors = list(state.get("errors", []))

    # 若未提供 title，尝试从第一个 # 标题提取
    if not meta.get("title"):
        for line in state["md_content"].splitlines():
            if line.startswith("# "):
                meta["title"] = line[2:].strip()
                break

    # 若未提供 doc_id，自动生成 UUID
    if not meta.get("doc_id"):
        meta["doc_id"] = str(uuid.uuid4())

    # standard_no 缺失时记录警告（非错误，允许无编号文档）
    if not meta.get("standard_no"):
        errors.append("WARNING: doc_metadata missing 'standard_no'")

    # 透传 md_content，方便后续节点继续使用
    return {"doc_metadata": meta, "errors": errors, "md_content": state["md_content"]}

