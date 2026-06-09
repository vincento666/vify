from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.runtime_policy.domain.service import RuntimePolicyProfileService
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository
from app.modules.runtime_policy.web.schemas import RuntimePolicyProfileRequest

router = APIRouter(prefix="/api/v1/runtime-policy", tags=["runtime-policy"])


def get_runtime_policy_service(session: Session = Depends(get_session)) -> RuntimePolicyProfileService:
    return RuntimePolicyProfileService(RuntimePolicyRepository(session))


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
