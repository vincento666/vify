from datetime import datetime
import unittest
import time

from app.core.database import Base, get_session_factory, initialise_database
from app.core.errors import BizError
from app.core.schema import register_baseline_tables
from app.modules.provider.api.facade import ProviderModelFacade


class ModelConfigLookupTest(unittest.TestCase):
    def test_only_enabled_model_configs_are_returned(self) -> None:
        initialise_database()
        register_baseline_tables()
        provider = Base.metadata.tables["provider"]
        model_config = Base.metadata.tables["model_config"]
        now = datetime.now()

        with get_session_factory()() as session:
            provider_id = session.execute(
                provider.insert().values(
                    name=f"Model Lookup Provider {time.time_ns()}",
                    type="OPENAI",
                    base_url="https://api.example.com/v1",
                    auth_config={"api_key": "sk-test"},
                    description="",
                    enabled=True,
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                )
            ).inserted_primary_key[0]
            enabled_model_id = session.execute(
                model_config.insert().values(
                    provider_id=provider_id,
                    name="GPT-4o",
                    model_id="gpt-4o",
                    context_size=128000,
                    extra_params={"temperature": 0.7},
                    enabled=True,
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                )
            ).inserted_primary_key[0]
            disabled_model_id = session.execute(
                model_config.insert().values(
                    provider_id=provider_id,
                    name="Disabled",
                    model_id="disabled-model",
                    context_size=4096,
                    extra_params={},
                    enabled=False,
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                )
            ).inserted_primary_key[0]
            session.commit()

        with get_session_factory()() as session:
            facade = ProviderModelFacade(session)

            enabled = facade.get_enabled_model_config(int(enabled_model_id))
            self.assertEqual(enabled.model_id, "gpt-4o")
            self.assertEqual(enabled.provider_type, "OPENAI")

            with self.assertRaises(BizError):
                facade.get_enabled_model_config(int(disabled_model_id))


if __name__ == "__main__":
    unittest.main()
