import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app
from app.modules.demo.mvp_seed import MVP_DEMO_STORY_IDS, seed_mvp_demo


class CustomerAssistantDemoStoryApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "customer_assistant_demo_story_api.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(bind=self._engine)
        self._factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)
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

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session
