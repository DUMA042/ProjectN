"""Upload hard cap: oversized streams are rejected and leave no partial file."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from owl.ingest.limits import UploadTooLarge, copy_with_cap


def test_copies_file_under_limit(tmp_path):
    dest = tmp_path / "ok.xlsx"
    written = copy_with_cap(io.BytesIO(b"x" * 1000), dest, limit_bytes=2000, chunk_bytes=256)
    assert written == 1000
    assert dest.exists() and dest.stat().st_size == 1000


def test_exactly_at_limit_is_allowed(tmp_path):
    dest = tmp_path / "edge.xlsx"
    assert copy_with_cap(io.BytesIO(b"y" * 512), dest, limit_bytes=512, chunk_bytes=128) == 512
    assert dest.exists()


def test_oversized_stream_is_rejected_and_partial_removed(tmp_path):
    dest = tmp_path / "big.xlsx"
    with pytest.raises(UploadTooLarge) as exc:
        copy_with_cap(io.BytesIO(b"z" * 5000), dest, limit_bytes=1000, chunk_bytes=256)
    assert exc.value.limit_mb == 0  # 1000 bytes // 1 MiB in this test
    assert not dest.exists(), "partial file must be deleted"


def test_source_error_also_removes_partial(tmp_path):
    class Exploding(io.BytesIO):
        calls = 0

        def read(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls > 1:
                raise OSError("disk gone")
            return super().read(16)

    dest = tmp_path / "boom.xlsx"
    with pytest.raises(OSError):
        copy_with_cap(Exploding(b"a" * 64), dest, limit_bytes=10_000, chunk_bytes=16)
    assert not dest.exists()


def test_route_rejects_file_above_configured_cap(monkeypatch, tmp_path):
    """End-to-end: the upload endpoint reports the rejection per file."""
    from fastapi.testclient import TestClient

    from api import main as app_module

    monkeypatch.setattr("owl.config.settings.max_upload_mb", 1, raising=False)
    monkeypatch.setattr("api.routes.ingestion.INBOX_DIR", Path(tmp_path))

    client = TestClient(app_module.app)
    payload = b"PK\x03\x04" + b"0" * (2 * 1024 * 1024)  # 2 MB > 1 MB cap
    res = client.post(
        "/api/ingest/upload",
        files={"files": ("too_big.xlsx", payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["results"] == []
    assert body["rejected"][0]["filename"] == "too_big.xlsx"
    assert "File too large (max 1 MB)" in body["rejected"][0]["reason"]
    assert list(tmp_path.glob("*.xlsx")) == [], "no partial file may remain"
