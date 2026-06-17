from contextlib import contextmanager
import json
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.modules.customer_assistant.domain.llm_primary import (
    CustomerAssistantLlmRuntimeMode,
    CustomerAssistantLlmRuntimeSettings,
)
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantLlmPrimaryRuntimeTest(unittest.TestCase):
    def test_primary_task_recognition_selects_valid_llm_candidate_when_opted_in(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                llm_runtime_settings=CustomerAssistantLlmRuntimeSettings(
                    mode=CustomerAssistantLlmRuntimeMode.LLM_PRIMARY_WITH_FALLBACK,
                    min_confidence=0.70,
                ),
                llm_primary_client=_FakePrimaryClient(task_confidence=0.88),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(
                int(assistant_session["id"]),
                "帮我查随身包规则",
                idempotency_key="llm-primary-task",
            )
            events = service.list_events(int(assistant_session["id"]))["list"]

        self.assertEqual([task["taskKey"] for task in result["taskSummaries"]], ["baggage_qa"])
        self.assertIn("llm_primary_selected", [event["type"] for event in events])

    def test_primary_recommendation_selects_valid_llm_candidate_when_opted_in(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                llm_runtime_settings=CustomerAssistantLlmRuntimeSettings(
                    mode=CustomerAssistantLlmRuntimeMode.LLM_PRIMARY_WITH_FALLBACK,
                    min_confidence=0.70,
                ),
                llm_primary_client=_FakePrimaryClient(task_confidence=0.88),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(
                int(assistant_session["id"]),
                "行李额是多少",
                idempotency_key="llm-primary-recommendation",
            )
            events = service.list_events(int(assistant_session["id"]))["list"]

        self.assertEqual(result["operatorRecommendation"], "LLM primary recommendation")
        self.assertEqual(result["customerReplyDraft"], "LLM primary draft")
        self.assertTrue(
            any(
                event["type"] == "llm_primary_selected"
                and event["payload"]["phase"] == "recommendation"
                for event in events
            )
        )

    def test_high_risk_direct_write_candidate_falls_back_without_executing_action(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                llm_runtime_settings=CustomerAssistantLlmRuntimeSettings(
                    mode=CustomerAssistantLlmRuntimeMode.LLM_PRIMARY_WITH_FALLBACK,
                    min_confidence=0.70,
                ),
                llm_primary_client=_FakePrimaryClient(command_type="EXECUTE_REFUND"),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(
                int(assistant_session["id"]),
                "请直接退款 TK-200",
                idempotency_key="llm-primary-direct-write",
            )
            events = service.list_events(int(assistant_session["id"]))["list"]

        self.assertEqual(result["proposedActions"], [])
        self.assertIn("refund_ticket", [task["taskKey"] for task in result["taskSummaries"]])
        self.assertTrue(
            any(
                event["type"] == "llm_primary_fallback"
                and event["payload"]["reason"] == "unsupported_direct_write"
                for event in events
            )
        )


class _FakePrimaryClient:
    def __init__(self, task_confidence: float = 0.88, command_type: str = "ADD_TASK") -> None:
        self._task_confidence = task_confidence
        self._command_type = command_type

    def recognize_tasks(self, **_kwargs) -> str:
        return json.dumps(
            {
                "confidence": self._task_confidence,
                "warnings": [],
                "commands": [
                    {
                        "type": self._command_type,
                        "taskKey": "baggage_qa",
                        "taskType": "QA",
                        "businessKey": "baggage_qa",
                        "workerType": "stub_qa",
                        "workerRef": "baggage_allowance",
                        "reason": "fake_llm_primary",
                    }
                ],
            }
        )

    def recommend(self, **_kwargs) -> str:
        return json.dumps(
            {
                "operatorRecommendation": "LLM primary recommendation",
                "customerReplyDraft": "LLM primary draft",
                "warnings": [],
                "taskSummaries": [],
            }
        )


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("customer_assistant_llm_primary", tables=customer_assistant_tables(), register=register_customer_assistant_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
