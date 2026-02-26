from __future__ import annotations

import json
import logging
import re

import requests

from app.core.config import settings
from app.models.invoice import (
    ConfidenceLevel,
    EngineType,
    LineItem,
    RecognitionResult,
)

logger = logging.getLogger(__name__)

_PARSE_PROMPT = """\
你是台灣統一發票資料解析器。從以下 OCR 辨識文字中提取發票資訊。
只回傳 JSON 物件，不加其他說明文字。

JSON 格式（無法辨識的欄位填 null）：
{{
    "store_name": "店名（字串）",
    "date": "消費日期（YYYY-MM-DD）",
    "items": [{{"name": "品項名稱", "unit_price": 0, "quantity": 1, "subtotal": 0}}],
    "total": 0,
    "tax": null,
    "category": "食 | 衣 | 住 | 行（無法判斷填 null）"
}}

發票文字：
{raw_text}
"""


class OllamaParseError(Exception):
    """Raised when Ollama fails to parse invoice text into JSON."""


class OllamaService:
    def __init__(
        self,
        url: str | None = None,
        model: str | None = None,
    ):
        self._url = url or settings.ollama_url
        self._model = model or settings.ollama_model

    def parse_to_invoice(self, raw_text: str) -> RecognitionResult:
        """Send OCR text to local Ollama LLM and parse response as RecognitionResult."""
        prompt = _PARSE_PROMPT.format(raw_text=raw_text)
        try:
            resp = requests.post(
                self._url,
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=60,
            )
        except requests.exceptions.RequestException as exc:
            raise OllamaParseError(f"Ollama connection failed: {exc}") from exc

        if resp.status_code != 200:
            raise OllamaParseError(f"Ollama returned HTTP {resp.status_code}")

        response_text = resp.json().get("response", "")
        return self._parse_json(response_text)

    def _parse_json(self, text: str) -> RecognitionResult:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise OllamaParseError("No JSON object found in Ollama response")

        try:
            data = json.loads(match.group())
        except json.JSONDecodeError as exc:
            raise OllamaParseError(f"Invalid JSON from Ollama: {exc}") from exc

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
            category=data.get("category"),
            confidence=ConfidenceLevel.LOW,
            engine_used=EngineType.PADDLEOCR_FALLBACK,
        )
