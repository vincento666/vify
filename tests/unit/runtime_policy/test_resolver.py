import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.core.database import Base
from app.modules.runtime_policy.domain.resolver import RuntimePolicyResolveContext, RuntimePolicyResolver
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository
from app.modules.runtime_policy.web.schemas import RuntimePolicyProfileRequest
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyResolverTest(unittest.TestCase):
    def test_resolver_prefers_specific_active_binding_and_masks_env_secret(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_engine(f"sqlite:///{Path(tmp_dir) / 'resolver.db'}", future=True)
            Base.metadata.create_all(bind=engine)
            factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
            with factory() as session:
                repository = RuntimePolicyRepository(session)
                global_payload = _profile_payload(name="global active")
                global_payload["status"] = "active"
                global_payload["bindings"] = {
                    **global_payload["bindings"],
                    "tenantId": "",
                    "botId": "",
                    "channel": "",
                    "sopGroup": "",
                }
                specific_payload = _profile_payload(name="specific active")
                specific_payload["status"] = "active"
                specific_payload["bindings"] = {
                    **specific_payload["bindings"],
                    "tenantId": "tenant-a",
                    "botId": "bot-a",
                    "channel": "web",
                    "sopGroup": "",
                }
                repository.create_profile(_values(global_payload))
                specific = repository.create_profile(_values(specific_payload))

                resolved = RuntimePolicyResolver(repository, Settings(_env_file=None)).resolve(
                    RuntimePolicyResolveContext(tenant_id="tenant-a", bot_id="bot-a", channel="web")
                )
            with factory() as session:
                empty_repository = RuntimePolicyRepository(session)
                for profile in empty_repository.list_active_profiles():
                    empty_repository.delete_profile(int(profile["id"]))
                fallback = RuntimePolicyResolver(
                    empty_repository,
                    Settings(
                        _env_file=None,
                        runtime_lab_intent_arbitrator_mode="llm",
                        runtime_lab_intent_arbitrator_api_key="sk-real",
                    ),
                ).resolve(RuntimePolicyResolveContext(tenant_id="other"))

        self.assertEqual(resolved["source"], "profile")
        self.assertEqual(resolved["profileId"], specific["id"])
        self.assertEqual(fallback["source"], "env")
        self.assertEqual(fallback["policySnapshot"]["classifier"]["apiKeyRef"], "env:HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_API_KEY")
        self.assertNotIn("sk-real", str(fallback))


def _values(payload: dict[str, object]) -> dict[str, object]:
    request = RuntimePolicyProfileRequest.model_validate(payload)
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


if __name__ == "__main__":
    unittest.main()
