from __future__ import annotations

from fastapi import Request

from app.core.host.context import RequestContext, request_context_from_headers


def get_request_context(request: Request) -> RequestContext:
    return request_context_from_headers(request.headers)
