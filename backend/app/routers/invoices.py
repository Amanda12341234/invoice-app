from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.core import queue_manager
from app.core.config import settings
from app.core.rate_limiter import limiter
from app.models.invoice import (
    ApiResponse,
    ErrorDetail,
    RecognitionTask,
    TaskStatus,
)

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/heic", "image/heif"}
MIN_WIDTH = 640
MIN_HEIGHT = 480

router = APIRouter(prefix="/invoices", tags=["invoices"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _error_response(
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
    meta: dict | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ApiResponse(
            status="error",
            error=ErrorDetail(code=code, message=message, retryable=retryable),
            meta=meta,
        ).model_dump(),
    )


def _validate_image(content: bytes, mime_type: str) -> JSONResponse | None:
    """Return error JSONResponse if invalid, else None."""
    # Format check
    if mime_type not in ALLOWED_MIME_TYPES:
        return _error_response(400, "INVALID_FORMAT", "不支援的圖片格式，請使用 JPEG 或 PNG")

    # Size check
    if len(content) > settings.max_file_size_bytes:
        return _error_response(413, "IMAGE_TOO_LARGE", f"圖片超過 {settings.max_file_size_mb} MB 上限")

    # Dimension check
    try:
        from io import BytesIO
        from PIL import Image
        img = Image.open(BytesIO(content))
        if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
            return _error_response(
                400, "IMAGE_TOO_SMALL",
                f"圖片解析度不足，請確保寬度 ≥ {MIN_WIDTH}px、高度 ≥ {MIN_HEIGHT}px"
            )
    except Exception:
        return _error_response(400, "INVALID_FORMAT", "無法解析圖片，請重新拍攝")

    return None


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/upload")
@limiter.limit(settings.rate_limit_string)
async def upload_invoice(request: Request, file: UploadFile):
    """Accept invoice image, validate, and enqueue for OCR processing."""
    content = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    # Validate image
    err = _validate_image(content, mime_type)
    if err:
        return err

    # Deduplication check (in-memory cache, 澄清 Q1)
    md5_hex = queue_manager.compute_md5(content)
    existing_task_id = queue_manager.find_duplicate(md5_hex)
    if existing_task_id:
        return JSONResponse(
            status_code=409,
            content=ApiResponse(
                status="error",
                error=ErrorDetail(
                    code="DUPLICATE_IMAGE",
                    message="此圖片已上傳，請查詢現有辨識結果",
                    retryable=False,
                ),
                meta={"existing_task_id": existing_task_id},
            ).model_dump(),
        )

    # Create task
    task_id = str(uuid.uuid4())
    task = RecognitionTask(task_id=task_id)
    task._image_bytes = content
    task._mime_type = mime_type

    # Enqueue
    try:
        queue_manager.enqueue(task)
        queue_manager.register_md5(md5_hex, task_id)
    except asyncio.QueueFull:
        return _error_response(
            503, "QUEUE_FULL", "辨識佇列已滿，請稍後再試",
            retryable=True,
            meta={"retry_after_seconds": 30},
        )

    return JSONResponse(
        status_code=202,
        content=ApiResponse(
            status="queued",
            meta={
                "task_id": task_id,
                "queue_depth": queue_manager.upload_queue.qsize(),
                "estimated_wait_seconds": queue_manager.upload_queue.qsize() * 10,
            },
        ).model_dump(),
    )


@router.get("/{task_id}")
async def get_invoice_result(task_id: str):
    """Poll recognition task status and result."""
    task = queue_manager.get_task(task_id)
    if task is None:
        return _error_response(404, "TASK_NOT_FOUND", "找不到此辨識任務，任務可能已過期")

    if task.status == TaskStatus.QUEUED:
        return ApiResponse(
            status="queued",
            meta={"task_id": task_id, "estimated_wait_seconds": 10},
        ).model_dump()

    if task.status == TaskStatus.PROCESSING:
        return ApiResponse(
            status="processing",
            meta={"task_id": task_id, "started_at": task.started_at.isoformat() if task.started_at else None},
        ).model_dump()

    if task.status == TaskStatus.COMPLETED and task.result:
        result_data = task.result.model_dump()
        has_partial = bool(task.result.partial_failure_fields)
        return JSONResponse(
            status_code=206 if has_partial else 200,
            content=ApiResponse(
                status="partial" if has_partial else "success",
                data=result_data,
                meta={
                    "task_id": task_id,
                    "engine_used": task.engine_used.value if task.engine_used else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                },
            ).model_dump(),
        )

    # FAILED
    return JSONResponse(
        status_code=200,
        content=ApiResponse(
            status="error",
            error=ErrorDetail(
                code=task.error_code or "ALL_ENGINES_FAILED",
                message=task.error_message or "辨識失敗，請重試",
                retryable=task.retryable,
            ),
            meta={"task_id": task_id},
        ).model_dump(),
    )


@router.get("/health/status")
@limiter.exempt
async def health_check():
    """Return service health, quota usage, and queue depth."""
    from datetime import datetime, timezone
    quota = queue_manager.get_quota()
    return ApiResponse(
        status="healthy",
        data=quota.model_dump(),
        meta={
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ).model_dump()
