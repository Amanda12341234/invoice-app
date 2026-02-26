from __future__ import annotations

import logging
import tempfile
import os
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Lazy import to avoid loading PaddleOCR at module level during tests
_ocr_instance = None


def _get_ocr(min_confidence: float = 0.5):
    global _ocr_instance
    if _ocr_instance is None:
        from paddleocr import PaddleOCR
        _ocr_instance = PaddleOCR(
            use_angle_cls=True,
            lang="ch",          # Supports Traditional Chinese (台灣繁體)
            use_gpu=False,
            show_log=False,
        )
    return _ocr_instance


class PaddleOCRService:
    def __init__(self, min_confidence: float = 0.5):
        self._min_confidence = min_confidence

    @classmethod
    def warmup(cls) -> None:
        """Pre-load model at startup to avoid first-request latency."""
        logger.info("Pre-loading PaddleOCR model...")
        _get_ocr()
        logger.info("PaddleOCR model ready.")

    def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image bytes. Returns empty string if nothing detected."""
        from paddleocr import PaddleOCR

        ocr = _get_ocr(self._min_confidence)

        # Write to temp file (PaddleOCR requires file path or numpy array)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(image_bytes)
            tmp_path = tmp.name

        try:
            results = ocr.ocr(tmp_path, cls=True)
        finally:
            os.unlink(tmp_path)

        if not results:
            return ""

        lines: list[str] = []
        for line_group in results:
            if not line_group:
                continue
            for _bbox, (text, confidence) in line_group:
                if confidence >= self._min_confidence:
                    lines.append(text)

        return "\n".join(lines)
