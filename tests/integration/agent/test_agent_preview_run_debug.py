from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentPreviewRunDebugTest(unittest.TestCase):
    def test_agent_preview_run_debug_is_backed_by_chat_session_messages(self) -> None:
        model_id = _seed_model()
        stamp = time.time_ns()
        with TestClient(app) as client:
            agent = client.post(
                "/api/v1/agents",
                json={
                    "name": f"021.4 Agent Debug {stamp}",
                    "description": "",
                    "systemPrompt": "Answer by echoing the user request.",
                    "modelConfigId": model_id,
                    "temperature": 0.2,
                    "maxTokens": 512,
                    "maxContextTurns": 4,
                    "toolIds": [],
                },
            ).json()["data"]
            session = client.post("/api/v1/chat/sessions", json={"agentId": agent["id"]}).json()["data"]
            turn = client.post(
                f"/api/v1/chat/sessions/{session['id']}/messages",
                json={"content": "预览调试链路", "stream": False, "variables": {}},
            ).json()["data"]

            response = client.get(f"/api/v1/agents/{agent['id']}/preview-runs/{session['id']}/debug")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["previewRunId"], session["id"])
        self.assertEqual(data["agentId"], agent["id"])
        self.assertEqual(data["sessionId"], session["id"])
        self.assertEqual(data["status"], "成功")
        self.assertEqual(data["input"]["content"], "预览调试链路")
        self.assertEqual(data["output"]["content"], turn["assistantMessage"]["content"])
        self.assertGreater(data["inputChars"], 0)
        self.assertGreater(data["outputChars"], 0)
        self.assertEqual([node["id"] for node in data["nodes"]], ["user", "llm"])
        self.assertEqual([lane["id"] for lane in data["flameLanes"]], ["user", "llm"])


def _seed_model() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Agent Preview Debug Provider {time.time_ns()}",
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
                name="Agent Preview Debug Model",
                model_id="agent-preview-debug-model",
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
