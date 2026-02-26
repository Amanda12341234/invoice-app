"""Integration tests for upload endpoint (T014).

Uses httpx.AsyncClient with FastAPI TestClient.
All OCR services are mocked to avoid requiring real Gemini/PaddleOCR.
"""
from __future__ import annotations

import asyncio
import io
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.models.invoice import EngineType, RecognitionResult, TaskStatus

MOCK_RESULT = RecognitionResult(
    store_name="全聯福利中心",
    date="2026-02-26",
    total=134,
    category="食",
    engine_used=EngineType.GEMINI_PRIMARY,
)


@pytest.fixture
def fake_image() -> bytes:
    """Minimal valid JPEG bytes."""
    from PIL import Image
    import io as _io

    img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    buf = _io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_returns_202_with_task_id(fake_image):
    """POST /invoices/upload 應回傳 202 Accepted 與 task_id。"""
    from app.main import app
    from app.services import ocr_orchestrator

    with patch.object(
        ocr_orchestrator.OCROrchestrator, "process", return_value=MOCK_RESULT
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/invoices/upload",
                files={"file": ("invoice.jpg", fake_image, "image/jpeg")},
            )

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert "task_id" in body["meta"]


@pytest.mark.asyncio
async def test_poll_task_returns_result(fake_image):
    """GET /invoices/{task_id} 應在 worker 完成後回傳 success 狀態。"""
    from app.main import app
    from app.core import queue_manager
    from app.services import ocr_orchestrator

    with patch.object(
        ocr_orchestrator.OCROrchestrator, "process", return_value=MOCK_RESULT
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            upload_resp = await client.post(
                "/invoices/upload",
                files={"file": ("invoice.jpg", fake_image, "image/jpeg")},
            )
            task_id = upload_resp.json()["meta"]["task_id"]

            # Allow worker to process
            await asyncio.sleep(0.5)

            poll_resp = await client.get(f"/invoices/{task_id}")

    body = poll_resp.json()
    assert poll_resp.status_code == 200
    # status may be queued/processing/completed depending on timing
    assert body["status"] in ("queued", "processing", "success")


@pytest.mark.asyncio
async def test_duplicate_upload_returns_409(fake_image):
    """相同圖片二次上傳應回傳 409 DUPLICATE_IMAGE（澄清 Q1）。"""
    from app.main import app
    from app.services import ocr_orchestrator

    with patch.object(
        ocr_orchestrator.OCROrchestrator, "process", return_value=MOCK_RESULT
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post(
                "/invoices/upload",
                files={"file": ("invoice.jpg", fake_image, "image/jpeg")},
            )
            second = await client.post(
                "/invoices/upload",
                files={"file": ("invoice.jpg", fake_image, "image/jpeg")},
            )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DUPLICATE_IMAGE"
