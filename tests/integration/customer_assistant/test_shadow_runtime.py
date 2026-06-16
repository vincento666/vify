import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.domain.shadow import (
    CustomerAssistantShadowSettings,
    FakeCustomerAssistantShadowClient,
)
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantShadowRuntimeTest(unittest.TestCase):
    def test_fake_shadow_events_do_not_change_deterministic_runtime_result(self) -> None:
        with _session() as session:
            repository = CustomerAssistantRepository(session)
            service = CustomerAssistantService(
                repository,
                shadow_settings=CustomerAssistantShadowSettings(mode="fake"),
                shadow_client=FakeCustomerAssistantShadowClient(),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(
                int(assistant_session["id"]),
                "我要退票",
                idempotency_key="shadow-fake",
                actor="customer",
            )
            rows = service.list_events(int(assistant_session["id"]))["list"]

        shadow_events = [event for event in rows if event["source"] == "llm_shadow"]
        self.assertEqual(
            [event["type"] for event in shadow_events],
            [
                "llm_shadow_started",
                "llm_shadow_completed",
                "llm_shadow_diff_recorded",
                "llm_shadow_started",
                "llm_shadow_completed",
                "llm_shadow_diff_recorded",
            ],
        )
        self.assertEqual([event["actor"] for event in shadow_events], ["customer"] * 6)
        self.assertEqual(shadow_events[0]["payload"]["phase"], "task_recognition")
        self.assertEqual(shadow_events[3]["payload"]["phase"], "recommendation")
        self.assertTrue(shadow_events[2]["payload"]["diff"]["matches"])
        self.assertTrue(shadow_events[5]["payload"]["diff"]["matches"])
        self.assertEqual(result["taskSummaries"][0]["taskKey"], "refund_ticket")
        self.assertIn("refund_ticket", result["operatorRecommendation"])
        self.assertNotIn("llm_shadow", result["customerReplyDraft"])

    def test_shadow_failure_records_debug_event_and_main_turn_still_succeeds(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                shadow_settings=CustomerAssistantShadowSettings(mode="fake"),
                shadow_client=_BrokenShadowClient(),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "我要退票", idempotency_key="shadow-broken")
            rows = service.list_events(int(assistant_session["id"]))["list"]

        failures = [event for event in rows if event["type"] == "llm_shadow_failed"]
        self.assertEqual(result["taskSummaries"][0]["taskKey"], "refund_ticket")
        self.assertGreaterEqual(len(failures), 1)
        self.assertEqual(failures[0]["source"], "llm_shadow")
        self.assertIn("invalid JSON", failures[0]["payload"]["error"])


class _BrokenShadowClient:
    def recognize_tasks(self, **_kwargs) -> str:
        return "{not-json"

    def recommend(self, **_kwargs) -> str:
        raise RuntimeError("shadow recommendation down")


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "customer_assistant_shadow.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_customer_assistant_tables()
    Base.metadata.create_all(bind=engine, tables=customer_assistant_tables())
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session


if __name__ == "__main__":
    unittest.main()
