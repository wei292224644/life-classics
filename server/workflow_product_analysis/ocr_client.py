"""组件 1：OCR HTTP 客户端，向 PaddleOCR-VL-1.5 服务发送图片。"""
from __future__ import annotations

import httpx

from config import Settings


class OcrServiceError(Exception):
    """OCR 服务调用失败，管道捕获后写入 error='ocr_failed'。"""


async def run_ocr(image_bytes: bytes, settings: Settings) -> str:
    """
    向 settings.OCR_SERVICE_URL/ocr 发送 multipart POST，返回 OCR 文字。

    入参：
        image_bytes: 客户端已压缩的图片字节流
        settings: 含 OCR_SERVICE_URL、OCR_TIMEOUT_SECONDS

    出参：
        str: 原始 OCR 文字（包含配料表、品名等所有文字）

    异常：
        OcrServiceError: HTTP 错误、超时、网络异常时抛出
    """
    url = f"{settings.OCR_SERVICE_URL.rstrip('/')}/ocr"
    try:
        async with httpx.AsyncClient(timeout=settings.OCR_TIMEOUT_SECONDS) as client:
            response = await client.post(
                url,
                files={"image": ("image.jpg", image_bytes, "image/jpeg")},
            )
            response.raise_for_status()
            data = response.json()
            return data["text"]
    except httpx.TimeoutException as e:
        raise OcrServiceError(f"OCR service timeout: {e}") from e
    except httpx.HTTPStatusError as e:
        raise OcrServiceError(f"OCR service HTTP error {e.response.status_code}") from e
    except Exception as e:
        raise OcrServiceError(f"OCR service error: {e}") from e
