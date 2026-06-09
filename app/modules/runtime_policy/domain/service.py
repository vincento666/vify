from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository
from app.modules.runtime_policy.web.schemas import RuntimePolicyProfileRequest, RuntimePolicyProfileResponse


class RuntimePolicyProfileService:
    def __init__(self, repository: RuntimePolicyRepository) -> None:
        self._repository = repository

    def create_profile(self, request: RuntimePolicyProfileRequest) -> dict[str, Any]:
        row = self._repository.create_profile(_profile_values(request))
        return _profile_response(row)

    def list_profiles(
        self,
        page: int,
        page_size: int,
        *,
        status: str | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        rows, total = self._repository.list_profiles(page, page_size, status=status, mode=mode)
        return {
            "list": [_profile_response(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }

    def get_profile(self, profile_id: int) -> dict[str, Any]:
        row = self._repository.get_profile(profile_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        return _profile_response(row)

    def update_profile(self, profile_id: int, request: RuntimePolicyProfileRequest) -> dict[str, Any]:
        row = self._repository.update_profile(profile_id, _profile_values(request))
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        return _profile_response(row)

    def delete_profile(self, profile_id: int) -> None:
        if not self._repository.delete_profile(profile_id):
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")

    def preview_profile(self, profile_id: int, request: RuntimePolicyProfileRequest | None = None) -> dict[str, Any]:
        profile = self.get_profile(profile_id)
        if request is not None:
            profile = {
                **profile,
                **RuntimePolicyProfileResponse(
                    id=profile_id,
                    version=int(profile["version"]),
                    createdAt=profile["createdAt"],
                    updatedAt=profile["updatedAt"],
                    **_profile_values(request),
                ).model_dump(by_alias=True),
            }
        return {
            "profileId": profile_id,
            "profileVersion": profile["version"],
            "policySnapshot": _policy_snapshot(profile),
        }


def _profile_values(request: RuntimePolicyProfileRequest) -> dict[str, Any]:
    return {
        "name": request.name,
        "description": request.description,
        "status": request.status,
        "mode": request.mode,
        "bindings": request.bindings.model_dump(mode="json", by_alias=True),
        "thresholds": request.thresholds.model_dump(mode="json", by_alias=True),
        "classifier": request.classifier.model_dump(mode="json", by_alias=True),
        "faq": request.faq.model_dump(mode="json", by_alias=True),
        "rag": request.rag.model_dump(mode="json", by_alias=True),
        "fallback_agent": request.fallback_agent.model_dump(mode="json", by_alias=True),
        "handoff": request.handoff.model_dump(mode="json", by_alias=True),
        "audit": request.audit.model_dump(mode="json", by_alias=True),
    }


def _profile_response(row: dict[str, Any]) -> dict[str, Any]:
    response = RuntimePolicyProfileResponse(
        id=int(row["id"]),
        version=int(row["version"]),
        name=str(row["name"]),
        description=str(row.get("description") or ""),
        status=str(row["status"]),
        mode=str(row["mode"]),
        bindings=row["bindings"],
        thresholds=row["thresholds"],
        classifier=row["classifier"],
        faq=row["faq"],
        rag=row["rag"],
        fallbackAgent=row["fallback_agent"],
        handoff=row["handoff"],
        audit=row["audit"],
        createdAt=row["created_at"].isoformat(),
        updatedAt=row["updated_at"].isoformat(),
    )
    return response.model_dump(by_alias=True)


def _policy_snapshot(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "profileId": profile["id"],
        "profileVersion": profile["version"],
        "status": profile["status"],
        "mode": profile["mode"],
        "bindings": profile["bindings"],
        "thresholds": profile["thresholds"],
        "classifier": profile["classifier"],
        "faq": profile["faq"],
        "rag": profile["rag"],
        "fallbackAgent": profile["fallbackAgent"],
        "handoff": profile["handoff"],
    }
