from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class EvalSetRelatedExperimentsTest(unittest.TestCase):
    def test_eval_set_related_experiments_show_version_usage(self) -> None:
        agent_id = _seed_agent()

        with TestClient(app) as client:
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Related Set {time.time_ns()}", "description": "related experiments"},
            ).json()["data"]
            client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={"input": "hello", "expectedOutput": "LLM mock: hello", "tags": [], "metadata": {}},
            )
            version = client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/versions",
                json={"description": "stable related version"},
            ).json()["data"]
            evaluator = client.post(
                "/api/v1/evaluators",
                json={"name": f"Related Exact {time.time_ns()}", "type": "EXACT_MATCH", "config": {}},
            ).json()["data"]
            experiment = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"Related Experiment {time.time_ns()}",
                    "targetType": "AGENT",
                    "targetId": agent_id,
                    "evalSetId": eval_set["id"],
                    "evalSetVersionId": version["id"],
                    "evaluatorIds": [evaluator["id"]],
                },
            ).json()["data"]

            response = client.get(f"/api/v1/eval-sets/{eval_set['id']}/related-experiments")

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()["data"]
        self.assertEqual(payload["total"], 1)
        related = payload["list"][0]
        self.assertEqual(related["id"], experiment["id"])
        self.assertEqual(related["name"], experiment["name"])
        self.assertEqual(related["evalSetId"], eval_set["id"])
        self.assertEqual(related["evalSetVersionId"], version["id"])
        self.assertEqual(related["evalSetVersion"], "0.0.1")
        self.assertEqual(related["targetType"], "AGENT")
        self.assertEqual(related["status"], "READY")
        self.assertIsNone(related["latestRunId"])


def _seed_agent() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Related Provider {time.time_ns()}",
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
                name="Related Mock Model",
                model_id="related-mock-model",
                context_size=4096,
                extra_params={},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        agent_id = session.execute(
            agent.insert().values(
                name=f"Related Agent {time.time_ns()}",
                description="",
                system_prompt="",
                model_config_id=model_id,
                temperature=0.0,
                max_tokens=512,
                max_context_turns=2,
                enabled=True,
                knowledge_base_id=None,
                workflow_id=None,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(agent_id)


if __name__ == "__main__":
    unittest.main()
