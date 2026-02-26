"""Image validation utilities (US2, T023).

Provides standalone validation functions used by the upload router.
All validation is done before any OCR engine is invoked.
"""
from __future__ import annotations

from io import BytesIO

from PIL import Image, UnidentifiedImageError

from app.core.config import settings

ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/heic",
    "image/heif",
})

MIN_WIDTH = 640
MIN_HEIGHT = 480


class ValidationError(Exception):
    """Raised when image fails validation. Contains error_code for API response."""
    def __init__(self, error_code: str, message: str, http_status: int = 400):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.http_status = http_status


def validate(content: bytes, mime_type: str) -> None:
    """Validate image content and MIME type. Raises ValidationError on failure."""
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            "INVALID_FORMAT",
            f"不支援的圖片格式（{mime_type}），請使用 JPEG 或 PNG",
            400,
        )

    if len(content) > settings.max_file_size_bytes:
        raise ValidationError(
            "IMAGE_TOO_LARGE",
            f"圖片超過 {settings.max_file_size_mb} MB 上限",
            413,
        )

    try:
        img = Image.open(BytesIO(content))
        if img.width < MIN_WIDTH or img.height < MIN_HEIGHT:
            raise ValidationError(
                "IMAGE_TOO_SMALL",
                f"圖片解析度不足（{img.width}×{img.height}），"
                f"請確保寬度 ≥ {MIN_WIDTH}px、高度 ≥ {MIN_HEIGHT}px",
                400,
            )
    except UnidentifiedImageError:
        raise ValidationError("INVALID_FORMAT", "無法解析圖片內容，請重新拍攝", 400)
