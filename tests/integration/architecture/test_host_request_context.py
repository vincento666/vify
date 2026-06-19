from __future__ import annotations

from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


HOST_HEADERS = {
    "X-Hify-Actor-Id": "host-user-0232",
    "X-Hify-Actor-Name": "Host User",
    "X-Hify-Tenant-Id": "tenant-0232",
    "X-Hify-Org-Id": "org-0232",
    "X-Hify-Roles": "builder,reviewer",
    "X-Hify-Permissions": "workflow:publish,workflow:run,chatflow:publish,evaluation:run",
    "X-Hify-Source": "host-shell",
    "X-Request-Id": "req-0232",
    "Accept-Language": "zh-CN",
}


class HostRequestContextIntegrationTest(unittest.TestCase):
    def test_host_context_is_recorded_for_core_write_and_run_audits(self) -> None:
        model_id = _seed_model()
        with TestClient(app) as client:
            workflow = _create_echo_workflow(client, "WORKFLOW", headers=HOST_HEADERS)
            publish_response = client.post(f"/api/v1/workflows/{workflow['id']}/publish", headers=HOST_HEADERS)
            self.assertEqual(publish_response.status_code, 200, publish_response.text)
            workflow_run_response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": "host-context"}},
                headers=HOST_HEADERS,
            )
            self.assertEqual(workflow_run_response.status_code, 200, workflow_run_response.text)
            workflow_run = workflow_run_response.json()["data"]

            chatflow = _create_echo_workflow(client, "CHATFLOW", headers=HOST_HEADERS)
            chatflow_run_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "host-context", "sys.conversation_id": f"host-{time.time_ns()}"}},
                headers=HOST_HEADERS,
            )
            self.assertEqual(chatflow_run_response.status_code, 200, chatflow_run_response.text)
            chatflow_run = chatflow_run_response.json()["data"]
            channel_response = client.put(
                f"/api/v1/chatflows/{chatflow['id']}/channels/web",
                json={"displayName": "Host Web", "enabled": True, "config": {"channelId": "host-web"}},
                headers=HOST_HEADERS,
            )
            self.assertEqual(channel_response.status_code, 200, channel_response.text)

            agent_response = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Host Agent {time.time_ns()}",
                    "description": "",
                    "systemPrompt": "You are a host-context test agent.",
                    "modelConfigId": model_id,
                    "temperature": 0.2,
                    "maxTokens": 128,
                    "maxContextTurns": 3,
                    "toolIds": [],
                },
                headers=HOST_HEADERS,
            )
            self.assertEqual(agent_response.status_code, 200, agent_response.text)
            agent = agent_response.json()["data"]

            run = _run_evaluation_experiment(client, workflow["id"], headers=HOST_HEADERS)
            audit = _wait_for_audit_records(
                client,
                [
                    ("WORKFLOW_RUN", "WORKFLOW_RUN", workflow_run["runId"]),
                    ("WORKFLOW_PUBLISH", "WORKFLOW", workflow["id"]),
                    ("CHATFLOW_RUN", "CHATFLOW_RUN", chatflow_run["runId"]),
                    ("CHATFLOW_CHANNEL_UPDATE", "CHATFLOW_CHANNEL", f"{chatflow['id']}:web"),
                    ("AGENT_CREATE", "AGENT", agent["id"]),
                    ("EVALUATION_RUN", "EVALUATION_RUN", run["id"]),
                ],
            )

        self._assert_host_context(_find_audit(audit, "WORKFLOW_RUN", "WORKFLOW_RUN", workflow_run["runId"]))
        self._assert_host_context(_find_audit(audit, "WORKFLOW_PUBLISH", "WORKFLOW", workflow["id"]))
        self._assert_host_context(_find_audit(audit, "CHATFLOW_RUN", "CHATFLOW_RUN", chatflow_run["runId"]))
        self._assert_host_context(_find_audit(audit, "CHATFLOW_CHANNEL_UPDATE", "CHATFLOW_CHANNEL", f"{chatflow['id']}:web"))
        self._assert_host_context(_find_audit(audit, "AGENT_CREATE", "AGENT", agent["id"]))
        self._assert_host_context(_find_audit(audit, "EVALUATION_RUN", "EVALUATION_RUN", run["id"]))

    def _assert_host_context(self, record: dict[str, object]) -> None:
        self.assertEqual(record["actor"], "host-user-0232")
        metadata = record["metadata"]
        self.assertIsInstance(metadata, dict)
        context = metadata["requestContext"]  # type: ignore[index]
        self.assertEqual(context["actorId"], "host-user-0232")
        self.assertEqual(context["actorName"], "Host User")
        self.assertEqual(context["tenantId"], "tenant-0232")
        self.assertEqual(context["orgId"], "org-0232")
        self.assertEqual(context["roles"], ["builder", "reviewer"])
        self.assertEqual(
            context["permissions"],
            ["workflow:publish", "workflow:run", "chatflow:publish", "evaluation:run"],
        )
        self.assertEqual(context["requestId"], "req-0232")
        self.assertEqual(context["source"], "host-shell")
        self.assertEqual(context["locale"], "zh-CN")


def _create_echo_workflow(client: TestClient, flow_type: str, *, headers: dict[str, str]) -> dict[str, object]:
    prefix = "chatflows" if flow_type == "CHATFLOW" else "workflows"
    response = client.post(
        f"/api/v1/{prefix}",
        json={
            "name": f"Host {flow_type} {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {"outputVariables": ["userMessage"]}},
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"output": "{{start.userMessage}}", "outputVariable": "output"},
                },
            ],
            "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
        },
        headers=headers,
    )
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()["data"]


def _run_evaluation_experiment(client: TestClient, workflow_id: int, *, headers: dict[str, str]) -> dict[str, object]:
    eval_set = client.post(
        "/api/v1/eval-sets",
        json={"name": f"Host Eval Set {time.time_ns()}", "description": "host context"},
        headers=headers,
    ).json()["data"]
    client.post(
        f"/api/v1/eval-sets/{eval_set['id']}/cases",
        json={"input": "host-context", "expectedOutput": "host-context", "tags": [], "metadata": {}},
        headers=headers,
    )
    evaluator = client.post(
        "/api/v1/evaluators",
        json={"name": f"Host Exact {time.time_ns()}", "type": "EXACT_MATCH", "config": {"ignoreCase": False}},
        headers=headers,
    ).json()["data"]
    experiment = client.post(
        "/api/v1/evaluation-experiments",
        json={
            "name": f"Host Experiment {time.time_ns()}",
            "targetType": "WORKFLOW",
            "targetId": workflow_id,
            "evalSetId": eval_set["id"],
            "evaluatorIds": [evaluator["id"]],
            "targetFieldMapping": {"userMessage": "input"},
            "evaluatorFieldMapping": {"expectedOutput": "expectedOutput", "actualOutput": "__target.output"},
        },
        headers=headers,
    ).json()["data"]
    response = client.post(f"/api/v1/evaluation-experiments/{experiment['id']}/runs", headers=headers)
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()["data"]


def _wait_for_audit_records(
    client: TestClient,
    expected: list[tuple[str, str, object]],
) -> list[dict[str, object]]:
    deadline = time.monotonic() + 5.0
    audit: list[dict[str, object]] = []
    while time.monotonic() < deadline:
        audit = client.get("/api/v1/audit-records", params={"pageSize": 200}).json()["data"]["list"]
        if all(_has_audit(audit, action, resource_type, resource_id) for action, resource_type, resource_id in expected):
            return audit
        time.sleep(0.05)
    return audit


def _has_audit(audit: list[dict[str, object]], action: str, resource_type: str, resource_id: object) -> bool:
    return any(
        record.get("action") == action
        and record.get("resourceType") == resource_type
        and str(record.get("resourceId")) == str(resource_id)
        for record in audit
    )


def _find_audit(audit: list[dict[str, object]], action: str, resource_type: str, resource_id: object) -> dict[str, object]:
    for record in audit:
        if (
            record.get("action") == action
            and record.get("resourceType") == resource_type
            and str(record.get("resourceId")) == str(resource_id)
        ):
            return record
    raise AssertionError(f"missing audit record {action}/{resource_type}/{resource_id}: {audit}")


def _seed_model() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Host Provider {time.time_ns()}",
                type="OPENAI",
                base_url="mock://success",
                auth_config={"api_key": "sk-test"},
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        model_id = session.execute(
            model_config.insert().values(
                provider_id=provider_id,
                name="Host Model",
                model_id="host-model",
                context_size=4096,
                extra_params={},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(model_id)


if __name__ == "__main__":
    unittest.main()
