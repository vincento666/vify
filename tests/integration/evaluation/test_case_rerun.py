from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class EvaluationCaseRerunTest(unittest.TestCase):
    def test_reruns_selected_case_into_single_case_run(self) -> None:
        agent_id = _seed_mock_agent()

        with TestClient(app) as client:
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Rerun Set {time.time_ns()}", "description": "selected case rerun"},
            ).json()["data"]
            client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={"input": "refund only", "expectedOutput": "refund policy", "tags": ["rerun"]},
            )
            evaluator = client.post(
                "/api/v1/evaluators",
                json={
                    "name": f"Rerun Keywords {time.time_ns()}",
                    "type": "CONTAINS_KEYWORDS",
                    "config": {"keywords": ["policy"], "matchMode": "all", "ignoreCase": True},
                },
            ).json()["data"]
            experiment = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"Rerun Experiment {time.time_ns()}",
                    "targetType": "AGENT",
                    "targetId": agent_id,
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [evaluator["id"]],
                },
            ).json()["data"]
            original_run = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs").json()["data"]
            self.assertEqual(original_run["failedCases"], 1)
            failed_case = original_run["caseResults"][0]

            client.put(
                f"/api/v1/evaluators/{evaluator['id']}",
                json={
                    "name": evaluator["name"],
                    "type": "CONTAINS_KEYWORDS",
                    "config": {"keywords": ["refund"], "matchMode": "all", "ignoreCase": True},
                },
            )
            rerun_response = client.post(
                f"/api/v1/evaluation-runs/{original_run['id']}/case-results/{failed_case['id']}/rerun"
            )

            self.assertEqual(rerun_response.status_code, 200, rerun_response.text)
            rerun = rerun_response.json()["data"]
            self.assertNotEqual(rerun["id"], original_run["id"])
            self.assertEqual(rerun["experimentId"], experiment["id"])
            self.assertEqual(rerun["totalCases"], 1)
            self.assertEqual(rerun["passedCases"], 1)
            self.assertEqual(rerun["failedCases"], 0)
            self.assertEqual(rerun["caseResults"][0]["evalCaseId"], failed_case["evalCaseId"])

            unchanged_original = client.get(f"/api/v1/evaluation-runs/{original_run['id']}").json()["data"]
            self.assertEqual(unchanged_original["failedCases"], 1)


def _seed_mock_agent() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Rerun Provider {time.time_ns()}",
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
                name="Rerun Mock Model",
                model_id="mock-rerun-model",
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
                name=f"Rerun Agent {time.time_ns()}",
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
