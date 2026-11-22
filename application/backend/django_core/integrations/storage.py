from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional
import uuid
import boto3
from django.conf import settings
from common.exceptions import ValidationDomainError

ALLOWED_MIME_SIGNATURES: dict[str, tuple[str, ...]] = {
    "application/pdf": (".pdf",),
    "image/jpeg": (".jpg", ".jpeg"),
    "image/png": (".png",),
    "image/webp": (".webp",),
    "image/x-icon": (".ico",),
    "image/vnd.microsoft.icon": (".ico",),
    "text/csv": (".csv",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (".xlsx",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (".docx",),
}

DANGEROUS_EXTENSIONS = {
    ".exe", ".bat", ".cmd", ".sh", ".ps1", ".php", ".py", ".rb", ".pl",
    ".js", ".mjs", ".cjs", ".html", ".htm", ".svg", ".jsp", ".asp", ".aspx", ".dll", ".so",
}


def validate_uploaded_file(*, filename: str, content_type: str, content: bytes, max_bytes: Optional[int] = None) -> tuple[str, str]:
    """
    Validates uploaded file extension, size, declared MIME type, and magic-byte signature
    to reject executables, scripts, SVG/HTML XSS payloads, and spoofed binary headers.
    """
    limit = max_bytes or getattr(settings, "MAX_UPLOAD_FILE_BYTES", 10 * 1024 * 1024)
    if not content:
        raise ValidationDomainError("فایل ارسالی خالی است.")
    if len(content) > limit:
        raise ValidationDomainError(f"حجم فایل بیش از سقف مجاز ({limit // (1024 * 1024)} مگابایت) است.")

    clean_name = Path(filename or "upload.bin").name
    suffix = Path(clean_name).suffix.lower()
    if suffix in DANGEROUS_EXTENSIONS or suffix == "":
        raise ValidationDomainError("پسوند فایل مجاز نیست یا در فهرست فرمت‌های ناامن قرار دارد.")

    mime = (content_type or "").split(";")[0].strip().lower()
    if suffix == ".ico" and mime in ("", "application/octet-stream"):
        mime = "image/x-icon"
    allowed_exts = ALLOWED_MIME_SIGNATURES.get(mime)
    if not allowed_exts or suffix not in allowed_exts:
        raise ValidationDomainError("نوع محتوای فایل (MIME) با پسوند یا فرمت‌های مجاز سامانه مطابقت ندارد.")

    # Magic-byte header verification
    header = content[:16]
    if mime == "application/pdf" and not header.startswith(b"%PDF-"):
        raise ValidationDomainError("محتوای فایل با ساختار استاندارد PDF مطابقت ندارد.")
    if mime == "image/png" and not header.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValidationDomainError("محتوای فایل با تصویر PNG معتبر مطابقت ندارد.")
    if mime == "image/jpeg" and not header.startswith(b"\xff\xd8\xff"):
        raise ValidationDomainError("محتوای فایل با تصویر JPEG معتبر مطابقت ندارد.")
    if mime == "image/webp" and not (header.startswith(b"RIFF") and content[8:12] == b"WEBP"):
        raise ValidationDomainError("محتوای فایل با تصویر WebP معتبر مطابقت ندارد.")
    if mime in ("image/x-icon", "image/vnd.microsoft.icon") and not (
        header.startswith(b"\x00\x00\x01\x00") or header.startswith(b"\x00\x00\x02\x00")
    ):
        raise ValidationDomainError("محتوای فایل با تصویر آیکن (ICO) معتبر مطابقت ندارد.")
    if mime in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ) and not header.startswith(b"PK\x03\x04"):
        raise ValidationDomainError("محتوای فایل با ساختار معتبر Office XML مطابقت ندارد.")
    if mime == "text/csv":
        lowered = content[:2048].lower()
        if b"<script" in lowered or b"<html" in lowered or b"<?php" in lowered or b"\x00" in content[:512]:
            raise ValidationDomainError("محتوای CSV مشکوک یا مخرب شناسایی شد و رد گردید.")

    safe_stem = re.sub(r"[^a-zA-Z0-9_-]", "-", Path(clean_name).stem).strip("-") or "file"
    return f"{safe_stem[:60]}-{uuid.uuid4().hex[:8]}{suffix}", mime


@dataclass(frozen=True)
class StoredObjectResult:
    file_key: str
    url: str
    size_bytes: int
    mime_type: str
    provider_key: str


class StorageProviderBase(ABC):
    provider_key: str

    @abstractmethod
    def put_bytes(self, *, key_prefix: str, safe_filename: str, content: bytes, mime_type: str) -> StoredObjectResult:
        raise NotImplementedError

    @abstractmethod
    def get_bytes(self, *, file_key: str) -> bytes:
        raise NotImplementedError


class LocalSecureStorageAdapter(StorageProviderBase):
    provider_key = "local"

    def _root(self) -> Path:
        root = Path(settings.MEDIA_ROOT).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def put_bytes(self, *, key_prefix: str, safe_filename: str, content: bytes, mime_type: str) -> StoredObjectResult:
        clean_prefix = "/".join(p for p in key_prefix.strip("/").split("/") if p and ".." not in p)
        file_key = f"{clean_prefix}/{safe_filename}" if clean_prefix else safe_filename
        target = (self._root() / file_key).resolve()
        if not str(target).startswith(str(self._root())):
            raise ValidationDomainError("مسیر ذخیره‌سازی نامعتبر است.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return StoredObjectResult(
            file_key=file_key,
            url=f"{settings.MEDIA_URL.rstrip('/')}/{file_key}",
            size_bytes=len(content),
            mime_type=mime_type,
            provider_key=self.provider_key,
        )

    def get_bytes(self, *, file_key: str) -> bytes:
        target = (self._root() / file_key.lstrip("/")).resolve()
        if not str(target).startswith(str(self._root())) or not target.exists():
            raise FileNotFoundError(file_key)
        return target.read_bytes()


class S3CompatibleStorageAdapter(StorageProviderBase):
    provider_key = "s3"

    def _client(self):
        return boto3.client(
            "s3",
            endpoint_url=getattr(settings, "S3_ENDPOINT_URL", None) or None,
            aws_access_key_id=getattr(settings, "S3_ACCESS_KEY_ID", ""),
            aws_secret_access_key=getattr(settings, "S3_SECRET_ACCESS_KEY", ""),
            region_name=getattr(settings, "S3_REGION", "us-east-1"),
        )

    def put_bytes(self, *, key_prefix: str, safe_filename: str, content: bytes, mime_type: str) -> StoredObjectResult:
        bucket = getattr(settings, "S3_BUCKET_NAME", "")
        if not bucket:
            raise RuntimeError("S3_BUCKET_NAME is not configured.")
        file_key = f"{key_prefix.strip('/')}/{safe_filename}"
        self._client().put_object(
            Bucket=bucket,
            Key=file_key,
            Body=content,
            ContentType=mime_type,
        )
        return StoredObjectResult(
            file_key=file_key,
            url=f"s3://{bucket}/{file_key}",
            size_bytes=len(content),
            mime_type=mime_type,
            provider_key=self.provider_key,
        )

    def get_bytes(self, *, file_key: str) -> bytes:
        bucket = getattr(settings, "S3_BUCKET_NAME", "")
        obj = self._client().get_object(Bucket=bucket, Key=file_key)
        return obj["Body"].read()
