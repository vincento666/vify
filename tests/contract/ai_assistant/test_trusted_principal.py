from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.host.context import RequestContext
from app.core.host.dependencies import get_request_context


def test_trusted_identity_mode_rejects_unverified_identity_headers() -> None:
    principal_app = _principal_app()
    principal_app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        deployment_environment="production",
        host_identity_mode="trusted_state",
    )

    with TestClient(principal_app) as client:
        response = client.get(
            "/principal",
            headers={
                "X-Hify-Actor-Id": "spoofed-admin",
                "X-Hify-Tenant-Id": "spoofed-tenant",
                "X-Hify-Permissions": "admin:*",
            },
        )

    assert response.status_code == 401


def test_trusted_identity_mode_accepts_server_verified_request_state() -> None:
    principal_app = _principal_app(with_verified_principal=True)
    principal_app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        deployment_environment="production",
        host_identity_mode="trusted_state",
    )

    with TestClient(principal_app) as client:
        response = client.get(
            "/principal",
            headers={"X-Hify-Actor-Id": "spoofed-admin"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "actorId": "verified-user",
        "tenantId": "verified-tenant",
        "source": "trusted-auth-adapter",
    }


def _principal_app(*, with_verified_principal: bool = False) -> FastAPI:
    principal_app = FastAPI()

    if with_verified_principal:

        @principal_app.middleware("http")
        async def install_principal(request, call_next):
            request.state.hify_principal = RequestContext(
                actor_id="verified-user",
                actor_name="Verified User",
                tenant_id="verified-tenant",
                org_id="verified-org",
                roles=("operator",),
                permissions=("ai_assistant:operate",),
                source="trusted-auth-adapter",
            )
            return await call_next(request)

    @principal_app.get("/principal")
    def principal(
        context: RequestContext = Depends(get_request_context),
    ) -> dict[str, str]:
        return {
            "actorId": context.actor_id,
            "tenantId": context.tenant_id,
            "source": context.source,
        }

    return principal_app
