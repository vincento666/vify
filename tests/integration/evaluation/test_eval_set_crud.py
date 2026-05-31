import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class EvalSetCrudTest(unittest.TestCase):
    def test_create_list_update_case_edit_and_delete_eval_set(self) -> None:
        name = f"Refund Eval Set {time.time_ns()}"

        with TestClient(app) as client:
            create_response = client.post(
                "/api/v1/eval-sets",
                json={"name": name, "description": "refund regression cases"},
            )
            self.assertEqual(create_response.status_code, 200)
            created = create_response.json()["data"]
            self.assertEqual(created["name"], name)
            self.assertEqual(created["caseCount"], 0)

            case_response = client.post(
                f"/api/v1/eval-sets/{created['id']}/cases",
                json={
                    "input": "用户问：7 天内可以退款吗？",
                    "expectedOutput": "7 天内可以申请退款",
                    "tags": ["refund", "policy"],
                    "metadata": {"priority": "p0"},
                },
            )
            self.assertEqual(case_response.status_code, 200)
            created_case = case_response.json()["data"]
            self.assertEqual(created_case["evalSetId"], created["id"])
            self.assertEqual(created_case["tags"], ["refund", "policy"])

            detail_response = client.get(f"/api/v1/eval-sets/{created['id']}")
            self.assertEqual(detail_response.status_code, 200)
            detail = detail_response.json()["data"]
            self.assertEqual(detail["caseCount"], 1)
            self.assertEqual(detail["cases"][0]["expectedOutput"], "7 天内可以申请退款")

            update_case_response = client.put(
                f"/api/v1/eval-cases/{created_case['id']}",
                json={
                    "input": "用户问：8 天后可以退款吗？",
                    "expectedOutput": "超过 7 天需转人工审核",
                    "tags": ["refund", "manual-review"],
                    "metadata": {"priority": "p1"},
                },
            )
            self.assertEqual(update_case_response.status_code, 200)
            self.assertEqual(update_case_response.json()["data"]["metadata"]["priority"], "p1")

            update_set_response = client.put(
                f"/api/v1/eval-sets/{created['id']}",
                json={"name": name, "description": "updated regression cases"},
            )
            self.assertEqual(update_set_response.status_code, 200)
            self.assertEqual(update_set_response.json()["data"]["description"], "updated regression cases")

            list_response = client.get("/api/v1/eval-sets", params={"page": 1, "pageSize": 20})
            self.assertEqual(list_response.status_code, 200)
            page = list_response.json()["data"]
            listed = next(item for item in page["list"] if item["id"] == created["id"])
            self.assertEqual(listed["caseCount"], 1)

            delete_case_response = client.delete(f"/api/v1/eval-cases/{created_case['id']}")
            self.assertEqual(delete_case_response.status_code, 200)

            delete_set_response = client.delete(f"/api/v1/eval-sets/{created['id']}")
            self.assertEqual(delete_set_response.status_code, 200)
            self.assertIsNone(delete_set_response.json()["data"])

            missing_response = client.get(f"/api/v1/eval-sets/{created['id']}")
            self.assertEqual(missing_response.status_code, 404)

    def test_rejects_case_creation_for_missing_set_and_empty_expected_output(self) -> None:
        with TestClient(app) as client:
            missing_set_response = client.post(
                "/api/v1/eval-sets/999999999/cases",
                json={"input": "hello", "expectedOutput": "world", "tags": []},
            )
            self.assertEqual(missing_set_response.status_code, 404)

            invalid_payload_response = client.post(
                "/api/v1/eval-sets/999999999/cases",
                json={"input": "hello", "expectedOutput": "", "tags": []},
            )
            self.assertEqual(invalid_payload_response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
