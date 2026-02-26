"""Unit tests for OllamaService (T012).

HTTP calls to Ollama are mocked.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.models.invoice import RecognitionResult
from app.services.ollama_service import OllamaService, OllamaParseError

RAW_TEXT = "全聯福利中心\n2026/02/26\n統一科學麵 x3 $45\n合計 $45"

VALID_OLLAMA_RESPONSE = {
    "response": '{"store_name": "全聯福利中心", "date": "2026-02-26", '
                '"items": [{"name": "統一科學麵", "unit_price": 15, "quantity": 3}], '
                '"total": 45, "tax": null, "category": "食"}'
}


class TestOllamaServiceParse:
    def test_parse_returns_recognition_result(self):
        """有效回應應解析為 RecognitionResult。"""
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200, json=lambda: VALID_OLLAMA_RESPONSE
            )
            service = OllamaService()
            result = service.parse_to_invoice(RAW_TEXT)

        assert isinstance(result, RecognitionResult)
        assert result.store_name == "全聯福利中心"
        assert result.total == 45

    def test_connection_failure_raises_parse_error(self):
        """Ollama 連線失敗應拋出 OllamaParseError。"""
        import requests

        with patch("requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError("refused")
            service = OllamaService()
            with pytest.raises(OllamaParseError):
                service.parse_to_invoice(RAW_TEXT)

    def test_invalid_json_in_response_raises_parse_error(self):
        """Ollama 回傳無法解析的 JSON 時應拋出 OllamaParseError。"""
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200, json=lambda: {"response": "這不是 JSON 格式"}
            )
            service = OllamaService()
            with pytest.raises(OllamaParseError):
                service.parse_to_invoice(RAW_TEXT)
