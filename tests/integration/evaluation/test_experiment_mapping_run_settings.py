import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ExperimentMappingRunSettingsTest(unittest.TestCase):
    def test_experiment_run_uses_mapped_dataset_fields_and_persists_run_settings(self) -> None:
        with TestClient(app) as client:
            workflow = client.post(
                "/api/v1/workflows",
                json={
                    "name": f"Mapping Workflow {time.time_ns()}",
                    "description": "",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {"outputVariables": ["userMessage"]}},
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"output": "{{start.userMessage}}", "outputVariable": "output"}},
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            ).json()["data"]
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Mapping Set {time.time_ns()}", "description": "mapping"},
            ).json()["data"]
            client.put(
                f"/api/v1/eval-sets/{eval_set['id']}/fields",
                json={
                    "fields": [
                        {"key": "input", "label": "Input", "contentType": "TEXT", "required": True, "displayOrder": 1},
                        {"key": "expectedOutput", "label": "Expected", "contentType": "TEXT", "required": True, "displayOrder": 2},
                        {"key": "prompt", "label": "Prompt", "contentType": "TEXT", "required": True, "displayOrder": 3},
                        {"key": "reference", "label": "Reference", "contentType": "TEXT", "required": True, "displayOrder": 4},
                    ]
                },
            )
            client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={
                    "input": "wrong input",
                    "expectedOutput": "wrong expected",
                    "tags": ["mapping"],
                    "metadata": {"prompt": "mapped prompt", "reference": "mapped prompt"},
                },
            )
            evaluator = client.post(
                "/api/v1/evaluators",
                json={"name": f"Mapping Exact {time.time_ns()}", "type": "EXACT_MATCH", "config": {}},
            ).json()["data"]

            create_response = client.post(
                "/api/v1/evaluation-experiments",
                json={
                    "name": f"Mapping Experiment {time.time_ns()}",
                    "targetType": "WORKFLOW",
                    "targetId": workflow["id"],
                    "evalSetId": eval_set["id"],
                    "evaluatorIds": [evaluator["id"]],
                    "targetFieldMapping": {"userMessage": "prompt"},
                    "evaluatorFieldMapping": {"expectedOutput": "reference", "actualOutput": "__target.output"},
                    "itemConcurrency": 3,
                    "itemRetryCount": 2,
                },
            )
            experiment = create_response.json()["data"]
            run_response = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs")

        self.assertEqual(create_response.status_code, 200, create_response.text)
        self.assertEqual(experiment["targetFieldMapping"], {"userMessage": "prompt"})
        self.assertEqual(experiment["evaluatorFieldMapping"]["expectedOutput"], "reference")
        self.assertEqual(experiment["itemConcurrency"], 3)
        self.assertEqual(experiment["itemRetryCount"], 2)
        self.assertEqual(run_response.status_code, 200, run_response.text)
        run = run_response.json()["data"]
        self.assertEqual(run["passedCases"], 1)
        self.assertEqual(run["caseResults"][0]["input"], "mapped prompt")
        self.assertEqual(run["caseResults"][0]["expectedOutput"], "mapped prompt")
        self.assertEqual(run["caseResults"][0]["targetOutput"], "mapped prompt")


if __name__ == "__main__":
    unittest.main()
