import asyncio
import pytest
from fastapi import HTTPException
from app.core.uploads import read_upload_limited


class FakeUpload:
    def __init__(self, content: bytes):
        self.content = content
        self.offset = 0
        self.closed = False

    async def read(self, size: int):
        chunk = self.content[self.offset:self.offset + size]
        self.offset += len(chunk)
        return chunk

    async def close(self):
        self.closed = True


def test_upload_at_limit_is_accepted():
    upload = FakeUpload(b"x" * 1024)
    assert asyncio.run(read_upload_limited(upload, max_bytes=1024)) == b"x" * 1024


def test_upload_over_limit_is_rejected_and_closed():
    upload = FakeUpload(b"x" * 1025)
    with pytest.raises(HTTPException) as error:
        asyncio.run(read_upload_limited(upload, max_bytes=1024))
    assert error.value.status_code == 413
    assert upload.closed is True
