import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class EvalSetFieldsTest(unittest.TestCase):
    def test_eval_set_fields_are_saved_and_required_dynamic_fields_validate_cases(self) -> None:
        with TestClient(app) as client:
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Field Set {time.time_ns()}", "description": "fields"},
            ).json()["data"]
            fields_response = client.put(
                f"/api/v1/eval-sets/{eval_set['id']}/fields",
                json={
                    "fields": [
                        {"key": "input", "label": "Input", "contentType": "TEXT", "required": True, "displayOrder": 1},
                        {"key": "expectedOutput", "label": "Expected", "contentType": "TEXT", "required": True, "displayOrder": 2},
                        {"key": "reference_output", "label": "Reference", "contentType": "TEXT", "required": True, "displayOrder": 3},
                    ]
                },
            )
            missing_required = client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={"input": "hello", "expectedOutput": "world", "tags": [], "metadata": {}},
            )
            created_case = client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={
                    "input": "hello",
                    "expectedOutput": "world",
                    "tags": [],
                    "metadata": {"reference_output": "docs paragraph"},
                },
            )
            fields_list = client.get(f"/api/v1/eval-sets/{eval_set['id']}/fields")
            detail = client.get(f"/api/v1/eval-sets/{eval_set['id']}").json()["data"]

        self.assertEqual(fields_response.status_code, 200, fields_response.text)
        self.assertEqual(fields_response.json()["data"]["list"][2]["key"], "reference_output")
        self.assertEqual(missing_required.status_code, 400)
        self.assertIn("Reference", missing_required.json()["message"])
        self.assertEqual(created_case.status_code, 200, created_case.text)
        self.assertEqual(created_case.json()["data"]["metadata"]["reference_output"], "docs paragraph")
        self.assertEqual(fields_list.status_code, 200)
        self.assertEqual(fields_list.json()["data"]["total"], 3)
        self.assertEqual(detail["fieldSchema"][2]["key"], "reference_output")


if __name__ == "__main__":
    unittest.main()
