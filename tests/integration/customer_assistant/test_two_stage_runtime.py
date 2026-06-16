import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.customer_assistant.domain.llm_primary import (
    CustomerAssistantLlmRuntimeMode,
    CustomerAssistantLlmRuntimeSettings,
)
from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus, WorkerResult
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantTwoStageRuntimeTest(unittest.TestCase):
    def test_shadow_records_equivalence_without_extra_worker_dispatch(self) -> None:
        worker = _CountingWorker()
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler({"stub_qa": worker}),
                llm_runtime_settings=CustomerAssistantLlmRuntimeSettings(
                    mode=CustomerAssistantLlmRuntimeMode.TWO_STAGE_SHADOW
                ),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "two-stage-shadow")
            events = service.list_events(int(assistant_session["id"]))["list"]

        self.assertEqual(worker.calls, 1)
        self.assertIn("可免费携带一件手提行李", result["customerReplyDraft"])
        shadow = next(event for event in events if event["type"] == "two_stage_shadow_completed")
        self.assertEqual(shadow["payload"]["equivalence"]["passed"], True)
        self.assertEqual(shadow["payload"]["sideEffects"]["extraWorkerDispatches"], 0)

    def test_primary_selects_schema_compatible_two_stage_output(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler({"stub_qa": _CountingWorker()}),
                llm_runtime_settings=CustomerAssistantLlmRuntimeSettings(
                    mode=CustomerAssistantLlmRuntimeMode.TWO_STAGE_PRIMARY_WITH_FALLBACK
                ),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "two-stage-primary")
            events = service.list_events(int(assistant_session["id"]))["list"]

        self.assertIn("可免费携带一件手提行李", result["customerReplyDraft"])
        self.assertIn("two_stage_primary_selected", [event["type"] for event in events])

    def test_primary_records_sanitized_react_progression_and_keeps_three_stage_contract(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler({"stub_qa": _CountingWorker()}),
                llm_runtime_settings=CustomerAssistantLlmRuntimeSettings(
                    mode=CustomerAssistantLlmRuntimeMode.TWO_STAGE_PRIMARY_WITH_FALLBACK
                ),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "two-stage-react-progress")
            events = service.list_events(int(assistant_session["id"]))["list"]

        event_types = [event["type"] for event in events]
        progression = [
            event
            for event in events
            if event["type"]
            in {
                "two_stage_plan_recorded",
                "two_stage_action_recorded",
                "two_stage_observation_recorded",
            }
        ]

        self.assertEqual(
            [event["type"] for event in progression],
            ["two_stage_plan_recorded", "two_stage_action_recorded", "two_stage_observation_recorded"],
        )
        self.assertEqual([event["payload"]["reactStep"] for event in progression], ["plan", "action", "observation"])
        self.assertEqual(
            [event["payload"]["legacyStage"] for event in progression],
            ["task_recognition", "task_execute_parallel", "task_execute_parallel"],
        )
        self.assertTrue(all(event["visibility"] == "debug" for event in progression))
        self.assertNotIn("chainOfThought", str(progression))

        plan_payload = progression[0]["payload"]
        action_payload = progression[1]["payload"]
        observation_payload = progression[2]["payload"]
        self.assertEqual(plan_payload["summary"]["commands"][0]["taskKey"], "baggage_qa")
        self.assertEqual(action_payload["summary"]["workerDispatchCount"], 1)
        self.assertEqual(observation_payload["summary"]["workerResultCount"], 1)
        self.assertEqual(observation_payload["summary"]["taskStatuses"], [{"taskKey": "baggage_qa", "status": "COMPLETED"}])

        final = next(event for event in events if event["type"] == "two_stage_primary_selected")
        self.assertEqual(final["payload"]["reactStep"], "final")
        self.assertEqual(final["payload"]["legacyStage"], "generate_recommendation")
        self.assertIn("task_recognized", event_types)
        self.assertIn("recommendation_generated", event_types)
        self.assertIn("可免费携带一件手提行李", result["customerReplyDraft"])

    def test_primary_falls_back_when_finalizer_rewrites_waiting_prompt(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler({"stub_qa": _WaitingWorker()}),
                llm_runtime_settings=CustomerAssistantLlmRuntimeSettings(
                    mode=CustomerAssistantLlmRuntimeMode.TWO_STAGE_PRIMARY_WITH_FALLBACK
                ),
                two_stage_runtime=_FaultyTwoStageRuntime(),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "two-stage-fallback")
            events = service.list_events(int(assistant_session["id"]))["list"]

        self.assertEqual(result["customerReplyDraft"], "请提供客票舱位和航司。")
        fallback = next(event for event in events if event["type"] == "two_stage_fallback")
        self.assertEqual(fallback["payload"]["reason"], "prompt_preservation_failed")

    def test_primary_falls_back_when_equivalence_threshold_fails(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                scheduler=LocalWorkerScheduler({"stub_qa": _CountingWorker()}),
                llm_runtime_settings=CustomerAssistantLlmRuntimeSettings(
                    mode=CustomerAssistantLlmRuntimeMode.TWO_STAGE_PRIMARY_WITH_FALLBACK
                ),
                two_stage_runtime=_DivergentTwoStageRuntime(),
            )
            assistant_session = service.create_session()

            result = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "two-stage-equivalence")
            events = service.list_events(int(assistant_session["id"]))["list"]

        self.assertEqual(result["customerReplyDraft"], "经济舱通常可免费携带一件手提行李。")
        fallback = next(event for event in events if event["type"] == "two_stage_fallback")
        self.assertEqual(fallback["payload"]["reason"], "equivalence_threshold_failed")


class _CountingWorker:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, task: TaskItem, message: str) -> WorkerResult:
        self.calls += 1
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.COMPLETED,
            operator_recommendation=f"已按规则回答：{message}",
            customer_reply_draft="经济舱通常可免费携带一件手提行李。",
        )


class _WaitingWorker:
    def run(self, task: TaskItem, message: str) -> WorkerResult:
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.WAITING,
            operator_recommendation="需要客户补充舱位和航司。",
            customer_reply_draft="请提供客票舱位和航司。",
            missing_fields=["客票舱位", "航司"],
        )


class _FaultyTwoStageRuntime:
    def finalize(self, input_pack, baseline_result):
        del input_pack
        return {
            "operatorRecommendation": baseline_result.operator_recommendation,
            "customerReplyDraft": "请提供身份证号码。",
            "warnings": [],
        }


class _DivergentTwoStageRuntime:
    def finalize(self, input_pack, baseline_result):
        del input_pack
        return {
            "operatorRecommendation": baseline_result.operator_recommendation,
            "customerReplyDraft": "请放心，行李额度我已经为您确认好了。",
            "warnings": [],
        }


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "customer_assistant_two_stage.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_customer_assistant_tables()
    Base.metadata.create_all(bind=engine, tables=customer_assistant_tables())
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session


if __name__ == "__main__":
    unittest.main()
