import importlib
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

import sqlalchemy as sa

from app.core.config import get_settings
from app.core.database import Base, get_session_factory, initialise_database
from app.modules.customer_assistant.infra.schema import register_customer_assistant_tables
from app.modules.runtime_lab.infra.airline_chatflow_seed import AIRLINE_CHATFLOW_SOP_IDS


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
            self.assertNotIn("OPENROUTER_API_KEY", content)
            self.assertNotIn("sk-", content)


class _temp_database:
    def __enter__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._previous_url = os.environ.get("HIFY_DATABASE_URL")
        os.environ["HIFY_DATABASE_URL"] = f"sqlite:///{Path(self._tmp.name) / 'seed.db'}"
        get_settings.cache_clear()
        register_customer_assistant_tables()
        initialise_database()

    def __exit__(self, *_exc: object) -> None:
        if self._previous_url is None:
            os.environ.pop("HIFY_DATABASE_URL", None)
        else:
            os.environ["HIFY_DATABASE_URL"] = self._previous_url
        get_settings.cache_clear()
        self._tmp.cleanup()


def _find_mvp_seed_spec() -> object | None:
    try:
        return importlib.util.find_spec("app.modules.demo.mvp_seed")
    except ModuleNotFoundError:
        return None
