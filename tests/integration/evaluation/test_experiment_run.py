from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class EvaluationExperimentRunTest(unittest.TestCase):
    def test_create_agent_experiment_and_run_cases_synchronously(self) -> None:
        agent_id = _seed_mock_agent()

        with TestClient(app) as client:
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Experiment Set {time.time_ns()}", "description": "agent run cases"},
            ).json()["data"]
            case_response = client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={
                    "input": "refund policy",
                    "expectedOutput": "LLM mock: refund policy",
                    "tags": ["agent"],
                },
            )
            self.assertEqual(case_response.status_code, 200)
            evaluator = client.post(
                "/api/v1/evaluators",
                json={"name": f"Exact {time.time_ns()}", "type": "EXACT_MATCH", "config": {"ignoreCase": False}},
            ).json()["data"]

            create_experiment = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"Agent Experiment {time.time_ns()}",
                    "targetType": "AGENT",
                    "targetId": agent_id,
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [evaluator["id"]],
                },
            )
            self.assertEqual(create_experiment.status_code, 200)
            experiment = create_experiment.json()["data"]
            self.assertEqual(experiment["targetType"], "AGENT")

            run_response = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs")
            self.assertEqual(run_response.status_code, 200)
            run = run_response.json()["data"]
            self.assertEqual(run["status"], "COMPLETED")
            self.assertEqual(run["totalCases"], 1)
            self.assertEqual(run["passedCases"], 1)
            self.assertEqual(run["failedCases"], 0)
            self.assertEqual(run["aggregateScore"], 1.0)
            self.assertEqual(run["caseResults"][0]["targetOutput"], "LLM mock: refund policy")

    def test_create_workflow_experiment_and_run_cases_synchronously(self) -> None:
        with TestClient(app) as client:
            workflow = _create_flow(client, "/api/v1/workflows", "Workflow target")
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Workflow Eval Set {time.time_ns()}", "description": "workflow target"},
            ).json()["data"]
            client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={
                    "input": "refund policy",
                    "expectedOutput": "LLM mock: Workflow says refund policy",
                    "tags": ["workflow"],
                },
            )
            evaluator = client.post(
                "/api/v1/evaluators",
                json={"name": f"Workflow Exact {time.time_ns()}", "type": "EXACT_MATCH", "config": {}},
            ).json()["data"]

            create_experiment = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"Workflow Experiment {time.time_ns()}",
                    "targetType": "WORKFLOW",
                    "targetId": workflow["id"],
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [evaluator["id"]],
                },
            )
            self.assertEqual(create_experiment.status_code, 200, create_experiment.text)
            experiment = create_experiment.json()["data"]
            self.assertEqual(experiment["targetType"], "WORKFLOW")

            run_response = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs")
            self.assertEqual(run_response.status_code, 200, run_response.text)
            run = run_response.json()["data"]
            self.assertEqual(run["status"], "COMPLETED")
            self.assertEqual(run["passedCases"], 1)
            self.assertEqual(run["caseResults"][0]["targetOutput"], "LLM mock: Workflow says refund policy")

    def test_create_chatflow_experiment_and_run_cases_synchronously(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_flow(client, "/api/v1/chatflows", "Chatflow target")
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Chatflow Eval Set {time.time_ns()}", "description": "chatflow target"},
            ).json()["data"]
            client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={
                    "input": "shipping fee",
                    "expectedOutput": "LLM mock: Chatflow says shipping fee",
                    "tags": ["chatflow"],
                },
            )
            evaluator = client.post(
                "/api/v1/evaluators",
                json={"name": f"Chatflow Exact {time.time_ns()}", "type": "EXACT_MATCH", "config": {}},
            ).json()["data"]

            create_experiment = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"Chatflow Experiment {time.time_ns()}",
                    "targetType": "CHATFLOW",
                    "targetId": chatflow["id"],
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [evaluator["id"]],
                },
            )
            self.assertEqual(create_experiment.status_code, 200, create_experiment.text)
            experiment = create_experiment.json()["data"]
            self.assertEqual(experiment["targetType"], "CHATFLOW")

            run_response = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs")
            self.assertEqual(run_response.status_code, 200, run_response.text)
            run = run_response.json()["data"]
            self.assertEqual(run["status"], "COMPLETED")
            self.assertEqual(run["passedCases"], 1)
            self.assertEqual(run["caseResults"][0]["targetOutput"], "LLM mock: Chatflow says shipping fee")

    def test_rejects_unknown_target_and_missing_evaluator(self) -> None:
        with TestClient(app) as client:
            unknown_target_response = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": "Unknown target should fail",
                    "targetType": "BOT",
                    "targetId": 1,
                    "evalSetId": 1,
                    "evaluatorIds": [1],
                },
            )
            self.assertEqual(unknown_target_response.status_code, 422)

            missing_evaluator_response = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": "Missing evaluator",
                    "targetType": "AGENT",
                    "targetId": 999999999,
                    "evalSetId": 999999999,
                    "evaluatorIds": [999999999],
                },
            )
            self.assertEqual(missing_evaluator_response.status_code, 404)


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
                name=f"Experiment Provider {time.time_ns()}",
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
                name="Experiment Mock Model",
                model_id="mock-eval-model",
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
                name=f"Experiment Agent {time.time_ns()}",
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


def _create_flow(client: TestClient, url: str, name: str) -> dict[str, object]:
    prefix = "Workflow" if url.endswith("workflows") else "Chatflow"
    response = client.post(
        url,
        json={
            "name": f"{name} {time.time_ns()}",
            "description": "",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"outputVariables": ["userMessage"]},
                },
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "LLM",
                    "config": {
                        "prompt": f"{prefix} says {{{{start.userMessage}}}}",
                        "outputVariable": "answer",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"output": "{{llm.answer}}", "outputVariable": "output"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
