from app.core.database import get_session_factory
from app.modules.provider.domain.connection import ProviderConnectionTester
from app.modules.provider.infra.repository import ProviderRepository


class ProviderHealthChecker:
    def check_once(self) -> int:
        checked = 0
        with get_session_factory()() as session:
            repository = ProviderRepository(session)
            tester = ProviderConnectionTester()
            for provider in repository.list_enabled_providers():
                result = tester.test(
                    provider_type=str(provider["type"]),
                    base_url=str(provider["base_url"]),
                    auth_config=dict(provider["auth_config"] or {}),
                )
                repository.upsert_health(int(provider["id"]), result)
                checked += 1
        return checked
