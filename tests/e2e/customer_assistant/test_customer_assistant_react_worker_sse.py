import json
import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app
from app.modules.customer_assistant.domain.react_worker import (
    FakeReactWorkerModel,
    ReactModelAction,
    RestrictedReactWorker,
)
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.domain.worker_registry import ReactWorkerConfig
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)
from app.modules.customer_assistant.web.router import get_customer_assistant_service
from tests.integration.customer_assistant.test_react_worker_integration import _ReactTaskCore


class CustomerAssistantReactWorkerSseTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "customer_assistant_react_sse.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        register_customer_assistant_tables()
        Base.metadata.create_all(bind=self._engine, tables=customer_assistant_tables())
        self._factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)
        app.dependency_overrides[get_customer_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_customer_assistant_service, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_react_worker_l1_event_replays_through_customer_assistant_sse(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/customer-assistant/sessions", json={})
            session_id = created.json()["data"]["id"]
            client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "查 TK-100", "idempotencyKey": "react-sse"},
            )
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events").json()["data"]["list"]
            sequence = [event["sequence"] for event in events if event["type"] == "react_worker_started"][0]
            with client.stream(
                "GET",
                f"/api/v1/customer-assistant/sessions/{session_id}/events/stream"
                f"?afterSequence={sequence - 1}&_testLimit=1",
            ) as response:
                streamed = _read_one_sse_data(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(streamed["type"], "react_worker_started")
        self.assertEqual(streamed["source"], "react_worker")

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session

    def _service_override(self, session: Session = Depends(get_session)) -> CustomerAssistantService:
        config = ReactWorkerConfig(
            worker_ref="refund_status_react",
            task_type="refund_status",
            allowed_tools=("lookup_order",),
            max_iterations=3,
            timeout_ms=1000,
        )
        return CustomerAssistantService(
            CustomerAssistantRepository(session),
            core=_ReactTaskCore(),
            scheduler=LocalWorkerScheduler(
                {
                    "react_worker": RestrictedReactWorker(
                        config=config,
                        model=FakeReactWorkerModel(
                            [
                                ReactModelAction.request_tool("lookup_order", {"orderNo": "TK-100"}),
                                ReactModelAction.final(
                                    operator_recommendation="Order TK-100 is refundable.",
                                    customer_reply_draft="订单 TK-100 可退票。",
                                ),
                            ]
                        ),
                        tools={"lookup_order": lambda args: {"orderNo": args["orderNo"], "status": "ok"}},
                    )
                }
            ),
        )


def _read_one_sse_data(response) -> dict[str, object]:
    for line in response.iter_lines():
        if line.startswith("data: "):
            return json.loads(line.removeprefix("data: "))
    raise AssertionError("No SSE data frame returned")


if __name__ == "__main__":
    unittest.main()
