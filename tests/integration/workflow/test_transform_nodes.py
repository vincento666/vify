import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class WorkflowTransformNodesIntegrationTest(unittest.TestCase):
    def test_workflow_runs_code_text_process_and_json_parse_nodes(self) -> None:
        with TestClient(app) as client:
            workflow = _create_transform_workflow(client)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"first": "Ada", "last": "Lovelace", "score": 97}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(
            data["output"],
            {"final": "Ada Lovelace scored 97 with grade A"},
        )

    def test_workflow_runs_javascript_code_node_main_function(self) -> None:
        with TestClient(app) as client:
            workflow = _create_javascript_code_workflow(client)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"first": "Ada", "last": "Lovelace"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json()["data"]["output"],
            {"final": "Ada Lovelace"},
        )

    def test_json_parse_strict_failure_returns_status_and_error_in_workflow_output(self) -> None:
        with TestClient(app) as client:
            workflow = _create_json_parse_node_workflow(client)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"raw": "{bad json"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json()["data"]["output"],
            {"final": "status=FAILED; error=Expecting property name enclosed in double quotes"},
        )

    def test_chatflow_can_run_same_data_transform_nodes(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow_transform(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "alice@example.com"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "captured alice@example.com"})


def _create_transform_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Transform Workflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "code_1",
                    "type": "CODE",
                    "name": "Code",
                    "config": {
                        "language": "python",
                        "code": "result = {'full_name': inputs['first'] + ' ' + inputs['last'], 'score': int(inputs['score'])}",
                        "outputParameters": [
                            {"name": "full_name", "type": "string"},
                            {"name": "score", "type": "number"},
                        ],
                    },
                },
                {
                    "nodeKey": "text_process_1",
                    "type": "TEXT_PROCESS",
                    "name": "Text Process",
                    "config": {
                        "operation": "format_template",
                        "template": '{"name":"{{code_1.full_name}}","score":{{code_1.score}},"grade":"A"}',
                        "outputVariable": "jsonText",
                    },
                },
                {
                    "nodeKey": "json_parse_1",
                    "type": "JSON_PARSE",
                    "name": "JSON Parse",
                    "config": {
                        "source": "{{text_process_1.jsonText}}",
                        "outputVariable": "parsed",
                        "fieldMap": [
                            {"name": "name", "path": "$.name"},
                            {"name": "score", "path": "$.score"},
                            {"name": "grade", "path": "$.grade"},
                        ],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "{{json_parse_1.name}} scored {{json_parse_1.score}} with grade {{json_parse_1.grade}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "code_1", "condition": None},
                {"sourceNodeKey": "code_1", "targetNodeKey": "text_process_1", "condition": None},
                {"sourceNodeKey": "text_process_1", "targetNodeKey": "json_parse_1", "condition": None},
                {"sourceNodeKey": "json_parse_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_javascript_code_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"JavaScript Code Workflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "code_1",
                    "type": "CODE",
                    "name": "Code",
                    "config": {
                        "language": "javascript",
                        "inputParameters": [
                            {"name": "first", "type": "string", "valueMode": "reference", "value": "{{start.first}}"},
                            {"name": "last", "type": "string", "valueMode": "reference", "value": "{{start.last}}"},
                        ],
                        "code": "async function main({ params }) { return { fullName: `${params.first} ${params.last}` } }",
                        "outputParameters": [{"name": "fullName", "type": "string"}],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{code_1.fullName}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "code_1", "condition": None},
                {"sourceNodeKey": "code_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_json_parse_node_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"JSON Parse Node Test {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "json_parse_1",
                    "type": "JSON_PARSE",
                    "name": "JSON Parse",
                    "config": {"source": "{{start.raw}}", "outputVariable": "parsed"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "status={{json_parse_1.parseStatus}}; error={{json_parse_1.errorMessage}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "json_parse_1", "condition": None},
                {"sourceNodeKey": "json_parse_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_chatflow_transform(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Transform Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "text_process_1",
                    "type": "TEXT_PROCESS",
                    "name": "Extract Email",
                    "config": {
                        "operation": "extract_regex",
                        "source": "{{start.sys.query}}",
                        "pattern": r"[\w.-]+@[\w.-]+",
                        "outputVariable": "email",
                    },
                },
                {
                    "nodeKey": "code_1",
                    "type": "CODE",
                    "name": "Wrap",
                    "config": {
                        "inputParameters": [
                            {"name": "email", "type": "string", "valueMode": "reference", "value": "{{text_process_1.email}}"}
                        ],
                        "code": "result = {'payload': json.dumps({'email': inputs['email']})}",
                    },
                },
                {
                    "nodeKey": "json_parse_1",
                    "type": "JSON_PARSE",
                    "name": "Parse",
                    "config": {
                        "source": "{{code_1.payload}}",
                        "fieldMap": [{"name": "email", "path": "$.email"}],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "captured {{json_parse_1.email}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "text_process_1", "condition": None},
                {"sourceNodeKey": "text_process_1", "targetNodeKey": "code_1", "condition": None},
                {"sourceNodeKey": "code_1", "targetNodeKey": "json_parse_1", "condition": None},
                {"sourceNodeKey": "json_parse_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
