from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.provider.domain.service import ProviderService
from app.modules.provider.infra.repository import ProviderRepository
from app.modules.provider.web.schemas import ProviderCreateRequest, ProviderUpdateRequest

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


def get_provider_service(session: Session = Depends(get_session)) -> ProviderService:
    return ProviderService(ProviderRepository(session))


@router.post("")
def create_provider(
    request: ProviderCreateRequest,
    service: ProviderService = Depends(get_provider_service),
) -> dict[str, Any]:
    return success(service.create(request))


@router.get("")
def list_providers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    provider_type: str | None = Query(None, alias="type"),
    enabled: bool | None = None,
    service: ProviderService = Depends(get_provider_service),
) -> dict[str, Any]:
    return success(service.list(page, page_size, provider_type, enabled))


@router.get("/{provider_id}")
def get_provider(
    provider_id: int,
    service: ProviderService = Depends(get_provider_service),
) -> dict[str, Any]:
    return success(service.get(provider_id))


@router.put("/{provider_id}")
def update_provider(
    provider_id: int,
    request: ProviderUpdateRequest,
    service: ProviderService = Depends(get_provider_service),
) -> dict[str, Any]:
    return success(service.update(provider_id, request))


@router.delete("/{provider_id}")
def delete_provider(
    provider_id: int,
    service: ProviderService = Depends(get_provider_service),
) -> dict[str, Any]:
    service.delete(provider_id)
    return success(None)


@router.post("/{provider_id}/test-connection")
def test_provider_connection(
    provider_id: int,
    service: ProviderService = Depends(get_provider_service),
) -> dict[str, Any]:
    return success(service.test_connection(provider_id))


@router.post("/{provider_id}/models/{model_config_id}/connectivity")
def test_provider_model_connectivity(
    provider_id: int,
    model_config_id: int,
    service: ProviderService = Depends(get_provider_service),
) -> dict[str, Any]:
    return success(service.test_model_connectivity(provider_id, model_config_id))
