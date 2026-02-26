"""Unit tests for QuotaStatus tracking in queue_manager (T028).

Tests quota increment, daily limit enforcement, and engine switching.
"""
from __future__ import annotations

import pytest

from app.core import queue_manager
from app.models.invoice import EngineType


@pytest.mark.asyncio
async def test_record_gemini_call_increments_used_today():
    """每次 Gemini 呼叫應遞增 used_today。"""
    initial = queue_manager._quota.used_today
    await queue_manager.record_gemini_call()
    assert queue_manager._quota.used_today == initial + 1
    # Restore for other tests
    queue_manager._quota.used_today = initial


@pytest.mark.asyncio
async def test_daily_limit_triggers_fallback_engine():
    """used_today 達到 daily_limit 時應切換至 PADDLEOCR_FALLBACK（澄清 Q2）。"""
    original_limit = queue_manager._quota.daily_limit
    original_used = queue_manager._quota.used_today
    original_engine = queue_manager._quota.active_engine

    # Set quota to one below limit
    queue_manager._quota.daily_limit = 1
    queue_manager._quota.used_today = 0
    queue_manager._quota.active_engine = EngineType.GEMINI_PRIMARY

    await queue_manager.record_gemini_call()  # This should trigger switch

    assert queue_manager._quota.active_engine == EngineType.PADDLEOCR_FALLBACK

    # Restore
    queue_manager._quota.daily_limit = original_limit
    queue_manager._quota.used_today = original_used
    queue_manager._quota.active_engine = original_engine


@pytest.mark.asyncio
async def test_get_active_engine_returns_current_engine():
    """get_active_engine 應回傳當前使用的引擎。"""
    queue_manager._quota.active_engine = EngineType.GEMINI_PRIMARY
    engine = await queue_manager.get_active_engine()
    assert engine == EngineType.GEMINI_PRIMARY


def test_get_quota_includes_queue_depth():
    """get_quota 回傳的 QuotaStatus 應包含當前佇列深度。"""
    quota = queue_manager.get_quota()
    assert hasattr(quota, "queue_depth")
    assert quota.queue_depth >= 0
