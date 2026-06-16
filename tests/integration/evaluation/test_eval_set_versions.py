import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class EvalSetVersionsTest(unittest.TestCase):
    def test_eval_set_versions_are_immutable_and_track_draft_state(self) -> None:
        with TestClient(app) as client:
            eval_set = client.post(
                "/api/v1/eval-sets",
                json={"name": f"Versioned Set {time.time_ns()}", "description": "draft"},
            ).json()["data"]
            case = client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/cases",
                json={"input": "hello", "expectedOutput": "world", "tags": ["v1"], "metadata": {"locale": "en"}},
            ).json()["data"]

            version_1 = client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/versions",
                json={"description": "first release"},
            ).json()["data"]

            client.put(
                f"/api/v1/eval-cases/{case['id']}",
                json={"input": "hello edited", "expectedOutput": "world edited", "tags": ["v2"], "metadata": {}},
            )
            dirty_detail = client.get(f"/api/v1/eval-sets/{eval_set['id']}").json()["data"]
            version_2 = client.post(
                f"/api/v1/eval-sets/{eval_set['id']}/versions",
                json={"description": "second release"},
            ).json()["data"]
            clean_detail = client.get(f"/api/v1/eval-sets/{eval_set['id']}").json()["data"]
            versions = client.get(f"/api/v1/eval-sets/{eval_set['id']}/versions").json()["data"]["list"]
            version_1_detail = client.get(f"/api/v1/eval-sets/{eval_set['id']}/versions/{version_1['id']}").json()["data"]

        self.assertEqual(version_1["version"], "0.0.1")
        self.assertEqual(version_1["caseCount"], 1)
        self.assertEqual(version_1["caseSnapshot"][0]["input"], "hello")
        self.assertTrue(dirty_detail["draftChanged"])
        self.assertEqual(dirty_detail["latestVersion"], "0.0.1")
        self.assertEqual(version_2["version"], "0.0.2")
        self.assertEqual(version_2["caseSnapshot"][0]["input"], "hello edited")
        self.assertFalse(clean_detail["draftChanged"])
        self.assertEqual(clean_detail["latestVersion"], "0.0.2")
        self.assertEqual([item["version"] for item in versions], ["0.0.2", "0.0.1"])
        self.assertEqual(version_1_detail["caseSnapshot"][0]["input"], "hello")
        self.assertEqual(version_1_detail["caseSnapshot"][0]["expectedOutput"], "world")


if __name__ == "__main__":
    unittest.main()
