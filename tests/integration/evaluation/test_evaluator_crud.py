import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class EvaluatorCrudTest(unittest.TestCase):
    def test_create_sample_test_update_list_and_delete_evaluator(self) -> None:
        name = f"Keyword Evaluator {time.time_ns()}"

        with TestClient(app) as client:
            draft_test = client.post(
                "/api/v1/evaluators/test",
                json={
                    "type": "CONTAINS_KEYWORDS",
                    "config": {"keywords": ["refund", "policy"], "matchMode": "all", "ignoreCase": True},
                    "expectedOutput": "",
                    "actualOutput": "Refund policy is available within seven days.",
                },
            )
            self.assertEqual(draft_test.status_code, 200)
            self.assertTrue(draft_test.json()["data"]["passed"])

            create_response = client.post(
                "/api/v1/evaluators",
                json={
                    "name": name,
                    "type": "CONTAINS_KEYWORDS",
                    "config": {"keywords": ["refund", "policy"], "matchMode": "all", "ignoreCase": True},
                },
            )
            self.assertEqual(create_response.status_code, 200)
            created = create_response.json()["data"]
            self.assertEqual(created["name"], name)
            self.assertEqual(created["enabled"], 1)

            saved_test = client.post(
                f"/api/v1/evaluators/{created['id']}/test",
                json={
                    "expectedOutput": "",
                    "actualOutput": "Refund is available, but the policy term is missing.",
                },
            )
            self.assertEqual(saved_test.status_code, 200)
            self.assertTrue(saved_test.json()["data"]["passed"])

            update_response = client.put(
                f"/api/v1/evaluators/{created['id']}",
                json={
                    "name": name,
                    "type": "EXACT_MATCH",
                    "config": {"ignoreCase": True},
                    "enabled": 0,
                },
            )
            self.assertEqual(update_response.status_code, 200)
            self.assertEqual(update_response.json()["data"]["type"], "EXACT_MATCH")
            self.assertEqual(update_response.json()["data"]["enabled"], 0)

            list_response = client.get("/api/v1/evaluators", params={"page": 1, "pageSize": 20})
            self.assertEqual(list_response.status_code, 200)
            self.assertTrue(any(item["id"] == created["id"] for item in list_response.json()["data"]["list"]))

            delete_response = client.delete(f"/api/v1/evaluators/{created['id']}")
            self.assertEqual(delete_response.status_code, 200)

            missing_response = client.get(f"/api/v1/evaluators/{created['id']}")
            self.assertEqual(missing_response.status_code, 404)

    def test_rejects_llm_judge_without_model_and_keyword_evaluator_without_keywords(self) -> None:
        with TestClient(app) as client:
            llm_judge_response = client.post(
                "/api/v1/evaluators",
                json={"name": "LLM judge", "type": "LLM_JUDGE", "config": {}},
            )
            self.assertEqual(llm_judge_response.status_code, 400)

            missing_keywords_response = client.post(
                "/api/v1/evaluators/test",
                json={
                    "type": "CONTAINS_KEYWORDS",
                    "config": {"keywords": []},
                    "expectedOutput": "",
                    "actualOutput": "hello",
                },
            )
            self.assertEqual(missing_keywords_response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
