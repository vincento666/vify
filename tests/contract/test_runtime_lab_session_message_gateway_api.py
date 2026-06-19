import time
import unittest
from collections.abc import Callable
from typing import Any, cast

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service
from app.modules.workflow.domain.runtime_v2 import ChatflowRuntimeV2Service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository


class RuntimeLabSessionMessageGatewayApiContractTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_runtime_lab_service, None)

    def test_message_gateway_auto_creates_session_and_returns_sop_projection(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_chatflow_sop(client, stamp)
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(int(chatflow["id"]))

            response = client.post(
                "/api/v1/runtime-lab/messages",
                json={"message": "我要退票", "idempotencyKey": f"runtime-lab-gateway-{stamp}"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertTrue(data["sessionId"])
        self.assertEqual(data["conversationId"], f"runtime-lab:{data['sessionId']}")
        self.assertEqual(data["currentSopId"], "refund_ticket")
        self.assertEqual(data["intent"], "refund_ticket")
        self.assertGreater(data["runId"], 0)
        self.assertIn(data["status"], {"WAITING", "COMPLETED", "RUNNING"})
        self.assertIsInstance(data["answer"], str)
        self.assertGreaterEqual(data["latencyMs"], 0)
        self.assertEqual(data["routeDecision"]["action"], "START_SOP")

    def test_message_gateway_reuses_session_and_links_trace_run(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_chatflow_sop(client, stamp)
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(int(chatflow["id"]))

            first = client.post(
                "/api/v1/runtime-lab/messages",
                json={"message": "我要退票", "idempotencyKey": f"runtime-lab-gateway-first-{stamp}"},
            ).json()["data"]
            second_response = client.post(
                "/api/v1/runtime-lab/messages",
                json={
                    "sessionId": first["sessionId"],
                    "message": "手机号 13800138000",
                    "idempotencyKey": f"runtime-lab-gateway-second-{stamp}",
                },
            )
            trace = client.get(f"/api/v1/runtime-lab/sessions/{first['sessionId']}/chatflow-trace").json()["data"]

        self.assertEqual(second_response.status_code, 200, second_response.text)
        second = second_response.json()["data"]
        self.assertEqual(second["sessionId"], first["sessionId"])
        self.assertEqual(second["currentSopId"], "refund_ticket")
        task_trace = next(task for task in trace["tasks"] if task["sopId"] == "refund_ticket")
        self.assertEqual(task_trace["chatflow"]["runId"], second["runId"])
        self.assertEqual(
            task_trace["chatflow"]["sessionId"],
            f"runtime-lab-{first['sessionId']}-{first['activeTask']['id']}-refund_ticket",
        )


def _runtime_service_override(chatflow_id: int) -> Callable[[Session], RuntimeLabService]:
    def override(session: Session = Depends(get_session)) -> RuntimeLabService:
        workflow_repository = WorkflowRepository(session)
        state_repository = ChatflowStateRepository(session)
        workflow_service = WorkflowService(
            workflow_repository,
            flow_type="CHATFLOW",
            chatflow_state_repository=state_repository,
        )
        adapter = ChatflowSopRuntimeAdapter(
            workflow_service,
            sop_chatflow_ids={"refund_ticket": chatflow_id},
            fallback_adapter=FakeSopRuntimeAdapter(),
            runtime_v2_service=ChatflowRuntimeV2Service(
                workflow_repository,
                state_repository,
                completion_delay_seconds=0,
            ),
        )
        return RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)

    return override


def _create_chatflow_sop(client: TestClient, stamp: int) -> dict[str, Any]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"197 Runtime Lab SOP Gateway {stamp}",
            "description": "runtime lab SOP session gateway fixture",
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
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "phone={{info_order.phone}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "info_order", "condition": None},
                {"sourceNodeKey": "info_order", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json()["data"])


if __name__ == "__main__":
    unittest.main()
