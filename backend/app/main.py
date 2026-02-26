from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.rate_limiter import limiter
from app.models.invoice import ApiResponse, ErrorDetail

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting Invoice OCR backend...")

    # Pre-load PaddleOCR model to avoid first-request latency
    try:
        from app.services.paddleocr_service import PaddleOCRService
        PaddleOCRService.warmup()
        logger.info("PaddleOCR model pre-loaded.")
    except Exception as exc:
        logger.warning("PaddleOCR warmup skipped: %s", exc)

    # Start background OCR worker
    from app.core import queue_manager
    from app.services.ocr_orchestrator import OCROrchestrator

    async def worker():
        orchestrator = OCROrchestrator()
        while True:
            try:
                task = await asyncio.wait_for(queue_manager.upload_queue.get(), timeout=30)
            except asyncio.TimeoutError:
                continue
            async with queue_manager.ocr_semaphore:
                from app.models.invoice import TaskStatus
                from datetime import datetime
                task.status = TaskStatus.PROCESSING
                task.started_at = datetime.utcnow()
                queue_manager.update_task(task)
                try:
                    result = await orchestrator.process(
                        task._image_bytes, task._mime_type
                    )
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    task.engine_used = result.engine_used
                    # Clear image bytes immediately (憲章原則四)
                    task._image_bytes = None
                except Exception as exc:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(exc)
                    task.retryable = True
                    task._image_bytes = None
                finally:
                    task.completed_at = datetime.utcnow()
                    queue_manager.update_task(task)
                    queue_manager.upload_queue.task_done()

    asyncio.create_task(worker())
    logger.info("OCR worker started.")

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down Invoice OCR backend.")


app = FastAPI(
    title="Invoice OCR API",
    description="Phase 2 backend: Gemini + PaddleOCR invoice recognition",
    version="0.2.0",
    lifespan=lifespan,
)

app.state.limiter = limiter


# ── Global exception handlers ─────────────────────────────────────────────────

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content=ApiResponse(
            status="error",
            error=ErrorDetail(
                code="RATE_LIMITED",
                message="請求頻率過高，請稍後再試",
                retryable=True,
            ),
            meta={"retry_after_seconds": 60},
        ).model_dump(),
    )


# ── Routers ───────────────────────────────────────────────────────────────────

from app.routers import invoices  # noqa: E402
app.include_router(invoices.router)
