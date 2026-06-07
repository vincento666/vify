import time
import unittest
from typing import Any, cast

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.sop_adapter import SopExecutionRequest, SopExecutionStatus
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository


class ChatflowSopRuntimeAdapterIntegrationTest(unittest.TestCase):
    def test_start_continue_suspend_resume_and_complete_real_chatflow_sop(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_chatflow_sop_fixture(client, stamp)
            adapter = _adapter(int(cast(int | str, chatflow["id"])))

            started = adapter.start_sop(_request(message="我要退票", stamp=stamp))
            suspended = adapter.suspend_sop(_request(checkpoint=started.checkpoint, stamp=stamp))
            collected = adapter.continue_sop(
                _request(message="手机号 13800138000", checkpoint=suspended, stamp=stamp)
            )
            completed = adapter.resume_sop(
                _request(message="确认", checkpoint=collected.checkpoint, stamp=stamp)
            )

        self.assertEqual(started.status, SopExecutionStatus.WAITING)
        self.assertEqual(started.current_step, "info_order")
        self.assertIn("phone", started.pending_prompt)
        self.assertEqual(suspended.current_step, "info_order")
        self.assertEqual(collected.status, SopExecutionStatus.WAITING)
        self.assertEqual(collected.current_step, "confirm_1")
        self.assertEqual(collected.collected["phone"], "13800138000")
        self.assertEqual(completed.status, SopExecutionStatus.COMPLETED)
        self.assertEqual(completed.current_step, "completed")
        self.assertEqual(completed.collected["phone"], "13800138000")

    def test_unknown_sop_returns_normalized_failure(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow_sop_fixture(client, time.time_ns())
            adapter = _adapter(int(cast(int | str, chatflow["id"])))

            result = adapter.start_sop(_request(sop_id="unknown_sop", message="start"))

        self.assertEqual(result.status, SopExecutionStatus.FAILED)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error["code"], "SOP_CHATFLOW_NOT_BOUND")


def _adapter(chatflow_id: int) -> ChatflowSopRuntimeAdapter:
    session = get_session_factory()()
    service = WorkflowService(
        WorkflowRepository(session),
        flow_type="CHATFLOW",
        chatflow_state_repository=ChatflowStateRepository(session),
    )
    return ChatflowSopRuntimeAdapter(service, sop_chatflow_ids={"refund_ticket": chatflow_id})


def _request(
    message: str = "",
    checkpoint: Any | None = None,
    sop_id: str = "refund_ticket",
    stamp: int | None = None,
) -> SopExecutionRequest:
    unique = stamp or time.time_ns()
    return SopExecutionRequest(
        runtime_session_id=1001,
        runtime_task_id=2002,
        sop_id=sop_id,
        message=message,
        checkpoint=checkpoint,
        collected={},
        business_refs={},
        metadata={
            "conversationId": f"runtime-lab-chatflow-{unique}",
            "userId": "runtime-lab-user",
            "channel": "runtime-lab",
        },
    )


def _create_chatflow_sop_fixture(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"032 Runtime SOP {stamp}",
            "description": "test-only runtime adapter SOP fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "info_order",
                    "type": "INFORMATION_COLLECTION",
                    "name": "收集手机号",
                    "config": {
                        "inputSource": "{{start.sys.query}}",
                        "outputVariable": "contact",
                        "collectionKey": "contact",
                        "fields": [
                            {
                                "name": "phone",
                                "type": "string",
                                "required": True,
                                "description": "手机号",
                                "targetScope": "conversation",
                                "targetVariable": "phone",
                            }
                        ],
                    },
                },
                {
                    "nodeKey": "confirm_1",
                    "type": "QUESTION",
                    "name": "确认办理",
                    "config": {
                        "question": "请确认是否继续办理退票。",
                        "outputVariable": "confirm",
                        "answerType": "text",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "phone={{info_order.phone}} confirm={{confirm_1.answer}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "info_order", "condition": None},
                {"sourceNodeKey": "info_order", "targetNodeKey": "confirm_1", "condition": None},
                {"sourceNodeKey": "confirm_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, dict)
    return cast(dict[str, object], data)
