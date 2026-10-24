"""Evidence store: write-once content addressing, type detection and path safety."""

import hashlib
from pathlib import Path

import pytest

from app.errors import UnsupportedFileType
from app.storage.evidence_store import EvidenceStore, detect_mime_type

SUPPLIER = "0f1e2d3c-0000-4000-8000-000000000001"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (b"%PDF-1.7 sample", "application/pdf"),
        (b"\xff\xd8\xff\xe0 jpeg sample", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n png sample", "image/png"),
        (b"\x00\x00\x00\x18ftypheic sample", "image/heic"),
        (b"plain text sample", "text/plain"),
    ],
)
def test_detects_allowed_types_by_magic_bytes(
    tmp_path: Path, content: bytes, expected: str
) -> None:
    path = tmp_path / "f"
    path.write_bytes(content)
    assert detect_mime_type(path) == expected


def test_rejects_non_utf8_binary(tmp_path: Path) -> None:
    path = tmp_path / "f"
    path.write_bytes(b"\xc3\x28 invalid utf-8")
    with pytest.raises(UnsupportedFileType):
        detect_mime_type(path)


def test_same_bytes_map_to_one_write_once_file(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path)
    first = store.save(SUPPLIER, [b"%PDF-", b" same bytes"], max_bytes=1024)
    second = store.save(SUPPLIER, [b"%PDF- same bytes"], max_bytes=1024)
    assert first == second
    assert first.sha256 == hashlib.sha256(b"%PDF- same bytes").hexdigest()
    path = store.path_for(first.storage_key)
    assert path.read_bytes() == b"%PDF- same bytes"
    assert oct(path.stat().st_mode & 0o777) == "0o600"
    assert list((tmp_path / "tmp").iterdir()) == []  # temp files cleaned up
    assert store.current_sha256(first.storage_key) == first.sha256


def test_missing_file_hash_is_none(tmp_path: Path) -> None:
    assert EvidenceStore(tmp_path).current_sha256("evidence/x/ab/" + "a" * 64) is None


@pytest.mark.parametrize("key", ["../outside", "evidence/../../etc/passwd", "tmp/whatever"])
def test_storage_keys_cannot_escape_the_evidence_root(tmp_path: Path, key: str) -> None:
    with pytest.raises(ValueError):
        EvidenceStore(tmp_path).path_for(key)


@pytest.mark.parametrize("supplier_id", ["../x", "a/b", ""])
def test_supplier_segment_is_validated(tmp_path: Path, supplier_id: str) -> None:
    with pytest.raises(ValueError):
        EvidenceStore(tmp_path).save(supplier_id, [b"%PDF- x"], max_bytes=1024)
