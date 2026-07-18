from __future__ import annotations

from typing import Any

from app.core.errors import BizError, ErrorCode
from app.core.host.context import RequestContext


def ensure_customer_assistant_session_owner(
    session: dict[str, Any],
    request_context: RequestContext | None,
) -> None:
    if request_context is None or is_local_request_context(request_context):
        return
    context = dict(session.get("context_json") or {})
    host_context = context.get("hostContext")
    if not isinstance(host_context, dict):
        raise BizError(ErrorCode.FORBIDDEN, "Customer assistant session belongs to another tenant")
    if str(host_context.get("tenantId") or "") != request_context.tenant_id:
        raise BizError(ErrorCode.FORBIDDEN, "Customer assistant session belongs to another tenant")
    if str(host_context.get("orgId") or "") != request_context.org_id:
        raise BizError(ErrorCode.FORBIDDEN, "Customer assistant session belongs to another organization")


def is_local_request_context(request_context: RequestContext) -> bool:
    return (
        request_context.source == "local"
        and request_context.actor_id == "local-user"
        and request_context.actor_name in {"local-user", "Local User"}
        and request_context.tenant_id == "local"
        and request_context.org_id == "local"
        and not request_context.roles
        and not request_context.permissions
        and not request_context.request_id
    )


__all__ = [
    "ensure_customer_assistant_session_owner",
    "is_local_request_context",
]
