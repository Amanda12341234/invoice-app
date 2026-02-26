"""Unit tests for PaddleOCRService (T011).

PaddleOCR is mocked — no model download required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.paddleocr_service import PaddleOCRService

SAMPLE_IMAGE = b"fake-image-bytes"

# Simulated PaddleOCR result format: list of lines, each line = list of (bbox, (text, conf))
MOCK_OCR_RESULT = [
    [([[0, 0], [100, 0], [100, 20], [0, 20]], ("全聯福利中心", 0.98))],
    [([[0, 25], [100, 25], [100, 45], [0, 45]], ("2026/02/26", 0.95))],
    [([[0, 50], [100, 50], [100, 70], [0, 70]], ("統一科學麵 $45", 0.87))],
]

MOCK_LOW_CONF_RESULT = [
    [([[0, 0], [100, 0], [100, 20], [0, 20]], ("unclear text", 0.3))],
]


class TestPaddleOCRServiceExtract:
    def test_extract_text_returns_string(self):
        """成功提取時回傳非空字串。"""
        with patch("app.services.paddleocr_service.PaddleOCR") as mock_cls:
            mock_ocr = MagicMock()
            mock_ocr.ocr.return_value = MOCK_OCR_RESULT
            mock_cls.return_value = mock_ocr

            service = PaddleOCRService()
            result = service.extract_text(SAMPLE_IMAGE)

        assert isinstance(result, str)
        assert "全聯福利中心" in result
        assert "2026/02/26" in result

    def test_empty_result_returns_empty_string(self):
        """無文字偵測時回傳空字串。"""
        with patch("app.services.paddleocr_service.PaddleOCR") as mock_cls:
            mock_ocr = MagicMock()
            mock_ocr.ocr.return_value = [[]]
            mock_cls.return_value = mock_ocr

            service = PaddleOCRService()
            result = service.extract_text(SAMPLE_IMAGE)

        assert result == ""

    def test_low_confidence_text_filtered(self):
        """信心度低於閾值的文字不包含在輸出中。"""
        with patch("app.services.paddleocr_service.PaddleOCR") as mock_cls:
            mock_ocr = MagicMock()
            mock_ocr.ocr.return_value = MOCK_LOW_CONF_RESULT
            mock_cls.return_value = mock_ocr

            service = PaddleOCRService(min_confidence=0.5)
            result = service.extract_text(SAMPLE_IMAGE)

        assert result == ""
