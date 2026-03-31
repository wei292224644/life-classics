import pytest
import respx
import httpx

from workflow_product_analysis.ocr_client import run_ocr, OcrServiceError
from config import settings as real_settings


class MockSettings:
    OCR_SERVICE_URL = "http://ocr-service:8100"
    OCR_TIMEOUT_SECONDS = 10


@pytest.fixture
def mock_settings():
    return MockSettings()


@pytest.mark.asyncio
async def test_run_ocr_success(mock_settings):
    with respx.mock:
        respx.post("http://ocr-service:8100/ocr").mock(
            return_value=httpx.Response(200, json={"text": "配料：燕麦粉，麦芽糊精"})
        )
        result = await run_ocr(b"fake_image_bytes", mock_settings)
        assert result == "配料：燕麦粉，麦芽糊精"


@pytest.mark.asyncio
async def test_run_ocr_http_error_raises(mock_settings):
    with respx.mock:
        respx.post("http://ocr-service:8100/ocr").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(OcrServiceError):
            await run_ocr(b"fake_image_bytes", mock_settings)


@pytest.mark.asyncio
async def test_run_ocr_timeout_raises(mock_settings):
    with respx.mock:
        respx.post("http://ocr-service:8100/ocr").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        with pytest.raises(OcrServiceError):
            await run_ocr(b"fake_image_bytes", mock_settings)
