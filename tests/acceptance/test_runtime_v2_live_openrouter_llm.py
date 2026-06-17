from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import time
import unittest
from typing import Any

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.database_url_policy import assert_mysql8_database_url
from app.core.db_write import insert_and_get_id
from app.core.schema import register_baseline_tables
from app.main import app


RUN_LIVE = os.getenv("HIFY_RUN_LIVE_RUNTIME_V2_OPENROUTER") == "1"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"
ARTIFACT_PATH = Path(
    "artifacts/slices/136-runtime-v2-openrouter-live-acceptance/136.1/runtime-v2-openrouter-live.md"
)


@unittest.skipUnless(
    RUN_LIVE,
    "Set HIFY_RUN_LIVE_RUNTIME_V2_OPENROUTER=1, OPENROUTER_API_KEY, and a disposable HIFY_DATABASE_URL to run",
)
class RuntimeV2LiveOpenRouterLlmAcceptanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api_key = os.environ["OPENROUTER_API_KEY"]
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self.model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)
        self.database_url = os.getenv("HIFY_DATABASE_URL", "")
        if not self.database_url:
            self.skipTest("Set HIFY_DATABASE_URL to a disposable MySQL8 database before running this live gate.")
        assert_mysql8_database_url(self.database_url)
        initialise_database()
        register_baseline_tables()

    def test_workflow_runs_v2_executes_live_openrouter_llm_and_persists_debug_evidence(self) -> None:
        marker = f"HIFY_RUNTIME_V2_LIVE_{time.time_ns()}"
        _seed_live_agent(self.api_key, self.base_url, self.model)

        with TestClient(app) as client:
            workflow = _create_live_llm_workflow(client, marker)
            published = client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            self.assertEqual(published.status_code, 200, published.text)
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {"userMessage": "runtime v2 live acceptance"}},
            ).json()["data"]
            terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED", timeout=60.0)
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        answer = str(terminal["output"].get("answer") or "")
        self.assertIn(marker, answer)
        self.assertNotIn("LLM mock:", str(terminal["output"]))
        llm_node = next(node for node in nodes if node["nodeKey"] == "llm")
        node_answer = str(llm_node["outputs"].get("answer") or "")
        self.assertIn(marker, node_answer)
        self.assertIn("__debug", llm_node["outputs"])
        self.assertIn("__usage", llm_node["outputs"])
        self.assertGreater(int(llm_node["outputs"]["__usage"]["totalTokens"]), 0)
        llm_debug = llm_node["outputs"]["__debug"]["llm"]
        self.assertEqual(llm_debug["input"]["model"], self.model)
        completed = next(
            event
            for event in events
            if event["type"] == "workflow_node_completed" and event.get("nodeId") == "llm"
        )
        self.assertEqual(completed["payload"]["output"]["__usage"]["totalTokens"], llm_node["outputs"]["__usage"]["totalTokens"])
        self.assertNotIn("sk-", str(completed["payload"]["output"]))
        _write_artifact(
            marker=marker,
            model=self.model,
            base_url=self.base_url,
            run_id=int(started["runId"]),
            total_tokens=int(llm_node["outputs"]["__usage"]["totalTokens"]),
            answer_excerpt=answer[:240],
        )


def _seed_live_agent(api_key: str, base_url: str, model: str) -> int:
    now = datetime.now()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    with get_session_factory()() as session:
        provider_id = insert_and_get_id(
            session,
            provider,
            {
                "name": f"Runtime V2 OpenRouter live provider {time.time_ns()}",
                "type": "OPENAI_COMPATIBLE",
                "base_url": base_url,
                "auth_config": {"api_key": api_key},
                "description": "runtime v2 live acceptance provider",
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
                "name": "Runtime V2 OpenRouter live model",
                "model_id": model,
                "context_size": 128000,
                "extra_params": {"temperature": 0},
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
                "name": f"Runtime V2 OpenRouter live agent {time.time_ns()}",
                "description": "",
                "system_prompt": "Follow marker instructions exactly for runtime v2 live acceptance.",
                "model_config_id": model_config_id,
                "temperature": 0,
                "max_tokens": 256,
                "max_context_turns": 4,
                "workflow_id": None,
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        session.commit()
    return int(agent_id)


def _create_live_llm_workflow(client: TestClient, marker: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 OpenRouter live workflow {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "llm",
                    "type": "LLM",
                    "name": "Live LLM",
                    "config": {
                        "systemPrompt": "You are a strict acceptance test assistant.",
                        "prompt": f"Return exactly this marker and nothing else: {marker}",
                        "outputVariable": "answer",
                        "temperature": 0,
                        "maxTokens": 160,
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm", "condition": None},
                {"sourceNodeKey": "llm", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    if response.status_code != 200:
        raise AssertionError(f"workflow creation failed: {response.status_code} {response.text}")
    return response.json()["data"]


def _wait_for_result(client: TestClient, result_ref: str, wanted_status: str, timeout: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] == wanted_status:
            return latest
        if latest["status"] in {"FAILED", "CANCELLED", "INTERRUPTED"} and latest["status"] != wanted_status:
            raise AssertionError(f"Expected {wanted_status}, got {latest}")
        time.sleep(0.2)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def _write_artifact(
    *,
    marker: str,
    model: str,
    base_url: str,
    run_id: int,
    total_tokens: int,
    answer_excerpt: str,
) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    safe_excerpt = answer_excerpt.replace("`", "'")
    ARTIFACT_PATH.write_text(
        "\n".join(
            [
                "# Runtime V2 OpenRouter Live LLM Acceptance",
                "",
                "- Slice: 136.1 runtime v2 live provider gate",
                "- Entry: `/api/v1/workflows/{id}/runs-v2`",
                f"- Base URL: `{base_url}`",
                f"- Model: `{model}`",
                "- API key: runtime environment only, not recorded",
                f"- Run ID: `{run_id}`",
                f"- Marker: `{marker}`",
                f"- Total tokens: `{total_tokens}`",
                f"- Answer excerpt: `{safe_excerpt}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
