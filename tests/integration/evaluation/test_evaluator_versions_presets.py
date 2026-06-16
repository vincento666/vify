import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class EvaluatorVersionsPresetsTest(unittest.TestCase):
    def test_evaluator_versions_are_immutable_and_presets_are_listed(self) -> None:
        with TestClient(app) as client:
            evaluator = client.post(
                "/api/v1/evaluators",
                json={
                    "name": f"Versioned Evaluator {time.time_ns()}",
                    "type": "CONTAINS_KEYWORDS",
                    "config": {"keywords": ["refund"], "matchMode": "all", "ignoreCase": True},
                },
            ).json()["data"]
            version = client.post(
                f"/api/v1/evaluators/{evaluator['id']}/versions",
                json={"description": "stable evaluator"},
            ).json()["data"]
            client.put(
                f"/api/v1/evaluators/{evaluator['id']}",
                json={
                    "name": evaluator["name"],
                    "type": "EXACT_MATCH",
                    "config": {"ignoreCase": False},
                    "enabled": 1,
                },
            )
            versions = client.get(f"/api/v1/evaluators/{evaluator['id']}/versions")
            presets = client.get("/api/v1/evaluators/presets")

        self.assertEqual(version["version"], "0.0.1")
        self.assertEqual(version["evaluatorId"], evaluator["id"])
        self.assertEqual(version["evaluatorType"], "CONTAINS_KEYWORDS")
        self.assertEqual(version["configSnapshot"]["keywords"], ["refund"])
        self.assertEqual(versions.status_code, 200, versions.text)
        listed = versions.json()["data"]["list"]
        self.assertEqual(listed[0]["configSnapshot"]["keywords"], ["refund"])
        self.assertEqual(presets.status_code, 200, presets.text)
        preset_keys = [item["key"] for item in presets.json()["data"]["list"]]
        self.assertEqual(preset_keys, ["EXACT_MATCH", "CONTAINS_KEYWORDS", "LLM_JUDGE", "CODE_EVALUATOR"])
        self.assertFalse(presets.json()["data"]["list"][-1]["enabled"])

    def test_experiment_binds_evaluator_versions_and_runs_against_snapshot(self) -> None:
        with TestClient(app) as client:
            workflow = client.post(
                "/api/v1/workflows",
                json={
                    "name": f"Evaluator Version Workflow {time.time_ns()}",
                    "description": "version binding target",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {"outputVariables": ["userMessage"]}},
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"output": "{{start.userMessage}}", "outputVariable": "output"}},
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            ).json()["data"]
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Evaluator Version Set {time.time_ns()}", "description": "version binding"},
            ).json()["data"]
            client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={"input": "refund policy", "expectedOutput": "refund policy", "tags": ["version"]},
            )
            evaluator = client.post(
                "/api/v1/evaluators",
                json={
                    "name": f"Evaluator Version Binding {time.time_ns()}",
                    "type": "CONTAINS_KEYWORDS",
                    "config": {"keywords": ["refund"], "matchMode": "all", "ignoreCase": True},
                },
            ).json()["data"]
            version = client.post(
                f"/api/v1/evaluators/{evaluator['id']}/versions",
                json={"description": "stable refund keyword"},
            ).json()["data"]
            client.put(
                f"/api/v1/evaluators/{evaluator['id']}",
                json={
                    "name": evaluator["name"],
                    "type": "CONTAINS_KEYWORDS",
                    "config": {"keywords": ["never-match"], "matchMode": "all", "ignoreCase": True},
                    "enabled": 1,
                },
            )

            create_response = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"Evaluator Version Experiment {time.time_ns()}",
                    "targetType": "WORKFLOW",
                    "targetId": workflow["id"],
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [evaluator["id"]],
                    "evaluatorVersionIds": [version["id"]],
                },
            )
            experiment = create_response.json()["data"]
            run_response = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs")

        self.assertEqual(create_response.status_code, 200, create_response.text)
        self.assertEqual(experiment["evaluatorVersionIds"], [version["id"]])
        self.assertEqual(run_response.status_code, 200, run_response.text)
        run = run_response.json()["data"]
        self.assertEqual(run["passedCases"], 1)
        self.assertEqual(run["caseResults"][0]["evaluatorResults"][0]["evaluatorVersionId"], version["id"])
        self.assertEqual(run["caseResults"][0]["evaluatorResults"][0]["version"], "0.0.1")

    def test_experiment_rejects_evaluator_version_from_unselected_evaluator(self) -> None:
        with TestClient(app) as client:
            workflow = client.post(
                "/api/v1/workflows",
                json={
                    "name": f"Evaluator Version Reject Workflow {time.time_ns()}",
                    "description": "version binding target",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "output"}},
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            ).json()["data"]
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Evaluator Version Reject Set {time.time_ns()}", "description": "version binding"},
            ).json()["data"]
            selected = client.post(
                "/api/v1/evaluators",
                json={"name": f"Selected Evaluator {time.time_ns()}", "type": "EXACT_MATCH", "config": {}},
            ).json()["data"]
            other = client.post(
                "/api/v1/evaluators",
                json={"name": f"Other Evaluator {time.time_ns()}", "type": "EXACT_MATCH", "config": {}},
            ).json()["data"]
            other_version = client.post(f"/api/v1/evaluators/{other['id']}/versions", json={}).json()["data"]

            response = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"Evaluator Version Reject Experiment {time.time_ns()}",
                    "targetType": "WORKFLOW",
                    "targetId": workflow["id"],
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [selected["id"]],
                    "evaluatorVersionIds": [other_version["id"]],
                },
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("Evaluator version", response.json()["message"])


if __name__ == "__main__":
    unittest.main()
