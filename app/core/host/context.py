from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class RequestContext:
    actor_id: str = "local-user"
    actor_name: str = "Local User"
    tenant_id: str = "local"
    org_id: str = "local"
    roles: tuple[str, ...] = field(default_factory=tuple)
    permissions: tuple[str, ...] = field(default_factory=tuple)
    request_id: str = ""
    source: str = "local"
    locale: str = "zh-CN"

    def audit_metadata(self) -> dict[str, Any]:
        return {
            "actorId": self.actor_id,
            "actorName": self.actor_name,
            "tenantId": self.tenant_id,
            "orgId": self.org_id,
            "roles": list(self.roles),
            "permissions": list(self.permissions),
            "requestId": self.request_id,
            "source": self.source,
            "locale": self.locale,
        }


def request_context_from_headers(headers: Mapping[str, str]) -> RequestContext:
    actor_id = _header(headers, "X-Hify-Actor-Id") or "local-user"
    actor_name = _header(headers, "X-Hify-Actor-Name") or actor_id
    tenant_id = _header(headers, "X-Hify-Tenant-Id") or "local"
    org_id = _header(headers, "X-Hify-Org-Id") or tenant_id
    request_id = _header(headers, "X-Request-Id")
    source = _header(headers, "X-Hify-Source") or "local"
    locale = _header(headers, "X-Hify-Locale") or _accept_language(headers) or "zh-CN"
    return RequestContext(
        actor_id=actor_id,
        actor_name=actor_name,
        tenant_id=tenant_id,
        org_id=org_id,
        roles=tuple(_split_header(_header(headers, "X-Hify-Roles"))),
        permissions=tuple(_split_header(_header(headers, "X-Hify-Permissions"))),
        request_id=request_id,
        source=source,
        locale=locale,
    )


def _header(headers: Mapping[str, str], name: str) -> str:
    value = headers.get(name) or headers.get(name.lower()) or headers.get(name.upper()) or ""
    return str(value).strip()


def _split_header(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _accept_language(headers: Mapping[str, str]) -> str:
    raw = _header(headers, "Accept-Language")
    if not raw:
        return ""
    return raw.split(",", 1)[0].strip()
