from io import BytesIO
from PIL import Image, ImageOps, UnidentifiedImageError
from common.exceptions import ValidationDomainError
from integrations.storage import validate_uploaded_file

ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FLOORPLAN_MIMES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


def validate_capture_image_upload(
    *,
    filename: str,
    content_type: str,
    content: bytes,
    max_mb: int = 20,
) -> tuple[str, str, int, int, bytes]:
    """
    Validates image extension, MIME signature, size, EXIF orientation normalization,
    and decodes pixel dimensions safely via Pillow without risking arbitrary file execution.
    """
    max_bytes = max(1, int(max_mb)) * 1024 * 1024
    safe_name, mime = validate_uploaded_file(
        filename=filename,
        content_type=content_type,
        content=content,
        max_bytes=max_bytes,
    )
    if mime not in ALLOWED_IMAGE_MIMES:
        raise ValidationDomainError("برای تصویربرداری تور مجازی فقط فرمت‌های JPG، PNG و WebP مجاز هستند.")

    try:
        with Image.open(BytesIO(content)) as img:
            img.verify()
        with Image.open(BytesIO(content)) as img2:
            img_oriented = ImageOps.exif_transpose(img2)
            width, height = img_oriented.size
            if width < 64 or height < 64:
                raise ValidationDomainError("ابعاد تصویر ارسالی بسیار کوچک و غیرقابل استفاده است.")
            if img_oriented.mode not in ("RGB", "RGBA"):
                img_oriented = img_oriented.convert("RGB")
            out = BytesIO()
            fmt = "JPEG" if mime == "image/jpeg" else ("WEBP" if mime == "image/webp" else "PNG")
            if fmt == "JPEG" and img_oriented.mode == "RGBA":
                img_oriented = img_oriented.convert("RGB")
            img_oriented.save(out, format=fmt, quality=92)
            normalized_bytes = out.getvalue()
    except ValidationDomainError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValidationDomainError("فایل تصویر آسیب‌دیده یا نامعتبر است و قابل خواندن نیست.") from exc

    return safe_name, mime, int(width), int(height), normalized_bytes


def validate_floorplan_upload(
    *,
    filename: str,
    content_type: str,
    content: bytes,
    max_mb: int = 25,
) -> tuple[str, str, str, int, int, bytes]:
    """
    Validates 2D floor plan upload (PNG, JPG, WEBP, or PDF).
    Explicitly rejects SVG/HTML/script files and malformed headers.
    Returns (safe_name, file_type, mime, width_px, height_px, normalized_bytes).
    """
    max_bytes = max(1, int(max_mb)) * 1024 * 1024
    lower = (filename or "").lower()
    if lower.endswith(".svg") or "svg" in (content_type or "").lower() or b"<svg" in content[:512].lower():
        raise ValidationDomainError("فایل SVG به دلایل امنیتی مجاز نیست؛ لطفاً پلان را با فرمت PNG، JPG، WebP یا PDF بارگذاری کنید.")

    safe_name, mime = validate_uploaded_file(
        filename=filename,
        content_type=content_type,
        content=content,
        max_bytes=max_bytes,
    )
    if mime not in ALLOWED_FLOORPLAN_MIMES:
        raise ValidationDomainError("فرمت پلان مجاز نیست. فرمت‌های قابل قبول: PNG، JPG، WebP و PDF.")

    if mime == "application/pdf":
        if not content.lstrip()[:8].startswith(b"%PDF-"):
            raise ValidationDomainError("ساختار فایل PDF پلان معتبر نیست.")
        # Logical A4/blueprint pixel reference space (1600x1131) when PDF uploaded
        return safe_name, "pdf", mime, 1600, 1131, content

    s_name, r_mime, width, height, normalized = validate_capture_image_upload(
        filename=safe_name,
        content_type=mime,
        content=content,
        max_mb=max_mb,
    )
    ext = "png" if r_mime == "image/png" else ("webp" if r_mime == "image/webp" else "jpg")
    return s_name, ext, r_mime, width, height, normalized
