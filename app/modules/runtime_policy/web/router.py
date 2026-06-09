from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.responses import success
from app.modules.runtime_policy.domain.resolver import RuntimePolicyResolveContext, RuntimePolicyResolver
from app.modules.runtime_policy.domain.service import RuntimePolicyProfileService
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository
from app.modules.runtime_policy.web.schemas import RuntimePolicyProfileRequest

router = APIRouter(prefix="/api/v1/runtime-policy", tags=["runtime-policy"])


def get_runtime_policy_service(session: Session = Depends(get_session)) -> RuntimePolicyProfileService:
    return RuntimePolicyProfileService(RuntimePolicyRepository(session))


def get_runtime_policy_resolver(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RuntimePolicyResolver:
    return RuntimePolicyResolver(RuntimePolicyRepository(session), settings)


@router.get("/effective-profile")
def get_effective_profile(
    tenant_id: str = Query("", alias="tenantId"),
    bot_id: str = Query("", alias="botId"),
    channel: str = "",
    session_id: str = Query("", alias="sessionId"),
    sop_group: str = Query("", alias="sopGroup"),
    resolver: RuntimePolicyResolver = Depends(get_runtime_policy_resolver),
) -> dict[str, Any]:
    return success(
        resolver.resolve(
            RuntimePolicyResolveContext(
                tenant_id=tenant_id,
                bot_id=bot_id,
                channel=channel,
                session_id=session_id,
                sop_group=sop_group,
            )
        )
    )


@router.get("/profiles")
def list_profiles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = None,
    mode: str | None = None,
    service: RuntimePolicyProfileService = Depends(get_runtime_policy_service),
) -> dict[str, Any]:
    return success(service.list_profiles(page, page_size, status=status, mode=mode))


@router.post("/profiles")
def create_profile(
    request: RuntimePolicyProfileRequest,
    service: RuntimePolicyProfileService = Depends(get_runtime_policy_service),
) -> dict[str, Any]:
    return success(service.create_profile(request))


@router.get("/profiles/{profile_id}")
def get_profile(
    profile_id: int,
    service: RuntimePolicyProfileService = Depends(get_runtime_policy_service),
) -> dict[str, Any]:
    return success(service.get_profile(profile_id))


@router.put("/profiles/{profile_id}")
def update_profile(
    profile_id: int,
    request: RuntimePolicyProfileRequest,
    service: RuntimePolicyProfileService = Depends(get_runtime_policy_service),
) -> dict[str, Any]:
    return success(service.update_profile(profile_id, request))


@router.delete("/profiles/{profile_id}")
def delete_profile(
    profile_id: int,
    service: RuntimePolicyProfileService = Depends(get_runtime_policy_service),
) -> dict[str, Any]:
    service.delete_profile(profile_id)
    return success(None)


@router.post("/profiles/{profile_id}/preview")
def preview_profile(
    profile_id: int,
    request: RuntimePolicyProfileRequest | None = None,
    service: RuntimePolicyProfileService = Depends(get_runtime_policy_service),
) -> dict[str, Any]:
    return success(service.preview_profile(profile_id, request))
