import os
from fastapi import HTTPException, UploadFile


def configured_upload_limit() -> int:
    try:
        value = int(os.environ.get("MAX_UPLOAD_FILE_BYTES", str(10 * 1024 * 1024)))
    except ValueError:
        value = 10 * 1024 * 1024
    return max(1024, min(value, 100 * 1024 * 1024))


async def read_upload_limited(upload: UploadFile, *, max_bytes: int | None = None) -> bytes:
    """Read an upload in bounded chunks and stop as soon as the configured cap is exceeded."""
    limit = max_bytes or configured_upload_limit()
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await upload.read(min(1024 * 1024, limit - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            await upload.close()
            raise HTTPException(
                status_code=413,
                detail=f"حجم فایل از سقف مجاز {limit} بایت بیشتر است.",
            )
        chunks.append(chunk)
    return b"".join(chunks)
