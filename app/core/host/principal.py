from __future__ import annotations

from typing import Protocol

from fastapi import Request

from app.core.config import Settings
from app.core.host.context import RequestContext, request_context_from_headers


class PrincipalResolutionError(RuntimeError):
    pass


class PrincipalResolver(Protocol):
    def resolve(self, request: Request) -> RequestContext: ...


class LocalHeaderPrincipalResolver:
    """Explicit compatibility adapter for local development only."""

    def resolve(self, request: Request) -> RequestContext:
        return request_context_from_headers(request.headers)


class TrustedStatePrincipalResolver:
    """Production adapter for an upstream host-authenticated principal."""

    def resolve(self, request: Request) -> RequestContext:
        principal = getattr(request.state, "hify_principal", None)
        if not isinstance(principal, RequestContext):
            raise PrincipalResolutionError("Verified Hify principal is required")
        return principal


def principal_resolver_for(settings: Settings) -> PrincipalResolver:
    if settings.host_identity_mode == "trusted_state":
        return TrustedStatePrincipalResolver()
    return LocalHeaderPrincipalResolver()
