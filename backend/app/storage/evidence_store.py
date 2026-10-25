"""Content-addressed evidence store (ARCHITECTURE.md Sections 3.1 and 14; DATABASE.md 3.9).

Uploads are streamed to a temp file while their SHA-256 is computed, checked against the size
limit and a type allow-list (magic bytes, never the client's filename or MIME type), then moved
to `evidence/{supplier_id}/{sha[0:2]}/{sha}`. Stored bytes are never modified or overwritten:
identical content maps to the same key. Directories are 0700 and files 0600.
"""

import hashlib
import os
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from app.errors import PayloadTooLarge, UnsupportedFileType

ALLOWED_TYPES = (
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/heic",
    "message/rfc822",
    "text/plain",
)
_HEIC_BRANDS = {b"heic", b"heix", b"heim", b"heis", b"hevc", b"mif1", b"msf1"}
_EMAIL_HEADER = re.compile(rb"^[A-Za-z][A-Za-z0-9-]*: ", re.MULTILINE)


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    sha256: str
    size_bytes: int
    mime_type: str


class EvidenceStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def save(self, supplier_id: str, chunks: Iterable[bytes], *, max_bytes: int) -> StoredFile:
        tmp_dir = self._ensure_dir(self.root / "tmp")
        tmp_path = tmp_dir / uuid.uuid4().hex
        digest = hashlib.sha256()
        size = 0
        try:
            with open(tmp_path, "wb") as handle:
                for chunk in chunks:
                    size += len(chunk)
                    if size > max_bytes:
                        raise PayloadTooLarge("The file is larger than the upload limit.")
                    digest.update(chunk)
                    handle.write(chunk)
            if size == 0:
                raise UnsupportedFileType("The file is empty.")
            mime_type = detect_mime_type(tmp_path)
            sha256 = digest.hexdigest()
            key = f"evidence/{_safe_segment(supplier_id)}/{sha256[:2]}/{sha256}"
            final = self.root / key
            self._ensure_dir(final.parent)
            if final.exists():
                tmp_path.unlink()  # same content already stored; never overwrite
            else:
                os.chmod(tmp_path, 0o600)
                os.replace(tmp_path, final)
            return StoredFile(key, sha256, size, mime_type)
        finally:
            tmp_path.unlink(missing_ok=True)

    def path_for(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        if not path.is_relative_to(self.root / "evidence"):
            raise ValueError("Storage key is outside the evidence store.")
        return path

    def current_sha256(self, storage_key: str) -> str | None:
        """Re-hash stored bytes; None if the file is missing."""
        path = self.path_for(storage_key)
        if not path.is_file():
            return None
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _ensure_dir(path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path


def detect_mime_type(path: Path) -> str:
    with open(path, "rb") as handle:
        head = handle.read(16)
    if head.startswith(b"%PDF-"):
        return "application/pdf"
    if head.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if head[4:8] == b"ftyp" and head[8:12] in _HEIC_BRANDS:
        return "image/heic"
    data = path.read_bytes()
    if b"\x00" not in data:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            looks_like_email = _EMAIL_HEADER.match(data) and b"\nFrom: " in b"\n" + data
            return "message/rfc822" if looks_like_email else "text/plain"
    raise UnsupportedFileType("Allowed types: PDF, JPEG, PNG, HEIC, email (.eml) and UTF-8 text.")


def _safe_segment(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", value):
        raise ValueError("Invalid storage path segment.")
    return value
