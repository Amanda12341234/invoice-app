"""Unit tests for image validation logic (T021).

Tests all validation rules: MIME type, file size, dimensions, MD5 dedup.
"""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from PIL import Image

from app.core.queue_manager import compute_md5, find_duplicate, register_md5


def make_jpeg(width=800, height=600) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestMIMETypeValidation:
    def test_jpeg_accepted(self):
        from app.routers.invoices import ALLOWED_MIME_TYPES
        assert "image/jpeg" in ALLOWED_MIME_TYPES

    def test_png_accepted(self):
        from app.routers.invoices import ALLOWED_MIME_TYPES
        assert "image/png" in ALLOWED_MIME_TYPES

    def test_text_rejected(self):
        from app.routers.invoices import ALLOWED_MIME_TYPES
        assert "text/plain" not in ALLOWED_MIME_TYPES


class TestFileSizeValidation:
    def test_file_within_limit_passes(self):
        from app.routers.invoices import _validate_image
        small = make_jpeg()
        result = _validate_image(small, "image/jpeg")
        assert result is None  # no error

    def test_file_over_limit_returns_413(self):
        from app.routers.invoices import _validate_image
        from app.core.config import settings

        oversized = b"x" * (settings.max_file_size_bytes + 1)
        result = _validate_image(oversized, "image/jpeg")
        assert result is not None
        assert result.status_code == 413


class TestDimensionValidation:
    def test_large_image_passes(self):
        from app.routers.invoices import _validate_image
        content = make_jpeg(1280, 960)
        result = _validate_image(content, "image/jpeg")
        assert result is None

    def test_tiny_image_returns_400(self):
        from app.routers.invoices import _validate_image
        content = make_jpeg(100, 100)
        result = _validate_image(content, "image/jpeg")
        assert result is not None
        assert result.status_code == 400


class TestMD5Deduplication:
    def test_first_upload_not_duplicate(self):
        md5 = compute_md5(b"unique-image-data-xyz")
        result = find_duplicate(md5)
        assert result is None

    def test_second_upload_returns_existing_task_id(self):
        data = b"repeated-invoice-image-abc"
        md5 = compute_md5(data)
        register_md5(md5, "task-999")
        result = find_duplicate(md5)
        assert result == "task-999"
