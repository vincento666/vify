from datetime import datetime
import io
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class EvaluationCsvImportExportTest(unittest.TestCase):
    def test_import_eval_cases_from_csv_and_export_run_results(self) -> None:
        agent_id = _seed_mock_agent()

        with TestClient(app) as client:
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"CSV Set {time.time_ns()}", "description": "csv import"},
            ).json()["data"]
            csv_content = "input,expectedOutput,tags\nrefund policy,LLM mock: refund policy,refund|policy\nshipping status,LLM mock: shipping status,shipping\n"
            import_response = client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases/import-csv",
                files={"file": ("cases.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
            )
            self.assertEqual(import_response.status_code, 200)
            self.assertEqual(import_response.json()["data"]["createdCount"], 2)

            detail = client.get(f"/api/v1/eval-sets/{eval_set['id']}").json()["data"]
            self.assertEqual(detail["caseCount"], 2)
            self.assertEqual(detail["cases"][0]["tags"], ["refund", "policy"])

            evaluator = client.post(
                "/api/v1/evaluators",
                json={"name": f"CSV Exact {time.time_ns()}", "type": "EXACT_MATCH", "config": {"ignoreCase": False}},
            ).json()["data"]
            experiment = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"CSV Experiment {time.time_ns()}",
                    "targetType": "AGENT",
                    "targetId": agent_id,
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [evaluator["id"]],
                },
            ).json()["data"]
            run = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs").json()["data"]

            export_response = client.get(f"/api/v1/evaluation-runs/{run['id']}/export-csv")
            self.assertEqual(export_response.status_code, 200)
            self.assertIn("text/csv", export_response.headers["content-type"])
            self.assertIn("target_output", export_response.text)
            self.assertIn("LLM mock: refund policy", export_response.text)


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
                name=f"CSV Provider {time.time_ns()}",
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
                name="CSV Mock Model",
                model_id="mock-csv-model",
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
                name=f"CSV Agent {time.time_ns()}",
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
