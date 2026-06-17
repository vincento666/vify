from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
import unittest
from unittest.mock import patch

from app.core.database import Base
from app.core.schema import register_baseline_tables
from app.modules.customer_assistant.eval.live_react_acceptance import (
    LIVE_GATE_NAME,
    run_customer_assistant_live_react_acceptance,
)
from tests.support.mysql import Mysql8TestDatabase, mysql8_database_url


ARTIFACT_DIR = Path("artifacts/slices/072-customer-assistant-live-react-acceptance/live")
LOCAL_COMPATIBLE_ARTIFACT_DIR = Path(
    "artifacts/slices/072-customer-assistant-live-react-acceptance/local-compatible-provider"
)
PROVIDER_CONFIG_ARTIFACT_DIR = Path(
    "artifacts/slices/093-live-gate-provider-config-bridge/provider-config"
)
LOCAL_COMPATIBLE_API_KEY = "local-api-key"
PROVIDER_CONFIG_API_KEY = "provider-config-secret"
DIRECT_ENV_API_KEY = "direct-secret"
EXPECTED_CATEGORIES = {
    "task_recognition_accuracy",
    "two_stage_recommendation_quality",
    "react_worker_tool_call_policy_and_event_echo",
    "proposed_action_safety_boundaries",
}


class CustomerAssistantLiveReactAcceptanceTest(unittest.TestCase):
    def test_gate_runs_against_local_openai_compatible_provider(self) -> None:
        with _local_openai_compatible_server() as server:
            with mysql8_database_url("live_react_local_provider") as database_url:
                with self.subTest("full local compatible provider gate"):
                    result = run_customer_assistant_live_react_acceptance(
                        env={
                            "HIFY_RUN_CUSTOMER_ASSISTANT_LIVE_REACT_ACCEPTANCE": "1",
                            "HIFY_CUSTOMER_ASSISTANT_LIVE_API_KEY": LOCAL_COMPATIBLE_API_KEY,
                            "HIFY_CUSTOMER_ASSISTANT_LIVE_BASE_URL": server.base_url,
                            "HIFY_DATABASE_URL": database_url,
                        },
                        output_dir=LOCAL_COMPATIBLE_ARTIFACT_DIR,
                    )

            artifact = Path(result.evidence_path or "")
            content = artifact.read_text(encoding="utf-8")

        self.assertEqual(result.status, "completed", result.reason)
        self.assertEqual({category.name for category in result.categories}, EXPECTED_CATEGORIES)
        self.assertGreaterEqual(result.live_model_calls, 5)
        self.assertTrue(any(call["model"] == "xiaomi/mimo-v2-flash" for call in server.calls))
        self.assertTrue(any(call["model"] == "qwen/qwen3.5-9b" for call in server.calls))
        self.assertTrue(all(call["path"] == "/chat/completions" for call in server.calls))
        self.assertTrue(all(call["authorization"] == f"Bearer {LOCAL_COMPATIBLE_API_KEY}" for call in server.calls))
        self.assertIn("task_recognition_accuracy", content)
        self.assertIn("two_stage_recommendation_quality", content)
        self.assertIn("react_worker_tool_call_policy_and_event_echo", content)
        self.assertIn("proposed_action_safety_boundaries", content)
        self.assertNotIn(LOCAL_COMPATIBLE_API_KEY, content)

    def test_gate_resolves_local_provider_model_config_without_recording_secret(self) -> None:
        with _local_openai_compatible_server() as server:
            with _provider_model_config_db(server.base_url, api_key=PROVIDER_CONFIG_API_KEY) as model_config:
                result = run_customer_assistant_live_react_acceptance(
                    env={
                        "HIFY_RUN_CUSTOMER_ASSISTANT_LIVE_REACT_ACCEPTANCE": "1",
                        "HIFY_DATABASE_URL": model_config.database_url,
                        "HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_CONFIG_ID": str(model_config.model_config_id),
                    },
                    output_dir=PROVIDER_CONFIG_ARTIFACT_DIR,
                )
            artifact = Path(result.evidence_path or "")
            content = artifact.read_text(encoding="utf-8")

        self.assertEqual(result.status, "completed", result.reason)
        self.assertGreaterEqual(result.live_model_calls, 5)
        self.assertEqual({category.name for category in result.categories}, EXPECTED_CATEGORIES)
        self.assertTrue(all(call["authorization"] == f"Bearer {PROVIDER_CONFIG_API_KEY}" for call in server.calls))
        self.assertTrue(all(call["model"] == "local/provider-config-model" for call in server.calls))
        self.assertIn("local/provider-config-model", content)
        self.assertNotIn(PROVIDER_CONFIG_API_KEY, content)

    def test_direct_live_env_takes_precedence_over_provider_model_config(self) -> None:
        with _local_openai_compatible_server() as direct_server:
            with _local_openai_compatible_server() as provider_server:
                with _provider_model_config_db(provider_server.base_url, api_key=PROVIDER_CONFIG_API_KEY) as model_config:
                    result = run_customer_assistant_live_react_acceptance(
                        env={
                            "HIFY_RUN_CUSTOMER_ASSISTANT_LIVE_REACT_ACCEPTANCE": "1",
                            "HIFY_CUSTOMER_ASSISTANT_LIVE_API_KEY": DIRECT_ENV_API_KEY,
                            "HIFY_CUSTOMER_ASSISTANT_LIVE_BASE_URL": direct_server.base_url,
                            "HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_POOL": "direct/env-model",
                            "HIFY_DATABASE_URL": model_config.database_url,
                            "HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_CONFIG_ID": str(model_config.model_config_id),
                        },
                        output_dir=PROVIDER_CONFIG_ARTIFACT_DIR,
                    )

        self.assertEqual(result.status, "completed", result.reason)
        self.assertGreaterEqual(result.live_model_calls, 5)
        self.assertTrue(all(call["authorization"] == f"Bearer {DIRECT_ENV_API_KEY}" for call in direct_server.calls))
        self.assertTrue(all(call["model"] == "direct/env-model" for call in direct_server.calls))
        self.assertEqual(provider_server.calls, [])

    def test_provider_config_bridge_does_not_use_ambient_database_url(self) -> None:
        with _local_openai_compatible_server() as server:
            with _provider_model_config_db(server.base_url, api_key=PROVIDER_CONFIG_API_KEY) as model_config:
                with patch.dict(os.environ, {"HIFY_DATABASE_URL": model_config.database_url}):
                    result = run_customer_assistant_live_react_acceptance(
                        env={
                            "HIFY_RUN_CUSTOMER_ASSISTANT_LIVE_REACT_ACCEPTANCE": "1",
                            "HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_CONFIG_ID": str(model_config.model_config_id),
                        },
                        output_dir=PROVIDER_CONFIG_ARTIFACT_DIR,
                    )
                artifact = Path(result.evidence_path or "")
                content = artifact.read_text(encoding="utf-8")

        self.assertEqual(result.status, "failed")
        self.assertIn("resolvable HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_CONFIG_ID", result.reason)
        self.assertEqual(server.calls, [])
        self.assertNotIn(PROVIDER_CONFIG_API_KEY, content)
        self.assertNotIn(model_config.database_url, content)

    def test_provider_config_bridge_rejects_unsupported_or_credential_urls(self) -> None:
        unsupported = _provider_config_failure(provider_type="MOCK", base_url="https://example.test/v1")
        credential_url = _provider_config_failure(
            provider_type="OPENAI_COMPATIBLE",
            base_url="https://user:pass@example.test/v1",
        )

        self.assertEqual(unsupported.status, "failed")
        self.assertEqual(credential_url.status, "failed")
        self.assertNotIn("user:pass", credential_url.artifact_text)
        self.assertNotIn(PROVIDER_CONFIG_API_KEY, credential_url.artifact_text)

    def test_customer_assistant_live_react_acceptance(self) -> None:
        result = run_customer_assistant_live_react_acceptance(env=os.environ, output_dir=ARTIFACT_DIR)
        artifact = Path(result.evidence_path or "")

        self.assertTrue(artifact.exists())
        content = artifact.read_text(encoding="utf-8")
        self.assertIn(LIVE_GATE_NAME, content)
        self.assertNotIn("sk-", content)

        if result.status == "skipped":
            self.skipTest(result.reason)

        self.assertEqual(result.status, "completed", result.reason)
        self.assertGreaterEqual(result.live_model_calls, 3)
        self.assertEqual({category.name for category in result.categories}, EXPECTED_CATEGORIES)
        for category in result.categories:
            self.assertEqual(category.status, "passed", category.summary)
            self.assertTrue(category.success_model)
            self.assertTrue(category.attempts)


class _LocalOpenAICompatibleServer:
    def __init__(self, server: ThreadingHTTPServer, thread: Thread) -> None:
        self._server = server
        self._thread = thread

    @property
    def base_url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    @property
    def calls(self) -> list[dict[str, Any]]:
        return list(getattr(self._server, "calls", []))

    def close(self) -> None:
        self._server.shutdown()
        self._thread.join(timeout=5)
        self._server.server_close()


@contextmanager
def _local_openai_compatible_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _OpenAICompatibleHandler)
    server.calls = []  # type: ignore[attr-defined]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    wrapper = _LocalOpenAICompatibleServer(server, thread)
    try:
        yield wrapper
    finally:
        wrapper.close()


class _ProviderModelConfig:
    def __init__(self, *, database_url: str, model_config_id: int) -> None:
        self.database_url = database_url
        self.model_config_id = model_config_id


class _ProviderConfigFailure:
    def __init__(self, *, status: str, artifact_text: str) -> None:
        self.status = status
        self.artifact_text = artifact_text


@contextmanager
def _provider_model_config_db(
    base_url: str,
    *,
    api_key: str,
    provider_type: str = "OPENAI_COMPATIBLE",
):
    with Mysql8TestDatabase("live_react_provider_config") as database:
        register_baseline_tables()
        database.create_all(
            tables=[
                Base.metadata.tables["provider"],
                Base.metadata.tables["model_config"],
                Base.metadata.tables["provider_health"],
            ]
        )
        now = datetime.now()
        with database.session() as session:
            provider = session.execute(
                Base.metadata.tables["provider"].insert().values(
                    name="Local Provider Config",
                    type=provider_type,
                    base_url=base_url,
                    auth_config={"api_key": api_key},
                    description="provider config bridge test",
                    enabled=True,
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            provider_id = int(provider.inserted_primary_key[0])
            model_config = session.execute(
                Base.metadata.tables["model_config"].insert().values(
                    provider_id=provider_id,
                    name="Provider Config Model",
                    model_id="local/provider-config-model",
                    context_size=4096,
                    extra_params={},
                    enabled=True,
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()
            model_config_id = int(model_config.inserted_primary_key[0])
        yield _ProviderModelConfig(
            database_url=database.database_url,
            model_config_id=model_config_id,
        )


def _provider_config_failure(*, provider_type: str, base_url: str) -> _ProviderConfigFailure:
    with _provider_model_config_db(base_url, api_key=PROVIDER_CONFIG_API_KEY, provider_type=provider_type) as model_config:
        result = run_customer_assistant_live_react_acceptance(
            env={
                "HIFY_RUN_CUSTOMER_ASSISTANT_LIVE_REACT_ACCEPTANCE": "1",
                "HIFY_DATABASE_URL": model_config.database_url,
                "HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_CONFIG_ID": str(model_config.model_config_id),
            },
            output_dir=PROVIDER_CONFIG_ARTIFACT_DIR,
        )
        artifact_text = Path(result.evidence_path or "").read_text(encoding="utf-8")
    return _ProviderConfigFailure(status=result.status, artifact_text=artifact_text)


class _OpenAICompatibleHandler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
        raw_body = self.rfile.read(int(self.headers.get("Content-Length") or "0"))
        request = json.loads(raw_body.decode("utf-8"))
        self.server.calls.append(  # type: ignore[attr-defined]
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "model": request.get("model"),
                "hasTools": bool(request.get("tools")),
            }
        )
        response = _chat_completion_response(request)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))

    def log_message(self, _format: str, *_args: Any) -> None:
        return


def _chat_completion_response(request: dict[str, Any]) -> dict[str, Any]:
    model = str(request.get("model") or "")
    prompt = "\n".join(str(message.get("content") or "") for message in request.get("messages", []))
    if request.get("tools"):
        tool_name = request.get("tool_choice", {}).get("function", {}).get("name") or "lookup_order"
        return _assistant_tool_call(tool_name)
    if model == "xiaomi/mimo-v2-flash" and "task recognition" in prompt:
        return _assistant_content(json.dumps({"bad": True}))
    if "task recognition" in prompt:
        return _assistant_content(
            json.dumps(
                {
                    "commands": [
                        {
                            "type": "ADD_TASK",
                            "taskKey": "baggage_qa",
                            "taskType": "QA",
                            "businessKey": "baggage_qa",
                            "workerType": "stub_qa",
                            "workerRef": "baggage_allowance",
                            "reason": "deterministic_intent",
                        }
                    ],
                    "confidence": 0.95,
                    "warnings": [],
                },
                ensure_ascii=False,
            )
        )
    if "recommendation" in prompt and "Baseline operatorRecommendation:" in prompt:
        return _assistant_content(
            json.dumps(
                {
                    "operatorRecommendation": _between(
                        prompt,
                        "Baseline operatorRecommendation: ",
                        "\nBaseline customerReplyDraft: ",
                    ),
                    "customerReplyDraft": _after(prompt, "Baseline customerReplyDraft: "),
                    "warnings": [],
                    "taskSummaries": [],
                },
                ensure_ascii=False,
            )
        )
    if "Two-Stage ReAct finalization" in prompt:
        baseline = json.loads(_after(prompt, "Baseline final: "))
        return _assistant_content(
            json.dumps(
                {
                    "schemaVersion": "customer_assistant.two_stage_final/1",
                    "operatorRecommendation": baseline["operatorRecommendation"],
                    "customerReplyDraft": baseline["customerReplyDraft"],
                    "warnings": baseline.get("warnings") or [],
                },
                ensure_ascii=False,
            )
        )
    return _assistant_content("{}")


def _assistant_content(content: str) -> dict[str, Any]:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 1},
    }


def _assistant_tool_call(tool_name: str) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": f"call_{tool_name}",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps({"orderNo": "TK-100"}),
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"total_tokens": 1},
    }


def _between(value: str, start: str, end: str) -> str:
    return _after(value, start).split(end, 1)[0]


def _after(value: str, marker: str) -> str:
    return value.split(marker, 1)[1].strip()


if __name__ == "__main__":
    unittest.main()
