"""Upload size guard.

Files are copied in chunks so an oversized workbook is rejected *before* it is
fully written to disk (and before any parsing/allocation happens). The partial
file is always removed on rejection.
"""
from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

CHUNK_BYTES = 1024 * 1024


class UploadTooLarge(Exception):
    """Raised when a stream exceeds the configured upload limit."""

    def __init__(self, limit_mb: int, written_bytes: int):
        self.limit_mb = limit_mb
        self.written_bytes = written_bytes
        super().__init__(f"File exceeds {limit_mb} MB")


def copy_with_cap(
    src: BinaryIO,
    dest_path: Path,
    limit_bytes: int,
    chunk_bytes: int = CHUNK_BYTES,
) -> int:
    """Copy *src* to *dest_path*, aborting past *limit_bytes*.

    Returns the number of bytes written. On rejection the partial file is
    deleted before :class:`UploadTooLarge` propagates, so a failed upload can
    never leave a half-written workbook behind.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        with open(dest_path, "wb") as out:
            while True:
                chunk = src.read(chunk_bytes)
                if not chunk:
                    break
                written += len(chunk)
                if written > limit_bytes:
                    raise UploadTooLarge(limit_bytes // (1024 * 1024), written)
                out.write(chunk)
    except UploadTooLarge:
        dest_path.unlink(missing_ok=True)
        raise
    except Exception:
        dest_path.unlink(missing_ok=True)
        raise
    return written
