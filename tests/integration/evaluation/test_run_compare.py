import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class EvaluationRunCompareTest(unittest.TestCase):
    def test_compares_two_runs_with_failed_recovered_and_unchanged_cases(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client)
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Compare Set {time.time_ns()}", "description": "run compare"},
            ).json()["data"]
            case_a = _create_case(client, eval_set["id"], "alpha", "LLM mock: Workflow says alpha")
            case_b = _create_case(client, eval_set["id"], "beta", "wrong beta")
            case_c = _create_case(client, eval_set["id"], "gamma", "wrong gamma")
            case_d = _create_case(client, eval_set["id"], "delta", "wrong delta")
            evaluator = client.post(
                "/api/v1/evaluators",
                json={"name": f"Compare Exact {time.time_ns()}", "type": "EXACT_MATCH", "config": {}},
            ).json()["data"]
            experiment = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"Compare Experiment {time.time_ns()}",
                    "targetType": "WORKFLOW",
                    "targetId": workflow["id"],
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [evaluator["id"]],
                },
            ).json()["data"]
            base_run = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs").json()["data"]
            self.assertEqual(base_run["passedCases"], 1)
            self.assertEqual(base_run["failedCases"], 3)

            _update_case(client, case_a["id"], "alpha", "wrong alpha")
            _update_case(client, case_b["id"], "beta", "LLM mock: Workflow says beta")
            _update_case(client, case_c["id"], "gamma", "wrong gamma")
            _update_case(client, case_d["id"], "delta", "LLM mock: Workflow says delta")
            candidate_run = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs").json()["data"]
            self.assertEqual(candidate_run["passedCases"], 2)
            self.assertEqual(candidate_run["failedCases"], 2)

            compare_response = client.get(
                "/api/v1/evaluation-runs/compare",
                params={"baseRunId": base_run["id"], "candidateRunId": candidate_run["id"]},
            )

            self.assertEqual(compare_response.status_code, 200, compare_response.text)
            compare = compare_response.json()["data"]
            self.assertEqual(compare["baseRunId"], base_run["id"])
            self.assertEqual(compare["candidateRunId"], candidate_run["id"])
            self.assertEqual(compare["baseScore"], 0.25)
            self.assertEqual(compare["candidateScore"], 0.5)
            self.assertEqual(compare["scoreDelta"], 0.25)
            self.assertEqual(compare["passRateDelta"], 0.25)
            self.assertEqual([item["evalCaseId"] for item in compare["newlyFailedCases"]], [case_a["id"]])
            self.assertEqual(
                [item["evalCaseId"] for item in compare["recoveredCases"]],
                [case_b["id"], case_d["id"]],
            )
            self.assertEqual([item["evalCaseId"] for item in compare["unchangedFailures"]], [case_c["id"]])

            missing_response = client.get(
                "/api/v1/evaluation-runs/compare",
                params={"baseRunId": 999999999, "candidateRunId": candidate_run["id"]},
            )
            self.assertEqual(missing_response.status_code, 404)


def _create_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Compare Workflow {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "LLM",
                    "config": {
                        "prompt": "Workflow says {{start.userMessage}}",
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


def _create_case(client: TestClient, eval_set_id: int, input_text: str, expected_output: str) -> dict[str, object]:
    return client.post(
        f"/api/v1/eval-sets/{eval_set_id}/cases",
        json={"input": input_text, "expectedOutput": expected_output, "tags": ["compare"]},
    ).json()["data"]


def _update_case(client: TestClient, case_id: int, input_text: str, expected_output: str) -> None:
    response = client.put(
        f"/api/v1/eval-cases/{case_id}",
        json={"input": input_text, "expectedOutput": expected_output, "tags": ["compare"]},
    )
    assert response.status_code == 200, response.text


if __name__ == "__main__":
    unittest.main()
