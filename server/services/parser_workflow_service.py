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

    async def transform_and_merge(
        self,
        state: dict,
        doc_metadata: dict,
    ) -> list[dict]:
        """对已构建的 WorkflowState 进行 transform + merge，用于 reparse."""
        transform_result = await transform_node(state)
        final_chunks = transform_result.get("final_chunks", [])
        merge_result = merge_node({"final_chunks": final_chunks, "doc_metadata": doc_metadata})
        return merge_result.get("final_chunks", [])

    async def reparse_chunk(
        self,
        raw_content: str,
        section_path_str: str,
        semantic_type: str,
        structure_type: str,
        cross_refs: list,
        failed_table_refs: list,
        rules_dir: str,
        doc_metadata: dict,
    ) -> list[dict]:
        """对单个 chunk 进行 reparse：构建 state → transform → merge."""
        store = RulesStore(rules_dir)
        transform_params = store.get_transform_params(semantic_type)
        typed_segment = {
            "content": raw_content,
            "structure_type": structure_type,
            "semantic_type": semantic_type,
            "transform_params": transform_params,
            "confidence": 1.0,
            "escalated": False,
            "cross_refs": cross_refs,
            "ref_context": "",
            "failed_table_refs": failed_table_refs,
        }
        raw_chunk = {
            "content": raw_content,
            "section_path": section_path_str.split("|") if section_path_str else [],
            "char_count": len(raw_content),
        }
        classified_chunk = {
            "raw_chunk": raw_chunk,
            "segments": [typed_segment],
            "has_unknown": False,
        }
        state = {
            "md_content": "",
            "doc_metadata": doc_metadata,
            "config": {},
            "rules_dir": rules_dir,
            "raw_chunks": [],
            "classified_chunks": [classified_chunk],
            "final_chunks": [],
            "errors": [],
        }
        return await self.transform_and_merge(state, doc_metadata)
