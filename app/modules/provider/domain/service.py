import os
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.provider.domain.connection import ProviderConnectionTester
from app.modules.provider.domain.model_connectivity import ProviderModelConnectivityTester
from app.modules.provider.infra.repository import ProviderRepository
from app.modules.provider.web.schemas import (
    ModelConfigResponse,
    ProviderCreateRequest,
    ProviderHealthResponse,
    ProviderPageResponse,
    ProviderResponse,
    ProviderUpdateRequest,
    format_datetime,
)


class ProviderService:
    def __init__(self, repository: ProviderRepository) -> None:
        self._repository = repository

    def create(self, request: ProviderCreateRequest) -> dict[str, Any]:
        row = self._repository.create(
            {
                "name": request.name,
                "type": request.type,
                "base_url": request.base_url,
                "description": request.description,
                "auth_config": request.auth_config,
            }
        )
        return self._to_response(row).model_dump(by_alias=True)

    def list(
        self,
        page: int,
        page_size: int,
        provider_type: str | None,
        enabled: bool | None,
    ) -> dict[str, Any]:
        rows, total = self._repository.list_page(page, page_size, provider_type, enabled)
        response = ProviderPageResponse(
            list=[self._to_response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def get(self, provider_id: int) -> dict[str, Any]:
        row = self._repository.get(provider_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Provider not found")
        return self._to_response(row).model_dump(by_alias=True)

    def update(self, provider_id: int, request: ProviderUpdateRequest) -> dict[str, Any]:
        values = request.model_dump(exclude_unset=True, by_alias=False)
        row = self._repository.update(provider_id, values)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Provider not found")
        return self._to_response(row).model_dump(by_alias=True)

    def delete(self, provider_id: int) -> None:
        deleted = self._repository.delete(provider_id)
        if not deleted:
            raise BizError(ErrorCode.NOT_FOUND, "Provider not found")

    def test_connection(self, provider_id: int) -> dict[str, Any]:
        row = self._repository.get(provider_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Provider not found")
        result = ProviderConnectionTester().test(
            provider_type=str(row["type"]),
            base_url=str(row["base_url"]),
            auth_config=dict(row["auth_config"] or {}),
        )
        return result.to_response()

    def test_model_connectivity(self, provider_id: int, model_config_id: int) -> dict[str, Any]:
        row = self._repository.get_enabled_provider_model_config(provider_id, model_config_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Model config not found")
        return ProviderModelConnectivityTester().test(row).to_response()

    def _to_response(self, row: dict[str, Any]) -> ProviderResponse:
        models = [
            ModelConfigResponse(
                id=item["id"],
                name=item["name"],
                modelId=item["model_id"],
                enabled=bool(item["enabled"]),
            )
            for item in self._repository.list_models(int(row["id"]))
        ]
        health_row = self._repository.get_health(int(row["id"]))
        health = None
        if health_row:
            health = ProviderHealthResponse(
                status=health_row["status"],
                lastCheckAt=format_datetime(health_row["last_check_at"])
                if health_row["last_check_at"]
                else None,
                latencyMs=health_row["latency_ms"],
                errorMessage=health_row["error_message"],
            )
        return ProviderResponse(
            id=int(row["id"]),
            name=str(row["name"]),
            type=row["type"],
            baseUrl=str(row["base_url"]),
            description=str(row["description"] or ""),
            enabled=bool(row["enabled"]),
            authConfigured=_has_usable_api_key(row["auth_config"]),
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
            models=models,
            health=health,
        )


def _has_usable_api_key(auth_config: Any) -> bool:
    if not isinstance(auth_config, dict):
        return False
    direct = str(auth_config.get("api_key") or auth_config.get("apiKey") or "").strip()
    if direct:
        return True
    ref = str(auth_config.get("api_key_ref") or auth_config.get("apiKeyRef") or "").strip()
    if not ref.startswith("env:"):
        return False
    return bool(os.getenv(ref.removeprefix("env:"), "").strip())
