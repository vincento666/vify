import unittest
from typing import Any

from fastapi import Depends
from fastapi.testclient import TestClient
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base, get_session, get_session_factory
from app.main import app
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.router import get_workflow_service


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": max(1, len(content.split()))},
    }


class WorkflowLinearRunTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_workflow_service, None)

    def test_run_linear_workflow_records_run_and_node_runs(self) -> None:
        fake_client = FakeOpenAIChatClient(response_payload=_assistant_payload("LLM_LINEAR_OK"))
        app.dependency_overrides[get_workflow_service] = _service_override(fake_client)

        with TestClient(app) as client:
            workflow = _create_linear_workflow(client)

            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "reset password"}},
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"]["answer"], "LLM_LINEAR_OK")
        self.assertNotIn("DOWNSTREAM", data["output"]["answer"])
        self.assertGreater(data["runId"], 0)
        self.assertEqual(_run_status(data["runId"]), "SUCCEEDED")
        self.assertEqual(_node_run_count(data["runId"]), 3)


def _service_override(fake_client: FakeOpenAIChatClient):
    def override(session: Session = Depends(get_session)) -> WorkflowService:
        return WorkflowService(
            WorkflowRepository(session),
            agent_repository=_AgentRepositoryStub(),
            model_facade=_ModelFacadeStub(),
            llm_client_factory=lambda _config: fake_client,
        )

    return override


def _create_linear_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": "Linear workflow run",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Answer",
                    "config": {"prompt": "User: {{start.userMessage}}", "outputVariable": "answer"},
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    return response.json()["data"]


def _run_status(run_id: int) -> str:
    workflow_run = Base.metadata.tables["workflow_run"]
    with get_session_factory()() as session:
        return str(
            session.execute(
                workflow_run.select().where(workflow_run.c.id == run_id)
            ).mappings().one()["status"]
        )


def _node_run_count(run_id: int) -> int:
    workflow_node_run = Base.metadata.tables["workflow_node_run"]
    with get_session_factory()() as session:
        return int(
            session.execute(
                sa.select(sa.func.count())
                .select_from(workflow_node_run)
                .where(workflow_node_run.c.workflow_run_id == run_id)
            ).scalar_one()
        )


class _AgentRepositoryStub:
    def find_default_live_llm_agent(self) -> dict[str, Any]:
        return {
            "id": 501,
            "name": "Canvas Live Agent",
            "system_prompt": "You are the workflow canvas agent.",
            "model_config_id": 601,
            "temperature": 0.1,
            "max_tokens": 128,
            "enabled": True,
        }


class _ModelFacadeStub:
    def get_enabled_model_config(self, model_config_id: int) -> ModelConfigDto:
        assert model_config_id == 601
        return ModelConfigDto(
            id=model_config_id,
            provider_id=701,
            provider_type="OPENAI",
            provider_base_url="https://example.test/v1",
            provider_auth_config={},
            name="Fake model",
            model_id="fake-model",
            context_size=4096,
            extra_params={},
        )


if __name__ == "__main__":
    unittest.main()
