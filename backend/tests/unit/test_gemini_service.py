"""Unit tests for GeminiService (T010).

Tests run with mocked Gemini SDK — no real API calls.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.invoice import ConfidenceLevel, EngineType, RecognitionResult
from app.services.gemini_service import (
    GeminiQuotaError,
    GeminiUnavailableError,
    GeminiService,
)

SAMPLE_INVOICE_JSON = """{
    "store_name": "全聯福利中心",
    "date": "2026-02-26",
    "items": [{"name": "統一科學麵", "unit_price": 15, "quantity": 3, "subtotal": 45}],
    "total": 45,
    "tax": null,
    "category": "食"
}"""

SAMPLE_IMAGE = b"fake-image-bytes"
SAMPLE_MIME = "image/jpeg"


@pytest.fixture
def service():
    return GeminiService(api_key="test-key")


class TestGeminiServiceSuccess:
    def test_recognize_returns_recognition_result(self, service):
        """成功辨識時回傳 RecognitionResult，包含憲章指定欄位。"""
        mock_response = MagicMock()
        mock_response.text = SAMPLE_INVOICE_JSON

        with patch.object(service, "_model") as mock_model:
            mock_model.generate_content.return_value = mock_response
            result = service.recognize(SAMPLE_IMAGE, SAMPLE_MIME)

        assert isinstance(result, RecognitionResult)
        assert result.store_name == "全聯福利中心"
        assert result.date == "2026-02-26"
        assert result.total == 45
        assert result.category == "食"
        assert result.engine_used == EngineType.GEMINI_PRIMARY

    def test_recognize_category_null_when_missing(self, service):
        """無法判斷類別時 category 為 null（澄清 Q3）。"""
        json_no_category = SAMPLE_INVOICE_JSON.replace('"食"', "null")
        mock_response = MagicMock()
        mock_response.text = json_no_category

        with patch.object(service, "_model") as mock_model:
            mock_model.generate_content.return_value = mock_response
            result = service.recognize(SAMPLE_IMAGE, SAMPLE_MIME)

        assert result.category is None

    def test_recognize_marks_partial_failure_fields(self, service):
        """部分欄位缺失時 partial_failure_fields 記錄失敗欄位。"""
        json_no_store = SAMPLE_INVOICE_JSON.replace('"全聯福利中心"', '""')
        mock_response = MagicMock()
        mock_response.text = json_no_store

        with patch.object(service, "_model") as mock_model:
            mock_model.generate_content.return_value = mock_response
            result = service.recognize(SAMPLE_IMAGE, SAMPLE_MIME)

        assert "store_name" in result.partial_failure_fields


class TestGeminiServiceErrors:
    def test_429_raises_quota_error(self, service):
        """Gemini 429 應拋出 GeminiQuotaError 以觸發降級。"""
        import google.api_core.exceptions as gexc

        with patch.object(service, "_model") as mock_model:
            mock_model.generate_content.side_effect = gexc.ResourceExhausted("quota")
            with pytest.raises(GeminiQuotaError):
                service.recognize(SAMPLE_IMAGE, SAMPLE_MIME)

    def test_503_raises_unavailable_error(self, service):
        """Gemini 503 應拋出 GeminiUnavailableError 以觸發降級。"""
        import google.api_core.exceptions as gexc

        with patch.object(service, "_model") as mock_model:
            mock_model.generate_content.side_effect = gexc.ServiceUnavailable("down")
            with pytest.raises(GeminiUnavailableError):
                service.recognize(SAMPLE_IMAGE, SAMPLE_MIME)
