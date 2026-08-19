from dataclasses import dataclass

from fastapi import Request


@dataclass(frozen=True, slots=True)
class RequestContext:
    ip: str | None
    user_agent: str | None
    request_id: str | None


def build_request_context(request: Request) -> RequestContext:
    return RequestContext(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
    )
