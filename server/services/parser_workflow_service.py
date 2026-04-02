"""Parser Workflow 编排服务 — L2 层，调用 workflow_parser_kb."""
from __future__ import annotations

from collections.abc import AsyncIterator

from workflow_parser_kb.graph import run_parser_workflow_stream
from workflow_parser_kb.models import ClassifiedChunk, TypedSegment
from workflow_parser_kb.nodes.merge_node import merge_node
from workflow_parser_kb.nodes.transform_node import transform_node
from workflow_parser_kb.rules import RulesStore


class ParserWorkflowService:
    """L2: Parser Workflow 编排 — 调用 workflow_parser_kb."""

    async def run_parse_workflow(
        self,
        md_content: str,
        doc_name: str,
        rules_dir: str,
    ) -> AsyncIterator[dict]:
        """运行 parser workflow 流式处理."""
        async for event in run_parser_workflow_stream(
            md_content=md_content,
            doc_name=doc_name,
            rules_dir=rules_dir,
        ):
            yield event

    async def transform_chunks(
        self,
        state: dict,
    ) -> dict:
        """对分段后的 chunk 进行 transform."""
        return await transform_node(state)

    async def merge_chunks(
        self,
        final_chunks: list[ClassifiedChunk],
        doc_metadata: dict,
    ) -> dict:
        """合并相邻同类 chunk."""
        return merge_node({"final_chunks": final_chunks, "doc_metadata": doc_metadata})
