"""اعتبارسنجی فایل و دسترسی به مخازن عمومی و خصوصی."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import os
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

    def delete_object(self, *, file_key: str) -> None:
        raise NotImplementedError

    def get_legacy_public_bytes(self, *, file_key: str) -> bytes:
        return self.get_bytes(file_key=file_key)

    def delete_legacy_public_object(self, *, file_key: str) -> None:
        self.delete_object(file_key=file_key)


class LocalSecureStorageAdapter(StorageProviderBase):
    """فایل‌ها را در ریشه‌های مجزای عمومی و خصوصی نگه می‌دارد."""
    provider_key = "local"

    def _root(self, *, private: bool = False) -> Path:
        """ریشهٔ مطلق را برای عملیات فایل و مسیرهای بلند ویندوز آماده می‌کند."""
        configured = getattr(settings, "PRIVATE_MEDIA_ROOT", None) if private else settings.MEDIA_ROOT
        root = Path(configured or (Path(settings.MEDIA_ROOT).parent / "private_media")).resolve()
        if os.name == "nt":
            path = str(root)
            if not path.startswith("\\\\?\\"):
                root = Path("\\\\?\\UNC\\" + path[2:] if path.startswith("\\\\") else "\\\\?\\" + path)
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _safe_relative_key(file_key: str) -> tuple[bool, str]:
        """کلید منطقی را اعتبارسنجی و بخش خصوصی را از مسیر نسبی جدا می‌کند."""
        if not isinstance(file_key, str) or not file_key or "\\" in file_key:
            raise ValidationDomainError("کلید فایل نامعتبر است.")
        private = file_key.startswith("private/")
        relative = file_key[len("private/"):] if private else file_key
        candidate = Path(relative)
        if not candidate.parts or candidate.anchor or any(
            part in ("", ".", "..") or ":" in part or "\x00" in part for part in candidate.parts
        ) or candidate.is_reserved():
            raise ValidationDomainError("مسیر فایل نامعتبر است.")
        return private, candidate.as_posix()

    @staticmethod
    def _contained_path(root: Path, relative_key: str) -> Path:
        """پس از حل مسیر واقعی، قرارگیری فایل داخل ریشهٔ مجاز را بررسی می‌کند."""
        target = (root / relative_key).resolve()
        if not target.is_relative_to(root):
            raise ValidationDomainError("مسیر فایل خارج از مخزن مجاز است.")
        return target

    def put_bytes(self, *, key_prefix: str, safe_filename: str, content: bytes, mime_type: str) -> StoredObjectResult:
        """داده را در مسیر کنترل‌شده ذخیره می‌کند و کلید مخزن را برمی‌گرداند."""
        if not safe_filename or Path(safe_filename).name != safe_filename or safe_filename in (".", ".."):
            raise ValidationDomainError("نام فایل نامعتبر است.")
        prefix = key_prefix.strip("/")
        parts = Path(prefix).parts if prefix else ()
        if any(part in (".", "..") for part in parts) or "\\" in prefix:
            raise ValidationDomainError("مسیر ذخیره‌سازی نامعتبر است.")
        private = bool(parts and parts[0] == "private")
        relative_prefix = "/".join(parts[1:] if private else parts)
        relative_key = f"{relative_prefix}/{safe_filename}" if relative_prefix else safe_filename
        root = self._root(private=private)
        file_key = f"private/{relative_key}" if private else relative_key
        _, checked_key = self._safe_relative_key(file_key)
        target = self._contained_path(root, checked_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return StoredObjectResult(
            file_key=file_key,
            # Private objects are intentionally never exposed as public media URLs.
            url="" if private else f"{settings.MEDIA_URL.rstrip('/')}/{file_key}",
            size_bytes=len(content),
            mime_type=mime_type,
            provider_key=self.provider_key,
        )

    def get_bytes(self, *, file_key: str) -> bytes:
        private, relative_key = self._safe_relative_key(file_key)
        root = self._root(private=private)
        target = self._contained_path(root, relative_key)
        if not target.is_file():
            raise FileNotFoundError(file_key)
        return target.read_bytes()

    def delete_object(self, *, file_key: str) -> None:
        private, relative_key = self._safe_relative_key(file_key)
        target = self._contained_path(self._root(private=private), relative_key)
        if target.exists():
            target.unlink()

    def get_legacy_public_bytes(self, *, file_key: str) -> bytes:
        if (
            not isinstance(file_key, str) or not file_key or file_key.startswith("/")
            or "\\\\" in file_key or "\x00" in file_key
            or any(part in ("", ".", "..") for part in Path(file_key).parts)
        ):
            raise FileNotFoundError(file_key)
        target = self._contained_path(self._root(private=False), Path(file_key))
        if not target.is_file():
            raise FileNotFoundError(file_key)
        return target.read_bytes()

    def delete_legacy_public_object(self, *, file_key: str) -> None:
        if (
            not isinstance(file_key, str) or not file_key or file_key.startswith("/")
            or "\\\\" in file_key or "\x00" in file_key
            or any(part in ("", ".", "..") for part in Path(file_key).parts)
        ):
            raise FileNotFoundError(file_key)
        target = self._contained_path(self._root(private=False), Path(file_key))
        if target.exists():
            target.unlink()


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
        prefix = key_prefix.strip("/")
        parts = Path(prefix).parts if prefix else ()
        is_private = bool(parts and parts[0] == "private")
        bucket = (getattr(settings, "S3_PRIVATE_BUCKET_NAME", "") if is_private
                  else getattr(settings, "S3_BUCKET_NAME", ""))
        if not bucket:
            raise RuntimeError("S3_PRIVATE_BUCKET_NAME is required for private objects." if is_private else "S3_BUCKET_NAME is not configured.")
        parts = Path(prefix).parts if prefix else ()
        if (
            not safe_filename or Path(safe_filename).name != safe_filename
            or "\\\\" in prefix or any(part in ("", ".", "..") for part in parts)
        ):
            raise ValidationDomainError("مسیر ذخیره‌سازی نامعتبر است.")
        file_key = f"{prefix}/{safe_filename}" if prefix else safe_filename
        self._client().put_object(
            Bucket=bucket,
            Key=file_key,
            Body=content,
            ContentType=mime_type,
        )
        public_url = "" if is_private else self._client().generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": file_key}, ExpiresIn=3600
        )
        return StoredObjectResult(
            file_key=file_key,
            url=public_url,
            size_bytes=len(content),
            mime_type=mime_type,
            provider_key=self.provider_key,
        )

    def get_bytes(self, *, file_key: str) -> bytes:
        if (
            not isinstance(file_key, str) or not file_key or file_key.startswith("/")
            or "\\\\" in file_key or "\x00" in file_key
            or any(part in ("", ".", "..") for part in Path(file_key).parts)
        ):
            raise FileNotFoundError(file_key)
        is_private = file_key.startswith("private/")
        bucket = (getattr(settings, "S3_PRIVATE_BUCKET_NAME", "") if is_private
                  else getattr(settings, "S3_BUCKET_NAME", ""))
        if not bucket:
            raise RuntimeError("S3_PRIVATE_BUCKET_NAME is required for private objects." if is_private else "S3_BUCKET_NAME is not configured.")
        obj = self._client().get_object(Bucket=bucket, Key=file_key)
        return obj["Body"].read()

    def delete_object(self, *, file_key: str) -> None:
        if not isinstance(file_key, str) or not file_key or file_key.startswith("/") or "\\\\" in file_key or any(
            part in ("", ".", "..") for part in Path(file_key).parts
        ):
            raise FileNotFoundError(file_key)
        is_private = file_key.startswith("private/")
        bucket = (getattr(settings, "S3_PRIVATE_BUCKET_NAME", "") if is_private
                  else getattr(settings, "S3_BUCKET_NAME", ""))
        if not bucket:
            raise RuntimeError("S3_PRIVATE_BUCKET_NAME is required for private objects." if is_private else "S3_BUCKET_NAME is not configured.")
        self._client().delete_object(Bucket=bucket, Key=file_key)


    def get_legacy_public_bytes(self, *, file_key: str) -> bytes:
        if (
            not isinstance(file_key, str) or not file_key or file_key.startswith("/")
            or "\\\\" in file_key or "\x00" in file_key
            or any(part in ("", ".", "..") for part in Path(file_key).parts)
        ):
            raise FileNotFoundError(file_key)
        bucket = getattr(settings, "S3_BUCKET_NAME", "")
        if not bucket:
            raise RuntimeError("S3_BUCKET_NAME is not configured.")
        obj = self._client().get_object(Bucket=bucket, Key=file_key)
        return obj["Body"].read()

    def delete_legacy_public_object(self, *, file_key: str) -> None:
        if (
            not isinstance(file_key, str) or not file_key or file_key.startswith("/")
            or "\\\\" in file_key or "\x00" in file_key
            or any(part in ("", ".", "..") for part in Path(file_key).parts)
        ):
            raise FileNotFoundError(file_key)
        bucket = getattr(settings, "S3_BUCKET_NAME", "")
        if not bucket:
            raise RuntimeError("S3_BUCKET_NAME is not configured.")
        self._client().delete_object(Bucket=bucket, Key=file_key)
