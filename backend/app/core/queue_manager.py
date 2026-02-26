from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.models.invoice import EngineType, QuotaStatus, RecognitionTask, TaskStatus


# ── Global state ──────────────────────────────────────────────────────────────

upload_queue: asyncio.Queue[RecognitionTask] = asyncio.Queue(
    maxsize=settings.queue_max_size
)

# task_id -> RecognitionTask (in-memory, cleared on restart)
ocr_tasks: dict[str, RecognitionTask] = {}

# MD5 去重快取 (in-memory only, 憲章原則四 + 澄清 Q1)
# md5_hex -> task_id
md5_cache: dict[str, str] = {}

# OCR concurrency: process one at a time to protect Ollama sequential bottleneck
ocr_semaphore = asyncio.Semaphore(1)

# Quota tracking (single instance)
_quota = QuotaStatus(
    daily_limit=settings.daily_limit,
    rpm_limit=settings.rate_limit_rpm,
)
_quota_lock = asyncio.Lock()


# ── Queue helpers ──────────────────────────────────────────────────────────────

def compute_md5(image_bytes: bytes) -> str:
    return hashlib.md5(image_bytes).hexdigest()


def find_duplicate(md5_hex: str) -> Optional[str]:
    """Return existing task_id if image already processed, else None."""
    return md5_cache.get(md5_hex)


def register_md5(md5_hex: str, task_id: str) -> None:
    md5_cache[md5_hex] = task_id


def enqueue(task: RecognitionTask) -> None:
    """Non-blocking enqueue. Raises asyncio.QueueFull if at capacity."""
    upload_queue.put_nowait(task)
    ocr_tasks[task.task_id] = task


def get_task(task_id: str) -> Optional[RecognitionTask]:
    return ocr_tasks.get(task_id)


def update_task(task: RecognitionTask) -> None:
    ocr_tasks[task.task_id] = task


# ── Quota helpers ──────────────────────────────────────────────────────────────

def get_quota() -> QuotaStatus:
    _quota.queue_depth = upload_queue.qsize()
    return _quota


async def record_gemini_call() -> None:
    async with _quota_lock:
        _quota.used_today += 1
        _quota.rpm_used += 1
        if _quota.used_today >= _quota.daily_limit:
            _quota.active_engine = EngineType.PADDLEOCR_FALLBACK


async def get_active_engine() -> EngineType:
    async with _quota_lock:
        return _quota.active_engine


def force_fallback_engine() -> None:
    _quota.active_engine = EngineType.PADDLEOCR_FALLBACK


def reset_rpm_counter() -> None:
    """Called periodically to reset per-minute counter."""
    _quota.rpm_used = 0
