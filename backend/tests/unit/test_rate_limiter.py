"""Unit tests for rate limiter configuration (T027).

Verifies slowapi limiter is properly configured with settings-driven RPM.
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from app.core.rate_limiter import limiter


class TestRateLimiterConfig:
    def test_rate_limit_string_from_settings(self):
        """RPM 設定應由 settings 組合，不可硬編碼。"""
        rate_str = settings.rate_limit_string
        assert "/" in rate_str
        assert str(settings.rate_limit_rpm) in rate_str

    def test_limiter_instance_exists(self):
        """Limiter 實例應已建立（集中式，憲章原則六）。"""
        assert limiter is not None

    def test_default_rpm_is_within_gemini_free_tier(self):
        """預設 RPM 不超過 Gemini 免費層上限 15。"""
        assert settings.rate_limit_rpm <= 15
