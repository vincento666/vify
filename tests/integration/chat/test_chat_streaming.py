from datetime import datetime
import json
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class ChatStreamingTest(unittest.TestCase):
    def test_stream_message_returns_delta_and_done_events_and_persists_history(self) -> None:
        agent_id = _seed_agent()

        with TestClient(app) as client:
            session_id = client.post("/api/v1/chat/sessions", json={"agentId": agent_id}).json()["data"]["id"]
            with client.stream(
                "POST",
                f"/api/v1/chat/sessions/{session_id}/messages",
                json={"content": "hello stream", "stream": True},
            ) as response:
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/event-stream", response.headers["content-type"])
                body = "".join(response.iter_text())

            events = _parse_sse_events(body)
            self.assertEqual(events[0]["type"], "delta")
            self.assertEqual("".join(event.get("content", "") for event in events), "LLM mock: hello stream")
            self.assertEqual(events[-1]["type"], "done")
            self.assertEqual(events[-1]["finishReason"], "stop")

            messages = client.get(f"/api/v1/chat/sessions/{session_id}/messages").json()["data"]["list"]
            self.assertEqual([message["role"] for message in messages], ["user", "assistant"])
            self.assertEqual(messages[1]["content"], "LLM mock: hello stream")


def _parse_sse_events(body: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for block in body.strip().split("\n\n"):
        if not block.startswith("data:"):
            continue
        events.append(json.loads(block.removeprefix("data:").strip()))
    return events


def _seed_agent() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Stream Chat Provider {time.time_ns()}",
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
                name="Stream Chat Model",
                model_id="stream-chat-model",
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
                name=f"Stream Chat Agent {time.time_ns()}",
                description="",
                system_prompt="",
                model_config_id=model_id,
                temperature=0.7,
                max_tokens=2048,
                max_context_turns=10,
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(agent_id)


if __name__ == "__main__":
    unittest.main()
