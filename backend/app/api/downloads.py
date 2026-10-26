"""Attachment responses for stored files (evidence and certificates).

Stored bytes come from the configured blob backend (local disk or private Supabase Storage),
so downloads send bytes rather than a file path. The `Content-Disposition` value is built
exactly as Starlette's `FileResponse` builds it, so downloads look the same as before.
Always an attachment, never rendered inline.
"""

from urllib.parse import quote

from fastapi import Response


def attachment(
    content: bytes, *, media_type: str, filename: str, headers: dict[str, str]
) -> Response:
    quoted = quote(filename)
    disposition = (
        f'attachment; filename="{filename}"'
        if quoted == filename
        else f"attachment; filename*=utf-8''{quoted}"
    )
    return Response(
        content,
        media_type=media_type,
        headers={**headers, "Content-Disposition": disposition},
    )
