import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class WorkflowGraphCrudTest(unittest.TestCase):
    def test_workflow_graph_round_trips_input_parameter_config(self) -> None:
        name = f"Workflow Input Params {time.time_ns()}"
        input_parameters = [
            {"name": "question", "type": "string", "valueMode": "reference", "value": "{{start.USER_INPUT}}"},
            {"name": "limit", "type": "number", "valueMode": "literal", "value": 3},
        ]

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/workflows",
                json={
                    "name": name,
                    "description": "input parameter contract",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {"outputVariables": ["USER_INPUT"]}},
                        {
                            "nodeKey": "llm",
                            "type": "LLM",
                            "name": "Answer",
                            "config": {"prompt": "Return", "inputParameters": input_parameters},
                        },
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
                    ],
                    "edges": [
                        {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                        {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
                    ],
                },
            )

            self.assertEqual(create_response.status_code, 200)
            workflow_id = create_response.json()["data"]["id"]
            detail_response = client.get(f"/api/v1/workflows/{workflow_id}")

        self.assertEqual(detail_response.status_code, 200)
        nodes = detail_response.json()["data"]["nodes"]
        llm_config = next(node for node in nodes if node["nodeKey"] == "llm")["config"]
        self.assertEqual(llm_config["inputParameters"], input_parameters)

    def test_workflow_graph_round_trips_variable_picker_templates(self) -> None:
        name = f"Workflow Variable Picker {time.time_ns()}"
        output_template = "{{llm_1.answer}} {{global.brand}}"

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/workflows",
                json={
                    "name": name,
                    "description": "variable picker contract",
                    "nodes": [
                        {
                            "nodeKey": "start",
                            "type": "START",
                            "name": "Start",
                            "config": {"outputVariables": ["USER_INPUT"]},
                        },
                        {
                            "nodeKey": "llm_1",
                            "type": "LLM",
                            "name": "Answer",
                            "config": {
                                "prompt": "Return {{start.USER_INPUT}}",
                                "outputParameters": [{"name": "answer", "type": "string"}],
                                "outputVariable": "answer",
                            },
                        },
                        {
                            "nodeKey": "end",
                            "type": "END",
                            "name": "End",
                            "config": {"outputVariable": "output", "output": output_template},
                        },
                    ],
                    "edges": [
                        {"sourceNodeKey": "start", "targetNodeKey": "llm_1", "condition": None},
                        {"sourceNodeKey": "llm_1", "targetNodeKey": "end", "condition": None},
                    ],
                },
            )

            self.assertEqual(create_response.status_code, 200)
            workflow_id = create_response.json()["data"]["id"]
            detail_response = client.get(f"/api/v1/workflows/{workflow_id}")

        self.assertEqual(detail_response.status_code, 200)
        nodes = detail_response.json()["data"]["nodes"]
        end_config = next(node for node in nodes if node["nodeKey"] == "end")["config"]
        self.assertEqual(end_config["output"], output_template)

    def test_workflow_graph_round_trips_output_parameter_config(self) -> None:
        name = f"Workflow Output Params {time.time_ns()}"
        output_config = {
            "prompt": "Return answer",
            "outputFormat": "Markdown",
            "outputParameters": [
                {"name": "answer", "type": "string"},
                {"name": "reasoning", "type": "object"},
            ],
            "outputVariable": "answer",
        }

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/workflows",
                json={
                    "name": name,
                    "description": "output parameter contract",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {"nodeKey": "llm", "type": "LLM", "name": "Answer", "config": output_config},
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
                    ],
                    "edges": [
                        {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                        {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
                    ],
                },
            )

            self.assertEqual(create_response.status_code, 200)
            workflow_id = create_response.json()["data"]["id"]
            detail_response = client.get(f"/api/v1/workflows/{workflow_id}")

        self.assertEqual(detail_response.status_code, 200)
        nodes = detail_response.json()["data"]["nodes"]
        llm_config = next(node for node in nodes if node["nodeKey"] == "llm")["config"]
        self.assertEqual(llm_config["outputFormat"], "Markdown")
        self.assertEqual(llm_config["outputParameters"], output_config["outputParameters"])

    def test_create_detail_update_and_delete_workflow_graph(self) -> None:
        name = f"Workflow CRUD {time.time_ns()}"

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/workflows",
                json={
                    "name": name,
                    "description": "created from test",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
                    ],
                    "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
                },
            )

            self.assertEqual(create_response.status_code, 200)
            created = create_response.json()["data"]
            self.assertEqual(created["name"], name)
            self.assertEqual(created["status"], "DRAFT")
            self.assertEqual([node["nodeKey"] for node in created["nodes"]], ["start", "end"])
            self.assertEqual(created["edges"][0]["targetNodeKey"], "end")

            list_response = client.get("/api/v1/workflows", params={"page": 1, "pageSize": 20})
            self.assertTrue(any(item["id"] == created["id"] for item in list_response.json()["data"]["list"]))

            detail_response = client.get(f"/api/v1/workflows/{created['id']}")
            self.assertEqual(detail_response.status_code, 200)
            self.assertEqual(detail_response.json()["data"]["nodes"][1]["config"]["outputVariable"], "answer")

            update_response = client.put(
                f"/api/v1/workflows/{created['id']}",
                json={
                    "name": name,
                    "description": "updated from test",
                    "status": "PUBLISHED",
                    "nodes": [
                        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                        {"nodeKey": "llm", "type": "LLM", "name": "Answer", "config": {"outputVariable": "answer"}},
                        {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
                    ],
                    "edges": [
                        {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                        {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
                    ],
                },
            )
            self.assertEqual(update_response.status_code, 200)
            updated = update_response.json()["data"]
            self.assertEqual(updated["description"], "updated from test")
            self.assertEqual(updated["status"], "PUBLISHED")
            self.assertEqual([node["nodeKey"] for node in updated["nodes"]], ["start", "llm", "end"])

            delete_response = client.delete(f"/api/v1/workflows/{created['id']}")
            self.assertEqual(delete_response.status_code, 200)
            self.assertIsNone(delete_response.json()["data"])

            missing_response = client.get(f"/api/v1/workflows/{created['id']}")
            self.assertEqual(missing_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
