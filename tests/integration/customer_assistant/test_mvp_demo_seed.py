import importlib
import importlib.util
import json
import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

import sqlalchemy as sa
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session_factory
from app.core.database import get_session
from app.main import app
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.runtime_lab.infra.airline_chatflow_seed import AIRLINE_CHATFLOW_SOP_IDS
from tests.support.mysql import mysql8_app_database


class MvpDemoSeedTest(unittest.TestCase):
    def test_seed_creates_idempotent_customer_assistant_demo_topology(self) -> None:
        spec = _find_mvp_seed_spec()
        self.assertIsNotNone(spec, "expected app.modules.demo.mvp_seed module")
        module = importlib.import_module("app.modules.demo.mvp_seed")

        with _temp_database():
            with get_session_factory()() as session:
                first = module.seed_mvp_demo(session)
                second = module.seed_mvp_demo(session)

                self.assertEqual(second.chatflow_bindings, first.chatflow_bindings)
                self.assertEqual(second.customer_session_ids, first.customer_session_ids)
                self.assertEqual(second.knowledge_base_ids, first.knowledge_base_ids)
                self.assertEqual(tuple(first.chatflow_bindings.keys()), AIRLINE_CHATFLOW_SOP_IDS)
                self.assertGreaterEqual(len(first.customer_session_ids), 2)
                self.assertGreaterEqual(len(first.knowledge_base_ids), 1)
                self.assertEqual(
                    tuple(first.story_ids),
                    (
                        "refund_baggage_parallel",
                        "invoice_interrupt_flight_status",
                        "chatflow_block_resume_recommendation",
                    ),
                )

                tables = Base.metadata.tables
                task_count = session.execute(sa.select(sa.func.count()).select_from(tables["customer_assistant_task"])).scalar_one()
                action_count = session.execute(
                    sa.select(sa.func.count()).select_from(tables["customer_assistant_proposed_action"])
                ).scalar_one()
                knowledge_count = session.execute(sa.select(sa.func.count()).select_from(tables["knowledge_base"])).scalar_one()

                self.assertGreaterEqual(int(task_count), 4)
                self.assertGreaterEqual(int(action_count), 1)
                self.assertGreaterEqual(int(knowledge_count), 1)

    def test_seeded_demo_pending_task_action_can_be_confirmed(self) -> None:
        module = importlib.import_module("app.modules.demo.mvp_seed")

        with _temp_database():
            with get_session_factory()() as session:
                seed = module.seed_mvp_demo(session)
                repository = CustomerAssistantRepository(session)
                action = next(
                    item
                    for item in repository.list_proposed_actions(seed.customer_session_ids[0])
                    if item["title"] == "并行处理退票与行李额确认"
                )
                action_id = int(action["id"])
                seeded_payload = dict(action["payload"])
                self.assertEqual(seeded_payload["taskCommand"]["taskKey"], "refund_ticket:MU5137-8899")
                self.assertEqual(seeded_payload["taskCommand"]["workerType"], "chatflow_sop")

            app.dependency_overrides[get_session] = _session_override
            app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)
            try:
                with TestClient(app) as client:
                    response = client.post(f"/api/v1/customer-assistant/proposed-actions/{action_id}/confirm")
                    actions_response = client.get(
                        f"/api/v1/customer-assistant/sessions/{seed.customer_session_ids[0]}/proposed-actions"
                    )
            finally:
                app.dependency_overrides.pop(get_session, None)
                app.dependency_overrides.pop(get_settings, None)

        self.assertEqual(response.status_code, 200, response.text)
        confirmed = response.json()["data"]
        self.assertEqual(confirmed["status"], "CONFIRMED")
        self.assertEqual(confirmed["actionType"], "PROPOSED_TASK_COMMAND")
        self.assertEqual(confirmed["result"]["taskCommand"]["type"], "RESUME_TASK")
        self.assertEqual(actions_response.status_code, 200, actions_response.text)
        action_payload = next(
            item
            for item in actions_response.json()["data"]["list"]
            if item["title"] == "并行处理退票与行李额确认"
        )["payload"]
        self.assertEqual(action_payload["taskCommand"]["workerType"], "chatflow_sop")

    def test_seeded_customer_assistant_demo_tasks_use_productized_worker_routes(self) -> None:
        spec = _find_mvp_seed_spec()
        self.assertIsNotNone(spec, "expected app.modules.demo.mvp_seed module")
        module = importlib.import_module("app.modules.demo.mvp_seed")

        with _temp_database():
            with get_session_factory()() as session:
                module.seed_mvp_demo(session)

                task_table = Base.metadata.tables["customer_assistant_task"]
                task_rows = [
                    dict(row)
                    for row in session.execute(
                        sa.select(
                            task_table.c.task_key,
                            task_table.c.worker_type,
                            task_table.c.worker_ref,
                        ).order_by(task_table.c.task_key.asc())
                    ).mappings()
                ]

        serialized = json.dumps(task_rows, ensure_ascii=False, sort_keys=True)
        flight_status = next(row for row in task_rows if row["task_key"] == "flight_status:CA1301")
        self.assertEqual(flight_status["worker_type"], "chatflow_sop")
        self.assertEqual(flight_status["worker_ref"], "flight_status")
        self.assertNotIn("stub_qa", serialized)

    def test_env_writer_is_idempotent_and_secret_free(self) -> None:
        spec = _find_mvp_seed_spec()
        self.assertIsNotNone(spec, "expected app.modules.demo.mvp_seed module")
        module = importlib.import_module("app.modules.demo.mvp_seed")

        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env"
            env_path.write_text("EXISTING=value\nOPENROUTER_API_KEY=sk-should-stay-outside\n", encoding="utf-8")
            result = module.MvpDemoSeedResult(
                chatflow_bindings={"refund_ticket": 11, "baggage_service": 12},
                customer_session_ids=[101, 102],
                knowledge_base_ids=[201],
                story_ids=[
                    "refund_baggage_parallel",
                    "invoice_interrupt_flight_status",
                    "chatflow_block_resume_recommendation",
                ],
            )

            module.write_mvp_demo_env(env_path, result)
            module.write_mvp_demo_env(env_path, result)

            content = env_path.read_text(encoding="utf-8")
            self.assertEqual(content.count("# Hify MVP demo topology."), 1)
            self.assertIn("EXISTING=value", content)
            self.assertIn("HIFY_MVP_DEMO_STORY_IDS=refund_baggage_parallel,invoice_interrupt_flight_status,chatflow_block_resume_recommendation", content)
            self.assertIn("HIFY_MVP_DEMO_CUSTOMER_SESSION_IDS=101,102", content)
            self.assertIn("HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS=refund_ticket:11,baggage_service:12", content)
            self.assertIn("HIFY_CUSTOMER_ASSISTANT_WORKER_PROFILES_JSON=", content)
            self.assertIn("refund_ticket", content)
            self.assertIn("manual_confirm", content)
            self.assertNotIn("OPENROUTER_API_KEY", content)
            self.assertNotIn("sk-", content)
            self.assertNotIn("stub_qa", content)
            self.assertNotIn("baggage_allowance_stub", content)
            self.assertNotIn("fake_stub_qa_model", content)


class _temp_database:
    def __enter__(self) -> None:
        self._database = mysql8_app_database("mvp_demo_seed")
        self._database.__enter__()

    def __exit__(self, *_exc: object) -> None:
        self._database.__exit__(*_exc)


def _find_mvp_seed_spec() -> object | None:
    try:
        return importlib.util.find_spec("app.modules.demo.mvp_seed")
    except ModuleNotFoundError:
        return None


def _session_override() -> Generator[Session]:
    with get_session_factory()() as session:
        yield session
