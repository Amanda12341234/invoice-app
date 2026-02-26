from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EngineType(str, Enum):
    GEMINI_PRIMARY = "GEMINI_PRIMARY"
    PADDLEOCR_FALLBACK = "PADDLEOCR_FALLBACK"


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class LineItem(BaseModel):
    name: str
    unit_price: float = 0.0
    quantity: float = 1.0
    subtotal: Optional[float] = None


class RecognitionResult(BaseModel):
    store_name: str = ""
    date: Optional[str] = None          # YYYY-MM-DD or null
    items: list[LineItem] = Field(default_factory=list)
    total: Optional[float] = None
    tax: Optional[float] = None
    category: Optional[str] = None      # 食|衣|住|行 or null (澄清 Q3)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    engine_used: EngineType = EngineType.GEMINI_PRIMARY
    partial_failure_fields: list[str] = Field(default_factory=list)
    recognized_at: datetime = Field(default_factory=datetime.utcnow)


class RecognitionTask(BaseModel):
    task_id: str
    status: TaskStatus = TaskStatus.QUEUED
    engine_used: Optional[EngineType] = None
    queued_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[RecognitionResult] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    retryable: bool = True
    # internal: image bytes cleared after processing (憲章原則四)
    _image_bytes: Optional[bytes] = None
    _mime_type: str = "image/jpeg"


class QuotaStatus(BaseModel):
    used_today: int = 0
    daily_limit: int = 1500
    rpm_used: int = 0
    rpm_limit: int = 15
    reset_at_utc: Optional[datetime] = None
    queue_depth: int = 0
    active_engine: EngineType = EngineType.GEMINI_PRIMARY


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool = False


class ApiResponse(BaseModel):
    status: str
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
    meta: Optional[dict[str, Any]] = None
