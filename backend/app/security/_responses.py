"""Problem responses sent directly from ASGI middleware (outside FastAPI's handlers)."""

from starlette.types import Receive, Scope, Send

from app.errors import problem_response


async def send_problem(
    scope: Scope,
    receive: Receive,
    send: Send,
    *,
    status: int,
    code: str,
    title: str,
    detail: str,
    headers: dict[str, str] | None = None,
) -> None:
    request_id = scope.get("state", {}).get("request_id")
    response = problem_response(
        status=status, code=code, title=title, detail=detail, request_id=request_id, headers=headers
    )
    await response(scope, receive, send)
