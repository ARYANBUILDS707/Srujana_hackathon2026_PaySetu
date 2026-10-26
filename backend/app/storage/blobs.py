"""Where stored file bytes live: the local disk (default) or a private Supabase Storage bucket.

The evidence and business-document stores do all checking themselves (size, magic bytes, PDF
structure, SHA-256) on a local temp file, then hand the finished file to a `BlobBackend`
under a content-addressed name. A backend only stores and returns bytes, unchanged:

- Never overwrites: a name that exists already holds the same bytes (the name ends in the
  SHA-256), so a second `put` is a no-op.
- `read` returns the exact stored bytes, or None when the object is missing.

`SupabaseBlobs` talks to the Storage REST API over HTTPS with the service-role key, which is
read from the server's environment only and never logged or sent to the browser. The bucket
must be private: objects are only ever served through PaySetu's authenticated, owner-checked
download routes, never by URL. Requests have a timeout and are not retried (AGENTS.md 7).
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

from app.config import Settings, StorageBackend
from app.errors import IntegrationFailed

SUPABASE_TIMEOUT_SECONDS = 30
STORAGE_UNAVAILABLE = "File storage is unavailable right now. Please try again."


class BlobBackend(Protocol):
    def put(self, name: str, source: Path) -> None:
        """Store `source` under `name` unless `name` exists already."""

    def read(self, name: str) -> bytes | None:
        """The stored bytes, or None if there is no such object."""


class LocalBlobs:
    """Files under `root`: directories 0700, files 0600, moved into place, never overwritten."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def path(self, name: str) -> Path:
        path = (self.root / name).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Storage name is outside the store.")
        return path

    def put(self, name: str, source: Path) -> None:
        final = self.path(name)
        final.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if final.exists():
            source.unlink(missing_ok=True)
            return
        os.chmod(source, 0o600)
        os.replace(source, final)

    def read(self, name: str) -> bytes | None:
        path = self.path(name)
        return path.read_bytes() if path.is_file() else None


class SupabaseBlobs:
    """Objects in one private Supabase Storage bucket, reached with the service-role key."""

    def __init__(self, project_url: str, service_role_key: str, bucket: str) -> None:
        self._base = f"{project_url.rstrip('/')}/storage/v1/object"
        self._key = service_role_key
        self._bucket = quote(bucket, safe="")

    def _url(self, kind: str, name: str) -> str:
        return f"{self._base}{kind}/{self._bucket}/{quote(name, safe='/')}"

    def _request(self, method: str, url: str, body: bytes | None = None) -> urllib.request.Request:
        headers = {"Authorization": f"Bearer {self._key}", "apikey": self._key}
        if body is not None:
            # Stored as opaque bytes; PaySetu records and serves the real type itself.
            headers["Content-Type"] = "application/octet-stream"
            headers["x-upsert"] = "false"  # never overwrite
        return urllib.request.Request(url, data=body, method=method, headers=headers)

    def put(self, name: str, source: Path) -> None:
        request = self._request("POST", self._url("", name), source.read_bytes())
        try:
            with urllib.request.urlopen(request, timeout=SUPABASE_TIMEOUT_SECONDS):
                return
        except urllib.error.HTTPError as error:
            if _is_duplicate(error):
                return  # same name = same SHA-256 = same bytes, already stored
            raise IntegrationFailed(STORAGE_UNAVAILABLE, code="storage_unavailable") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise IntegrationFailed(STORAGE_UNAVAILABLE, code="storage_unavailable") from None
        finally:
            source.unlink(missing_ok=True)

    def read(self, name: str) -> bytes | None:
        request = self._request("GET", self._url("/authenticated", name))
        try:
            with urllib.request.urlopen(request, timeout=SUPABASE_TIMEOUT_SECONDS) as response:
                data: bytes = response.read()
                return data
        except urllib.error.HTTPError as error:
            if _is_not_found(error):
                return None
            raise IntegrationFailed(STORAGE_UNAVAILABLE, code="storage_unavailable") from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise IntegrationFailed(STORAGE_UNAVAILABLE, code="storage_unavailable") from None


def _error_body(error: urllib.error.HTTPError) -> dict[str, object]:
    try:
        body = json.loads(error.read() or b"{}")
    except (ValueError, OSError):
        return {}
    return body if isinstance(body, dict) else {}


def _is_duplicate(error: urllib.error.HTTPError) -> bool:
    # Supabase answers an existing object with 409, or 400 carrying statusCode "409".
    body = _error_body(error)
    return (
        error.code == 409
        or str(body.get("statusCode")) == "409"
        or (str(body.get("error", "")).lower() == "duplicate")
    )


def _is_not_found(error: urllib.error.HTTPError) -> bool:
    # Supabase answers a missing object with 404, or 400 carrying statusCode "404".
    body = _error_body(error)
    return (
        error.code == 404
        or str(body.get("statusCode")) == "404"
        or (str(body.get("error", "")).lower() == "not_found")
    )


def build_remote_blobs(settings: Settings) -> SupabaseBlobs | None:
    """The Supabase backend when STORAGE_BACKEND=supabase; None means local files."""
    if settings.storage_backend is not StorageBackend.SUPABASE:
        return None
    # Settings validation guarantees both values for this backend.
    assert settings.supabase_url is not None and settings.supabase_service_role_key is not None
    return SupabaseBlobs(
        settings.supabase_url,
        settings.supabase_service_role_key.get_secret_value(),
        settings.supabase_storage_bucket,
    )
