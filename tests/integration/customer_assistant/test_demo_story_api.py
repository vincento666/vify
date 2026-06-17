import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database
from app.modules.demo.mvp_seed import MVP_DEMO_STORY_IDS, seed_mvp_demo


class CustomerAssistantDemoStoryApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "customer_assistant_demo_story_api")
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        with self._factory() as session:
            self._seed = seed_mvp_demo(session)
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_lists_seeded_demo_stories_with_session_refs(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/customer-assistant/demo-stories")

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["total"], 3)
        self.assertEqual([item["storyId"] for item in data["list"]], list(MVP_DEMO_STORY_IDS))
        self.assertEqual([item["sessionId"] for item in data["list"]], self._seed.customer_session_ids)
        self.assertTrue(all(item["taskCount"] >= 1 for item in data["list"]))
        self.assertTrue(all(item["pendingActionCount"] >= 1 for item in data["list"]))
        self.assertTrue(all(item["knowledgeBaseIds"] == self._seed.knowledge_base_ids for item in data["list"]))

    def test_lists_seeded_demo_story_proposed_actions(self) -> None:
        with TestClient(app) as client:
            response = client.get(
                f"/api/v1/customer-assistant/sessions/{self._seed.customer_session_ids[0]}/proposed-actions"
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(data["list"][0]["status"], "PENDING")
        self.assertEqual(data["list"][0]["actionType"], "PROPOSED_TASK_COMMAND")

    def test_returns_seeded_demo_story_observability_summary(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/customer-assistant/demo-stories/metrics")

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["storyCount"], len(MVP_DEMO_STORY_IDS))
        self.assertEqual(data["sessionCount"], len(self._seed.customer_session_ids))
        self.assertEqual([item["storyId"] for item in data["stories"]], list(MVP_DEMO_STORY_IDS))
        self.assertGreaterEqual(sum(data["taskStatusCounts"].values()), 3)
        self.assertGreaterEqual(data["proposedActionStatusCounts"]["PENDING"], 3)
        self.assertGreaterEqual(data["humanConfirmation"]["pending"], 3)
        self.assertIn("adoptionRate", data["humanConfirmation"])
        self.assertGreater(data["eventCounts"]["total"], 0)
        self.assertIn("workerEventCounts", data)
        self.assertLessEqual(len(data["recentFailureReasons"]), 5)
        self.assertNotIn("TK12345", str(data))
        self.assertNotIn("13800000000", str(data))

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session
