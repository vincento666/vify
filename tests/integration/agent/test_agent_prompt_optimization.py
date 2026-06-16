from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentPromptOptimizationContractTest(unittest.TestCase):
    def test_prompt_optimization_uses_agent_model_and_records_audit(self) -> None:
        model_id = _seed_model()
        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Agent Prompt Optimization {time.time_ns()}",
                    "systemPrompt": "你是客服。",
                    "modelConfigId": model_id,
                    "temperature": 0.2,
                    "maxTokens": 512,
                    "maxContextTurns": 4,
                    "toolIds": [],
                },
            )
            self.assertEqual(create_response.status_code, 200)
            agent = create_response.json()["data"]

            optimize_response = client.post(
                f"/api/v1/agents/{agent['id']}/prompt-optimizations",
                json={"instruction": "让角色约束更清晰，并保持中文。"},
            )
            self.assertEqual(optimize_response.status_code, 200)
            proposal = optimize_response.json()["data"]
            self.assertEqual(proposal["agentId"], agent["id"])
            self.assertEqual(proposal["originalPrompt"], "你是客服。")
            self.assertIn("Improve this Agent system prompt", proposal["optimizedPrompt"])
            self.assertEqual(proposal["audit"]["modelConfigId"], model_id)
            self.assertGreater(proposal["audit"]["tokenEstimate"], 0)

            list_response = client.get(f"/api/v1/agents/{agent['id']}/prompt-optimizations")
            self.assertEqual(list_response.status_code, 200)
            records = list_response.json()["data"]["list"]
            self.assertTrue(records)
            self.assertEqual(records[0]["id"], proposal["id"])
            self.assertEqual(records[0]["instruction"], "让角色约束更清晰，并保持中文。")


if __name__ == "__main__":
    unittest.main()


def _seed_model() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Agent Prompt Provider {time.time_ns()}",
                type="OPENAI",
                base_url="mock://success",
                auth_config={"api_key": "sk-test"},
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        model_id = session.execute(
            model_config.insert().values(
                provider_id=provider_id,
                name="Agent Prompt Model",
                model_id="agent-prompt-model",
                context_size=4096,
                extra_params={},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(model_id)
