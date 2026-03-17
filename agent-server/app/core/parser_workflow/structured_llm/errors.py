"""统一结构化输出异常。"""

from __future__ import annotations


class StructuredOutputError(RuntimeError):
    """
    结构化输出调用失败时的统一异常。

    包含 provider/model/node_name/response_model/retry_count/raw_error 等上下文，
    便于快速判断是 provider 兼容问题、schema 过严还是 prompt 质量问题。
    """

    def __init__(
        self,
        message: str,
        *,
        provider: str,
        model: str,
        node_name: str,
        response_model: str,
        retry_count: int,
        raw_error: str,
    ):
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.node_name = node_name
        self.response_model = response_model
        self.retry_count = retry_count
        self.raw_error = raw_error
