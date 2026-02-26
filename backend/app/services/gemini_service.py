from __future__ import annotations

import json
import logging
from io import BytesIO

import google.api_core.exceptions as gexc
import google.generativeai as genai
from PIL import Image

from app.core.config import settings
from app.models.invoice import (
    ConfidenceLevel,
    EngineType,
    LineItem,
    RecognitionResult,
)

logger = logging.getLogger(__name__)

# JSON schema for structured output (對應憲章技術標準)
_INVOICE_SCHEMA = {
    "type": "object",
    "properties": {
        "store_name": {"type": "string"},
        "date": {"type": "string", "nullable": True},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "unit_price": {"type": "number"},
                    "quantity": {"type": "number"},
                    "subtotal": {"type": "number", "nullable": True},
                },
            },
        },
        "total": {"type": "number", "nullable": True},
        "tax": {"type": "number", "nullable": True},
        "category": {"type": "string", "nullable": True},
    },
}

_PROMPT = (
    "你是台灣統一發票解析專家。從圖片中擷取發票資訊，"
    "以 JSON 格式回傳以下欄位（無法辨識的欄位填 null）：\n"
    "store_name（店家名稱）、date（YYYY-MM-DD）、"
    "items（品項陣列，含 name/unit_price/quantity/subtotal）、"
    "total（總金額）、tax（稅額）、"
    "category（消費類別：食|衣|住|行，無法判斷填 null）。\n"
    "只回傳 JSON，不加其他文字。"
)


class GeminiQuotaError(Exception):
    """Raised when Gemini API quota is exhausted (429)."""


class GeminiUnavailableError(Exception):
    """Raised when Gemini service is unavailable (503)."""


class GeminiService:
    def __init__(self, api_key: str | None = None):
        key = api_key or settings.gemini_api_key
        genai.configure(api_key=key)
        self._model = genai.GenerativeModel("gemini-2.0-flash")

    def recognize(self, image_bytes: bytes, mime_type: str) -> RecognitionResult:
        """Send image to Gemini and return structured RecognitionResult."""
        try:
            img = Image.open(BytesIO(image_bytes))
            response = self._model.generate_content(
                [img, _PROMPT],
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                ),
            )
        except gexc.ResourceExhausted as exc:
            logger.warning("Gemini quota exhausted: %s", exc)
            raise GeminiQuotaError from exc
        except gexc.ServiceUnavailable as exc:
            logger.warning("Gemini unavailable: %s", exc)
            raise GeminiUnavailableError from exc

        return self._parse_response(response.text)

    def _parse_response(self, text: str) -> RecognitionResult:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                data = json.loads(match.group())
            else:
                return RecognitionResult(
                    partial_failure_fields=["store_name", "date", "items", "total"],
                    confidence=ConfidenceLevel.LOW,
                    engine_used=EngineType.GEMINI_PRIMARY,
                )

        partial_fields: list[str] = []
        if not data.get("store_name"):
            partial_fields.append("store_name")

        items = [
            LineItem(
                name=i.get("name", ""),
                unit_price=i.get("unit_price", 0),
                quantity=i.get("quantity", 1),
                subtotal=i.get("subtotal"),
            )
            for i in data.get("items", [])
        ]

        return RecognitionResult(
            store_name=data.get("store_name", ""),
            date=data.get("date"),
            items=items,
            total=data.get("total"),
            tax=data.get("tax"),
            category=data.get("category"),  # null if unclassifiable (澄清 Q3)
            confidence=ConfidenceLevel.HIGH if not partial_fields else ConfidenceLevel.MEDIUM,
            engine_used=EngineType.GEMINI_PRIMARY,
            partial_failure_fields=partial_fields,
        )
