import json
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database
from app.modules.demo.mvp_seed import seed_mvp_demo


class CustomerAssistantOperatorKnowledgeQaApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "customer_assistant_operator_knowledge_qa")
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

    def test_operator_knowledge_qa_answers_seeded_context_read_only(self) -> None:
        session_id = self._seed.customer_session_ids[0]
        with TestClient(app) as client:
            before_tasks = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"]
            response = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/operator-knowledge-qa",
                json={"question": "退票和行李额可以并行处理吗？"},
            )
            after_tasks = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"]

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["sessionId"], session_id)
        self.assertIn("可以并行处理", data["answer"])
        self.assertIn("执行写操作前分别确认", data["answer"])
        self.assertGreaterEqual(len(data["sources"]), 1)
        self.assertEqual(data["sources"][0]["sourceType"], "FAQ")
        self.assertIn("退票和行李额", data["sources"][0]["title"])
        self.assertGreaterEqual(len(data["evidence"]), 1)
        self.assertEqual(data["contextSummary"]["taskCount"], 2)
        self.assertEqual(data["contextSummary"]["customer"]["name"], "赵女士")
        self.assertEqual(data["contextSummary"]["proposedActionCount"], 1)
        self.assertEqual(after_tasks, before_tasks)
        serialized = json.dumps(data, ensure_ascii=False)
        self.assertNotIn("MU5137-8899", serialized)
        self.assertNotIn("13800000000", serialized)
        self.assertNotIn("hostContext", serialized)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
