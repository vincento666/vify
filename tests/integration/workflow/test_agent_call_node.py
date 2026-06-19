from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient
import sqlalchemy as sa

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentCallNodeIntegrationTest(unittest.TestCase):
    def test_workflow_agent_call_invokes_agent_and_maps_output_downstream(self) -> None:
        agent_id = _seed_direct_agent()

        with TestClient(app) as client:
            workflow = _create_agent_call_flow(client, int(agent_id), "WORKFLOW")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"ticket": "A-221"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertIn("ticket A-221", data["output"]["final"])

        node_output = _node_run_output(data["runId"], "agent_call_1")
        self.assertEqual(node_output["status"], "SUCCEEDED")
        self.assertEqual(node_output["mappedInputSummary"], {"message": "Please handle ticket A-221", "query": "A-221"})
        self.assertEqual(node_output["mappedOutputSummary"]["agentAnswer"], node_output["agentAnswer"])
        self.assertGreater(node_output["sessionId"], 0)
        self.assertGreaterEqual(node_output["latencyMs"], 0)

    def test_chatflow_agent_call_can_include_conversation_context(self) -> None:
        agent_id = _seed_direct_agent(system_prompt="Use the supplied conversation context when it is present.")

        with TestClient(app) as client:
            chatflow = _create_agent_call_flow(client, int(agent_id), "CHATFLOW", history_mode="include")
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "continue the refund case",
                        "sys.conversation_id": f"agent-call-chatflow-{time.time_ns()}",
                        "sys.user_id": "agent-call-user",
                        "sys.channel": "web",
                        "history": [
                            {"role": "user", "content": "previous ticket was B-778"},
                            {"role": "assistant", "content": "I found the order."},
                        ],
                    }
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertIn("continue the refund case", data["output"]["final"])
        self.assertIn("previous ticket was B-778", data["output"]["final"])

    def test_agent_call_selected_node_uses_mapping_and_exposes_evidence(self) -> None:
        agent_id = _seed_direct_agent()

        with TestClient(app) as client:
            workflow = _create_agent_call_flow(client, int(agent_id), "WORKFLOW")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/nodes/agent_call_1/runs",
                json={"input": {"ticket": "C-919"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertIn("ticket C-919", data["output"]["agentAnswer"])
        self.assertEqual(data["output"]["status"], "SUCCEEDED")
        self.assertGreater(data["output"]["sessionId"], 0)

    def test_agent_call_stream_output_emits_chatflow_preview_events(self) -> None:
        agent_id = _seed_direct_agent()

        with TestClient(app) as client:
            chatflow = _create_agent_call_flow(client, int(agent_id), "CHATFLOW", stream_output="enabled")
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "stream agent response",
                        "sys.conversation_id": f"agent-call-stream-{time.time_ns()}",
                        "sys.user_id": "agent-call-user",
                        "sys.channel": "web",
                    }
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        stream_events = data["streamEvents"]
        self.assertTrue(
            any(event["type"] == "agent_delta" and event["nodeKey"] == "agent_call_1" for event in stream_events),
            stream_events,
        )
        node_output = _node_run_output(data["runId"], "agent_call_1")
        self.assertEqual(node_output["events"][0]["type"], "agent_delta")

    def test_agent_call_runs_in_chatflow_runtime_v2(self) -> None:
        agent_id = _seed_direct_agent()

        with TestClient(app) as client:
            chatflow = _create_agent_call_flow(client, int(agent_id), "CHATFLOW", history_mode="include")
            started_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={
                    "input": {
                        "sys.query": "continue ticket V2-445",
                        "sys.conversation_id": f"agent-call-v2-{time.time_ns()}",
                        "sys.user_id": "agent-call-user",
                        "sys.channel": "web",
                        "history": [
                            {"role": "user", "content": "previous ticket was HIST-V2-445"},
                            {"role": "assistant", "content": "I found the order."},
                        ],
                    }
                },
            )
            self.assertEqual(started_response.status_code, 200, started_response.text)
            started = started_response.json()["data"]
            terminal = _wait_for_runtime_v2_result(client, started["resultRef"])
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertIn("continue ticket V2-445", terminal["output"]["final"])
        self.assertIn("previous ticket was HIST-V2-445", terminal["output"]["final"])
        agent_node = next(node for node in nodes if node["nodeKey"] == "agent_call_1")
        self.assertEqual(agent_node["status"], "COMPLETED")
        self.assertGreater(agent_node["outputs"]["sessionId"], 0)

    def test_agent_call_rejects_missing_target_agent(self) -> None:
        with TestClient(app) as client:
            workflow = _create_agent_call_flow(client, 999_999_991, "WORKFLOW")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"ticket": "missing-agent"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("target agent not found", response.json()["message"].lower())

    def test_agent_call_rejects_disabled_target_agent(self) -> None:
        agent_id = _seed_direct_agent(enabled=False)

        with TestClient(app) as client:
            workflow = _create_agent_call_flow(client, int(agent_id), "WORKFLOW")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"ticket": "disabled-agent"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("target agent is disabled", response.json()["message"].lower())

    def test_agent_call_rejects_nested_workflow_agent_to_avoid_recursion(self) -> None:
        agent_id = _seed_direct_agent(workflow_id=123456)

        with TestClient(app) as client:
            workflow = _create_agent_call_flow(client, int(agent_id), "WORKFLOW")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"ticket": "nested-workflow-agent"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("workflow-bound agent", response.json()["message"].lower())

    def test_agent_call_rejects_timeout_budget(self) -> None:
        agent_id = _seed_direct_agent()

        with TestClient(app) as client:
            workflow = _create_agent_call_flow(client, int(agent_id), "WORKFLOW", timeout_ms=0)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"ticket": "timeout-agent"}},
            )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn("timed out", response.json()["message"].lower())


def _seed_direct_agent(
    *,
    enabled: bool = True,
    system_prompt: str = "You are an AgentCall agent. Echo important ticket details.",
    workflow_id: int | None = None,
) -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"AgentCall provider {time.time_ns()}",
                type="OPENAI_COMPATIBLE",
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
                name="AgentCall mock model",
                model_id="agent-call-model",
                context_size=4096,
                extra_params={},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        agent_id = session.execute(
            agent.insert().values(
                name=f"AgentCall agent {time.time_ns()}",
                description="",
                system_prompt=system_prompt,
                model_config_id=model_id,
                temperature=0.2,
                max_tokens=512,
                max_context_turns=10,
                tool_policies={},
                knowledge_base_id=None,
                workflow_id=workflow_id,
                enabled=enabled,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(agent_id)


def _create_agent_call_flow(
    client: TestClient,
    agent_id: int,
    flow_type: str,
    *,
    history_mode: str = "none",
    timeout_ms: int = 30000,
    stream_output: str = "inherit",
) -> dict[str, object]:
    endpoint = "/api/v1/chatflows" if flow_type == "CHATFLOW" else "/api/v1/workflows"
    query_ref = "{{start.sys.query}}" if flow_type == "CHATFLOW" else "{{start.ticket}}"
    message_template = (
        "User asks: {{start.sys.query}}. History: {{start.history}}"
        if flow_type == "CHATFLOW"
        else "Please handle ticket {{start.ticket}}"
    )
    response = client.post(
        endpoint,
        json={
            "name": f"022.5 {flow_type} Agent Call {time.time_ns()}",
            "description": "agent call runtime fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "agent_call_1",
                    "type": "AGENT_CALL",
                    "name": "Call Agent",
                    "config": {
                        "targetAgentId": agent_id,
                        "inputMappings": [
                            {"name": "message", "valueMode": "reference", "value": message_template, "required": True},
                            {"name": "query", "valueMode": "reference", "value": query_ref},
                        ],
                        "historyMode": history_mode,
                        "outputMappings": [
                            {"source": "answer", "target": "agentAnswer"},
                        ],
                        "timeoutMs": timeout_ms,
                        "maxDepth": 3,
                        "streamOutput": stream_output,
                        "outputParameters": [
                            {"name": "agentAnswer", "type": "string"},
                            {"name": "sessionId", "type": "number"},
                            {"name": "status", "type": "string"},
                            {"name": "latencyMs", "type": "number"},
                            {"name": "mappedInputSummary", "type": "object"},
                            {"name": "mappedOutputSummary", "type": "object"},
                            {"name": "toolCalls", "type": "array"},
                            {"name": "error", "type": "string"},
                        ],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "parent received {{agent_call_1.agentAnswer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "agent_call_1", "condition": None},
                {"sourceNodeKey": "agent_call_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _node_run_output(run_id: int, node_key: str) -> dict[str, object]:
    workflow_node_run = Base.metadata.tables["workflow_node_run"]
    with get_session_factory()() as session:
        row = session.execute(
            sa.select(workflow_node_run)
            .where(
                workflow_node_run.c.workflow_run_id == run_id,
                workflow_node_run.c.node_key == node_key,
            )
        ).mappings().one()
        return dict(row["outputs"])


def _wait_for_runtime_v2_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] == "SUCCEEDED":
            return latest
        if latest["status"] in {"FAILED", "CANCELLED", "INTERRUPTED"}:
            raise AssertionError(f"Expected SUCCEEDED, got {latest}")
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for runtime v2 success; latest={latest}")


if __name__ == "__main__":
    unittest.main()
