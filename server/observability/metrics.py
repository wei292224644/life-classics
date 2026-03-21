"""Prometheus 业务指标定义。所有指标在此集中注册，其他模块直接 import 使用。"""
from prometheus_client import Counter, Histogram

llm_calls_total = Counter(
    "llm_calls_total",
    "LLM 调用总次数",
    ["node", "model"],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "LLM token 用量",
    ["node", "model", "type"],
)

parser_chunks_processed_total = Counter(
    "parser_chunks_processed_total",
    "Parser Workflow 处理的 chunk 总数",
    ["node"],
)

parser_node_duration_seconds = Histogram(
    "parser_node_duration_seconds",
    "Parser 节点处理耗时（秒）",
    ["node"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

parser_workflow_duration_seconds = Histogram(
    "parser_workflow_duration_seconds",
    "Parser 完整流水线处理耗时（秒）",
    ["doc_type"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)
