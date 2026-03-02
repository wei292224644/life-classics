"""
MinerU 本地服务适配器：将 PDF 转为 Markdown。
调用方需已部署 mineru-api（如 Docker），本模块仅做 HTTP 调用。
"""

import requests
from pathlib import Path
from typing import Optional

from app.core.config import settings


def pdf_to_markdown(
    pdf_path: str,
    service_url: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """
    调用 MinerU 本地服务，将 PDF 转为 Markdown 文本。

    Args:
        pdf_path: 本地 PDF 文件路径
        service_url: MinerU API 根地址，默认从 settings 读取
        timeout: 请求超时秒数，默认从 settings 读取

    Returns:
        解析得到的 Markdown 字符串；失败时抛出异常。
    """
    url = (service_url or settings.MINERU_SERVICE_URL).rstrip("/")
    t = timeout if timeout is not None else settings.MINERU_REQUEST_TIMEOUT
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with open(pdf_path, "rb") as f:
        files = {"file": (path.name, f, "application/pdf")}
        r = requests.post(
            f"{url}/convert",
            files=files,
            timeout=t,
        )
    r.raise_for_status()
    data = r.json()
    return data.get("markdown", data.get("content", ""))
