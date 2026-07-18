from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from app.core.config import Settings, get_settings
from app.core.host.context import RequestContext
from app.core.host.principal import (
    PrincipalResolutionError,
    PrincipalResolver,
    principal_resolver_for,
)


def get_principal_resolver(
    settings: Settings = Depends(get_settings),
) -> PrincipalResolver:
    return principal_resolver_for(settings)


def get_request_context(
    request: Request,
    resolver: PrincipalResolver = Depends(get_principal_resolver),
) -> RequestContext:
    try:
        return resolver.resolve(request)
    except PrincipalResolutionError as exc:
        raise HTTPException(
            status_code=401,
            detail="Verified Hify principal is required",
        ) from exc
