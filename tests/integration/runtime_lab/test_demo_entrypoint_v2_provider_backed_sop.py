import json
import time
import unittest
from datetime import datetime
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import Base, get_session_factory
from app.core.db_write import insert_and_get_id
from app.main import app
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus
from app.modules.customer_assistant.domain.workers import ChatflowSopWorker
from app.modules.customer_assistant.web import router as customer_assistant_router
from app.modules.runtime_lab.web import router as runtime_lab_router
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from app.modules.workflow.runtime_job_worker import build_runtime_job_worker


TEST_AGENT_NAME_PREFIX = "Runtime V2 Entry Agent"


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "model": "runtime-v2-entrypoint-model",
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 9, "completion_tokens": 5, "total_tokens": 14},
    }


class DemoEntrypointRuntimeV2ProviderBackedSopTest(unittest.TestCase):
    def setUp(self) -> None:
        _cleanup_seeded_entrypoint_agents()

    def tearDown(self) -> None:
        _cleanup_seeded_entrypoint_agents()

    def test_runtime_lab_chatflow_sop_v2_uses_provider_backed_preferred_agent(self) -> None:
        agent_name = f"{TEST_AGENT_NAME_PREFIX} RuntimeLab {time.time_ns()}"
        _seed_live_agent(agent_name)
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("RUNTIME_LAB_V2_PROVIDER_OK"))

        with (
            patch.object(runtime_lab_router, "RUNTIME_LAB_AIRLINE_LLM_AGENT_NAME", agent_name),
            patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client),
            TestClient(app) as client,
        ):
            chatflow = _create_llm_chatflow(client)
            settings = Settings(
                runtime_lab_sop_chatflow_ids=f"refund_ticket:{chatflow['id']}",
                runtime_lab_intent_arbitrator_mode="fake",
                runtime_lab_sop_llm_mode="live",
            )
            with patch.object(runtime_lab_router, "get_settings", return_value=settings):
                with get_session_factory()() as session:
                    service = runtime_lab_router.get_runtime_lab_service(session)
                    runtime_session = service.create_session()
                    result = service.handle_command(
                        int(runtime_session["id"]),
                        "我要退票",
                        enabled_sop_ids=["refund_ticket"],
                    ).payload
                    chatflow_session = result["activeTask"]["chatflowSession"]
                    run_id = int(chatflow_session["runId"])
                    job = RuntimeJobRepository(session).get_by_run(run_id)
                    assert job is not None
                    drained = build_runtime_job_worker(
                        session,
                        owner="chatflow",
                        worker_id="runtime-lab-provider-backed-test",
                    ).run_once(job_id=int(job["id"]))
                result_response = client.get(str(chatflow_session["resultRef"]))

        self.assertEqual(result["routeDecision"]["action"], "START_SOP")
        self.assertEqual(result["reply"], "Chatflow SOP 正在后台执行，请稍候。")
        self.assertEqual(result["activeTask"]["status"], "RUNNING")
        self.assertEqual(drained["status"], "COMPLETED")
        self.assertEqual(result_response.status_code, 200, result_response.text)
        self.assertEqual(result_response.json()["data"]["output"]["final"], "RUNTIME_LAB_V2_PROVIDER_OK")
        self.assertNotIn("LLM mock:", result["reply"])
        self.assertEqual(fake_client.captured_payload["model"], "runtime-v2-entry-model")

    def test_customer_assistant_chatflow_sop_v2_uses_provider_backed_preferred_agent(self) -> None:
        agent_name = f"{TEST_AGENT_NAME_PREFIX} CustomerAssistant {time.time_ns()}"
        _seed_live_agent(agent_name)
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("CUSTOMER_ASSISTANT_V2_PROVIDER_OK"))

        with (
            patch.object(customer_assistant_router, "CUSTOMER_ASSISTANT_LLM_AGENT_NAME", agent_name),
            patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client),
            TestClient(app) as client,
        ):
            chatflow = _create_llm_chatflow(client)
            with get_session_factory()() as session:
                adapter = customer_assistant_router._customer_assistant_sop_adapter(
                    session,
                    {"refund_ticket": int(chatflow["id"])},
                )
                worker = ChatflowSopWorker(adapter)
                result = worker.run(
                    TaskItem(
                        id=13301,
                        session_id=133,
                        task_key="refund_ticket",
                        task_type="sop",
                        business_key="refund_ticket",
                        short_id="T13301",
                        status=TaskStatus.PENDING,
                        worker_type="chatflow_sop",
                        worker_ref="refund_ticket",
                        checkpoint={},
                        input_snapshot={},
                    ),
                    "我要退票",
                )
                refs = dict(result.evidence["runtimeRefs"])
                drained = _drain_runtime_job(session, int(refs["runId"]))
            result_response = client.get(str(refs["resultRef"]))

        self.assertEqual(result.status, TaskStatus.WAITING)
        self.assertIn("正在后台执行", result.customer_reply_draft)
        self.assertEqual(result.evidence["runtimeVersion"], 2)
        self.assertIn("chatflowRuntimeRefs", result.evidence)
        self.assertEqual(drained["status"], "COMPLETED")
        self.assertEqual(result_response.status_code, 200, result_response.text)
        self.assertEqual(result_response.json()["data"]["output"]["final"], "CUSTOMER_ASSISTANT_V2_PROVIDER_OK")
        self.assertNotIn("LLM mock:", result.customer_reply_draft)
        self.assertEqual(fake_client.captured_payload["model"], "runtime-v2-entry-model")

    def test_customer_assistant_chatflow_sop_v2_mock_mode_does_not_use_provider_agent(self) -> None:
        agent_name = f"{TEST_AGENT_NAME_PREFIX} CustomerAssistant Mock {time.time_ns()}"
        _seed_live_agent(agent_name)
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("SHOULD_NOT_CALL_PROVIDER"))

        with (
            patch.object(customer_assistant_router, "CUSTOMER_ASSISTANT_LLM_AGENT_NAME", agent_name),
            patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: fake_client),
            TestClient(app) as client,
        ):
            chatflow = _create_llm_chatflow(client)
            with get_session_factory()() as session:
                adapter = customer_assistant_router._customer_assistant_sop_adapter(
                    session,
                    {"refund_ticket": int(chatflow["id"])},
                    sop_llm_mode="mock",
                )
                worker = ChatflowSopWorker(adapter)
                result = worker.run(
                    TaskItem(
                        id=13302,
                        session_id=134,
                        task_key="refund_ticket",
                        task_type="sop",
                        business_key="refund_ticket",
                        short_id="T13302",
                        status=TaskStatus.PENDING,
                        worker_type="chatflow_sop",
                        worker_ref="refund_ticket",
                        checkpoint={},
                        input_snapshot={},
                    ),
                    "我要退票",
                )
                refs = dict(result.evidence["runtimeRefs"])
                drained = _drain_runtime_job(session, int(refs["runId"]))
            result_response = client.get(str(refs["resultRef"]))

        self.assertEqual(result.status, TaskStatus.WAITING)
        self.assertIn("正在后台执行", result.customer_reply_draft)
        self.assertEqual(result.evidence["runtimeVersion"], 2)
        self.assertEqual(drained["status"], "COMPLETED")
        self.assertEqual(result_response.status_code, 200, result_response.text)
        self.assertEqual(result_response.json()["data"]["status"], "SUCCEEDED")
        self.assertIn("LLM mock", json.dumps(result_response.json()["data"]["output"], ensure_ascii=False))
        self.assertEqual(fake_client.captured_payloads, [])


def _drain_runtime_job(session: Any, run_id: int) -> dict[str, object]:
    job = RuntimeJobRepository(session).get_by_run(run_id)
    assert job is not None
    return build_runtime_job_worker(
        session,
        owner="chatflow",
        worker_id=f"provider-backed-entrypoint-test-{run_id}",
    ).run_once(job_id=int(job["id"]))


def _seed_live_agent(agent_name: str) -> int:
    now = datetime.now()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    with get_session_factory()() as session:
        provider_id = insert_and_get_id(
            session,
            provider,
            {
                "name": f"Runtime V2 Entry Provider {time.time_ns()}",
                "type": "OPENAI",
                "base_url": "https://runtime-v2-entrypoint.example.test/v1",
                "auth_config": {"api_key": "sk-runtime-v2-entrypoint-test"},
                "description": "",
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        model_config_id = insert_and_get_id(
            session,
            model_config,
            {
                "provider_id": provider_id,
                "name": "runtime-v2-entrypoint-model",
                "model_id": "runtime-v2-entrypoint-model",
                "context_size": 128000,
                "extra_params": {},
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        agent_id = insert_and_get_id(
            session,
            agent,
            {
                "name": agent_name,
                "description": "",
                "system_prompt": "You are a runtime v2 demo entrypoint test agent.",
                "model_config_id": model_config_id,
                "temperature": 0.19,
                "max_tokens": 80,
                "max_context_turns": 4,
                "opening_message": "",
                "suggested_questions": [],
                "workflow_id": None,
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        session.commit()
    return int(agent_id)


def _cleanup_seeded_entrypoint_agents() -> None:
    now = datetime.now()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    with get_session_factory()() as session:
        session.execute(
            agent.update()
            .where(agent.c.name.like(f"{TEST_AGENT_NAME_PREFIX}%"))
            .values(deleted=True, enabled=False, updated_at=now)
        )
        session.execute(
            model_config.update()
            .where(model_config.c.model_id == "runtime-v2-entrypoint-model")
            .values(deleted=True, enabled=False, updated_at=now)
        )
        session.execute(
            provider.update()
            .where(provider.c.name.like("Runtime V2 Entry Provider %"))
            .values(deleted=True, enabled=False, updated_at=now)
        )
        session.commit()


def _create_llm_chatflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Entry Chatflow {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Provider LLM",
                    "config": {
                        "prompt": "Entrypoint prompt: {{sys.query}}",
                        "outputVariable": "answer",
                        "model": "runtime-v2-entry-model",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{llm.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
