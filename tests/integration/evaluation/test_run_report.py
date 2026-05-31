from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class EvaluationRunReportTest(unittest.TestCase):
    def test_run_detail_filters_failed_cases_with_reasons_and_target_output(self) -> None:
        agent_id = _seed_mock_agent()

        with TestClient(app) as client:
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Report Set {time.time_ns()}", "description": "failed report cases"},
            ).json()["data"]
            client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={
                    "input": "refund only",
                    "expectedOutput": "refund policy",
                    "tags": ["failed-report"],
                },
            )
            evaluator = client.post(
                "/api/v1/evaluators",
                json={
                    "name": f"Report Keywords {time.time_ns()}",
                    "type": "CONTAINS_KEYWORDS",
                    "config": {"keywords": ["refund", "policy"], "matchMode": "all", "ignoreCase": True},
                },
            ).json()["data"]
            experiment = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"Report Experiment {time.time_ns()}",
                    "targetType": "AGENT",
                    "targetId": agent_id,
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [evaluator["id"]],
                },
            ).json()["data"]
            run = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs").json()["data"]

            detail_response = client.get(
                f"/api/v1/evaluation-runs/{run['id']}",
                params={"caseStatus": "FAILED"},
            )
            self.assertEqual(detail_response.status_code, 200)
            detail = detail_response.json()["data"]
            self.assertEqual(detail["failedCases"], 1)
            self.assertEqual(len(detail["caseResults"]), 1)
            failed_case = detail["caseResults"][0]
            self.assertEqual(failed_case["status"], "FAILED")
            self.assertEqual(failed_case["targetOutput"], "LLM mock: refund only")
            self.assertIn("policy", failed_case["reason"])
            self.assertEqual(failed_case["evaluatorResults"][0]["evaluatorId"], evaluator["id"])

            list_response = client.get("/api/v1/evaluation-runs", params={"page": 1, "pageSize": 20})
            self.assertEqual(list_response.status_code, 200)
            self.assertTrue(any(item["id"] == run["id"] for item in list_response.json()["data"]["list"]))

            missing_response = client.get("/api/v1/evaluation-runs/999999999")
            self.assertEqual(missing_response.status_code, 404)


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
                name=f"Report Provider {time.time_ns()}",
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
                name="Report Mock Model",
                model_id="mock-report-model",
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
                name=f"Report Agent {time.time_ns()}",
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
