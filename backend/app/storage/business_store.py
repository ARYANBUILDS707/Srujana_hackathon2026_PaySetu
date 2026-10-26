"""Private store for business documents (Phase 7B): Udyam certificate PDFs only.

Separate from the case Evidence Vault: files live under `STORAGE_DIR/business/` at
`certificates/{supplier_id}/{sha[0:2]}/{sha}` (generated names; the client's filename is never
part of a path). Directories 0700, files 0600, never overwritten, never served statically:
downloads go through an authenticated, ownership-checked route. Hosted deployments keep the
finished bytes in a private Supabase Storage bucket instead (`app/storage/blobs.py`), under
`business/certificates/...`; temp files and all checks stay local.

PDF checks are structural, not a full parser: the `%PDF-1.x`/`%PDF-2.0` header, an `%%EOF`
marker near the end, `startxref`, a document catalog (`/Root` or `/Catalog`), and no active
content (`/JavaScript`, `/JS`, `/Launch`, `/EmbeddedFile`, `/RichMedia`, `/XFA`). The bytes are
never opened, rendered or executed by PaySetu. A SHA-256 records exactly what was uploaded;
it says nothing about whether the certificate is genuine.
"""

import hashlib
import os
import posixpath
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from app.errors import PayloadTooLarge, UnsupportedFileType
from app.storage.blobs import BlobBackend, LocalBlobs

_HEADER = re.compile(rb"^%PDF-(1\.[0-7]|2\.0)")
_ACTIVE_CONTENT = re.compile(rb"/(JavaScript|JS|Launch|EmbeddedFile|RichMedia|XFA)\b")
_TAIL_BYTES = 2048


@dataclass(frozen=True)
class StoredDocument:
    storage_key: str
    sha256: str
    size_bytes: int


class BusinessDocumentStore:
    def __init__(
        self, storage_dir: Path, blobs: BlobBackend | None = None, name_prefix: str = ""
    ) -> None:
        """`blobs` defaults to files under STORAGE_DIR/business; a shared remote backend is
        given `name_prefix="business/"` so certificates and evidence never share names."""
        self.root = (storage_dir / "business").resolve()
        self.blobs: BlobBackend = blobs or LocalBlobs(self.root)
        self.name_prefix = name_prefix

    def save_pdf(
        self, supplier_id: str, chunks: Iterable[bytes], *, max_bytes: int
    ) -> StoredDocument:
        tmp_dir = self._ensure_dir(self.root / "tmp")
        tmp_path = tmp_dir / uuid.uuid4().hex
        digest = hashlib.sha256()
        size = 0
        try:
            fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as handle:
                for chunk in chunks:
                    size += len(chunk)
                    if size > max_bytes:
                        raise PayloadTooLarge(
                            f"The certificate is larger than {max_bytes // (1024 * 1024)} MB.",
                            code="file_too_large",
                        )
                    digest.update(chunk)
                    handle.write(chunk)
            check_pdf(tmp_path)
            sha256 = digest.hexdigest()
            key = f"certificates/{_safe_segment(supplier_id)}/{sha256[:2]}/{sha256}"
            # Identical bytes are stored once and never overwritten.
            self.blobs.put(self.name_prefix + key, tmp_path)
            return StoredDocument(key, sha256, size)
        finally:
            tmp_path.unlink(missing_ok=True)

    def _name(self, storage_key: str) -> str:
        normalised = posixpath.normpath(storage_key)
        if storage_key.startswith("/") or not normalised.startswith("certificates/"):
            raise ValueError("Storage key is outside the business document store.")
        return self.name_prefix + normalised

    def path_for(self, storage_key: str) -> Path:
        """The local file for a key (local backend only; used by tests and tamper checks)."""
        if not isinstance(self.blobs, LocalBlobs):
            raise ValueError("Stored files are not on the local disk.")
        return self.blobs.path(self._name(storage_key))

    def read(self, storage_key: str) -> bytes | None:
        """The exact stored bytes, or None if the file is missing."""
        return self.blobs.read(self._name(storage_key))

    def current_sha256(self, storage_key: str) -> str | None:
        content = self.read(storage_key)
        return None if content is None else hashlib.sha256(content).hexdigest()

    @staticmethod
    def _ensure_dir(path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        return path


def check_pdf(path: Path) -> None:
    """Raise `UnsupportedFileType` unless the file looks like a plain, inactive PDF."""
    size = path.stat().st_size
    if size == 0:
        raise UnsupportedFileType("The file is empty.")
    with open(path, "rb") as handle:
        head = handle.read(1024)
        handle.seek(max(0, size - _TAIL_BYTES))
        tail = handle.read()
    if not _HEADER.match(head):
        raise UnsupportedFileType("Upload the certificate as a PDF file.", code="not_a_pdf")
    if b"%%EOF" not in tail or b"startxref" not in tail:
        raise UnsupportedFileType(
            "This PDF looks incomplete or damaged. Download the certificate again and retry.",
            code="damaged_pdf",
        )
    data = path.read_bytes()
    if b"/Root" not in data and b"/Catalog" not in data:
        raise UnsupportedFileType(
            "This PDF looks incomplete or damaged. Download the certificate again and retry.",
            code="damaged_pdf",
        )
    if _ACTIVE_CONTENT.search(data):
        raise UnsupportedFileType(
            "This PDF contains scripts, attachments or interactive forms. Upload the plain "
            "certificate PDF.",
            code="pdf_active_content",
        )


def _safe_segment(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", value):
        raise ValueError("Invalid storage path segment.")
    return value
