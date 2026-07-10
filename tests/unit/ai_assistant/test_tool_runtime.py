import importlib
import importlib.util
import time
import unittest
from typing import Any


def _load_runtime():
    module_name = "app.modules.ai_assistant.domain.tool_runtime"
    if importlib.util.find_spec(module_name) is None:
        raise AssertionError("ToolRuntime module is missing: app.modules.ai_assistant.domain.tool_runtime")
    return importlib.import_module(module_name)


def _manifest(name: str, *, timeout_ms: int = 100, risk_level=None):
    from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest

    return ToolManifest(
        name=name,
        description=f"{name} test tool",
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        timeout_ms=timeout_ms,
        risk_level=risk_level or RiskLevel.READ,
        read_resources=[],
        write_resources=[],
        policy_ref="test_policy",
    )


class AiAssistantToolRuntimeTest(unittest.TestCase):
    def test_runner_retries_with_backoff_jitter_and_records_idempotency_budget_and_span(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry, ToolResult

        runtime = _load_runtime()
        calls: list[dict[str, Any]] = []
        sleeps: list[float] = []

        def flaky(payload: dict[str, Any]) -> ToolResult:
            calls.append(payload)
            if len(calls) < 3:
                raise RuntimeError("simulated 5xx")
            return ToolResult(status="COMPLETED", output={"ok": True, "attempt": len(calls)})

        registry = ToolRegistry({"unstable_tool": (_manifest("unstable_tool"), flaky)})
        runner = runtime.ToolRunner(
            registry,
            policy=runtime.ToolRunnerPolicy(
                max_attempts=3,
                initial_backoff_ms=10,
                backoff_multiplier=2.0,
                jitter_ms=5,
            ),
            sleep=sleeps.append,
            jitter=lambda: 0.005,
        )

        result = runner.run("unstable_tool", {"caseId": "retry"}, idempotency_key="idem-retry")

        self.assertEqual(result.tool_result.status, "COMPLETED")
        self.assertEqual(result.tool_result.output["attempt"], 3)
        self.assertEqual(result.attempts, 3)
        self.assertEqual(result.idempotency_key, "idem-retry")
        self.assertEqual(result.budget["attempts"], 3)
        self.assertEqual(result.span["toolName"], "unstable_tool")
        self.assertEqual(result.span["status"], "OK")
        self.assertEqual(len(sleeps), 2)
        self.assertGreater(sleeps[0], 0.009)
        self.assertGreater(sleeps[1], sleeps[0])
        self.assertIn("tool.retry_scheduled", [event["type"] for event in result.events])

    def test_runner_timeout_returns_structured_model_observation(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry, ToolResult

        runtime = _load_runtime()

        def slow(_payload: dict[str, Any]) -> ToolResult:
            time.sleep(0.05)
            return ToolResult(status="COMPLETED", output={"late": True})

        from app.modules.ai_assistant.domain.tools import RiskLevel

        registry = ToolRegistry(
            {"slow_tool": (_manifest("slow_tool", timeout_ms=1, risk_level=RiskLevel.BUSINESS_WRITE), slow)}
        )
        runner = runtime.ToolRunner(
            registry,
            policy=runtime.ToolRunnerPolicy(max_attempts=1),
            sleep=lambda _seconds: None,
        )

        result = runner.run("slow_tool", {"caseId": "timeout"}, idempotency_key="idem-timeout")

        observation = result.tool_result.output["observation"]
        self.assertEqual(result.tool_result.status, "FAILED")
        self.assertEqual(observation["kind"], "tool_error")
        self.assertEqual(observation["toolName"], "slow_tool")
        self.assertEqual(observation["error"]["code"], "TOOL_TIMEOUT")
        self.assertTrue(observation["modelVisible"])
        self.assertEqual(result.span["status"], "ERROR")
        self.assertIn("tool.error_observation", [event["type"] for event in result.events])

    def test_read_timeout_does_not_create_unknown_block_and_cache_is_expirable(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry, ToolResult

        runtime = _load_runtime()
        calls = {"count": 0}

        def eventually_fast(_payload: dict[str, Any]) -> ToolResult:
            calls["count"] += 1
            if calls["count"] == 1:
                time.sleep(0.05)
            return ToolResult(status="COMPLETED", output={"call": calls["count"]})

        registry = ToolRegistry({"read_tool": (_manifest("read_tool", timeout_ms=1), eventually_fast)})
        runner = runtime.ToolRunner(
            registry,
            policy=runtime.ToolRunnerPolicy(max_attempts=1, read_cache_seconds=0),
            sleep=lambda _seconds: None,
        )

        first = runner.run("read_tool", {"caseId": "read-timeout"}, idempotency_key="read-timeout-key")
        second = runner.run("read_tool", {"caseId": "read-timeout"}, idempotency_key="read-timeout-key")
        third = runner.run("read_tool", {"caseId": "read-timeout"}, idempotency_key="read-timeout-key")

        self.assertEqual(first.tool_result.output["error"]["code"], "TOOL_TIMEOUT")
        self.assertEqual(second.tool_result.output, {"call": 2})
        self.assertEqual(third.tool_result.output, {"call": 3})
        self.assertEqual(calls["count"], 3)

    def test_runner_retries_rate_limit_errors_with_backoff_observation(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        runtime = _load_runtime()
        calls = {"count": 0}

        def rate_limited(_payload: dict[str, Any]) -> None:
            calls["count"] += 1
            raise RuntimeError("rate limit exceeded")

        registry = ToolRegistry({"rate_limited_tool": (_manifest("rate_limited_tool"), rate_limited)})
        runner = runtime.ToolRunner(
            registry,
            policy=runtime.ToolRunnerPolicy(max_attempts=2, initial_backoff_ms=1, jitter_ms=0),
            sleep=lambda _seconds: None,
        )

        result = runner.run("rate_limited_tool", {"caseId": "rate-limit"}, idempotency_key="idem-rate")
        event_types = [event["type"] for event in result.events]

        self.assertEqual(calls["count"], 2)
        self.assertEqual(result.tool_result.output["error"]["code"], "TOOL_RATE_LIMIT")
        self.assertIn("tool.retry_scheduled", event_types)
        self.assertIn("tool.error_observation", event_types)
        self.assertIn("retry_with_backoff", result.tool_result.output["observation"]["suggestedActions"])

    def test_runner_does_not_retry_or_fallback_after_timeout_when_completion_is_unknown(self) -> None:
        from app.modules.ai_assistant.domain.tools import RiskLevel, ToolRegistry, ToolResult

        runtime = _load_runtime()
        calls: list[dict[str, Any]] = []
        fallback_calls: list[dict[str, Any]] = []

        def slow(payload: dict[str, Any]) -> ToolResult:
            calls.append(payload)
            time.sleep(0.05)
            return ToolResult(status="COMPLETED", output={"late": True})

        def fallback(tool_name: str, payload: dict[str, Any], error: dict[str, Any]) -> ToolResult:
            fallback_calls.append({"toolName": tool_name, "payload": payload, "error": error})
            return ToolResult(status="COMPLETED", output={"fallback": True})

        registry = ToolRegistry(
            {"slow_tool": (_manifest("slow_tool", timeout_ms=1, risk_level=RiskLevel.BUSINESS_WRITE), slow)}
        )
        runner = runtime.ToolRunner(
            registry,
            policy=runtime.ToolRunnerPolicy(max_attempts=3, initial_backoff_ms=1),
            fallback_adapters={"slow_tool": fallback},
            sleep=lambda _seconds: None,
        )

        result = runner.run("slow_tool", {"caseId": "timeout-no-retry"}, idempotency_key="idem-timeout-no-retry")

        event_types = [event["type"] for event in result.events]
        self.assertEqual(result.attempts, 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(fallback_calls, [])
        self.assertNotIn("tool.retry_scheduled", event_types)
        self.assertNotIn("tool.fallback_used", event_types)
        self.assertEqual(result.tool_result.output["observation"]["error"]["code"], "TOOL_TIMEOUT")

    def test_runner_passes_and_enforces_idempotency_key(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry, ToolResult

        runtime = _load_runtime()
        seen_payloads: list[dict[str, Any]] = []

        def idempotent(payload: dict[str, Any]) -> ToolResult:
            seen_payloads.append(payload)
            return ToolResult(status="COMPLETED", output={"seenKey": payload["_toolRuntime"]["idempotencyKey"]})

        registry = ToolRegistry({"idempotent_tool": (_manifest("idempotent_tool"), idempotent)})
        runner = runtime.ToolRunner(registry, policy=runtime.ToolRunnerPolicy(max_attempts=1))

        first = runner.run("idempotent_tool", {"caseId": "idem"}, idempotency_key="idem-key-1")
        second = runner.run("idempotent_tool", {"caseId": "idem"}, idempotency_key="idem-key-1")

        self.assertEqual(first.tool_result.output["seenKey"], "idem-key-1")
        self.assertEqual(second.tool_result.output["seenKey"], "idem-key-1")
        self.assertEqual(len(seen_payloads), 1)
        self.assertEqual(seen_payloads[0]["_toolRuntime"]["attempt"], 1)
        self.assertIn("tool.idempotency_replayed", [event["type"] for event in second.events])

    def test_runner_opens_circuit_after_repeated_failures(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        runtime = _load_runtime()
        calls: list[dict[str, Any]] = []

        def broken(payload: dict[str, Any]):
            calls.append(payload)
            raise RuntimeError("still failing")

        registry = ToolRegistry({"broken_tool": (_manifest("broken_tool"), broken)})
        runner = runtime.ToolRunner(
            registry,
            policy=runtime.ToolRunnerPolicy(max_attempts=1, circuit_failure_threshold=2),
            sleep=lambda _seconds: None,
        )

        runner.run("broken_tool", {"caseId": "one"})
        runner.run("broken_tool", {"caseId": "two"})
        third = runner.run("broken_tool", {"caseId": "three"})

        observation = third.tool_result.output["observation"]
        self.assertEqual(len(calls), 2)
        self.assertEqual(third.attempts, 0)
        self.assertEqual(observation["error"]["code"], "TOOL_CIRCUIT_OPEN")
        self.assertIn("tool.circuit_open", [event["type"] for event in third.events])

    def test_runner_uses_fallback_adapter_after_primary_failure(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry, ToolResult

        runtime = _load_runtime()

        def primary(_payload: dict[str, Any]) -> ToolResult:
            raise RuntimeError("primary unavailable")

        def fallback(tool_name: str, payload: dict[str, Any], error: dict[str, Any]) -> ToolResult:
            return ToolResult(
                status="COMPLETED",
                output={"fallback": True, "toolName": tool_name, "caseId": payload["caseId"], "sourceError": error["code"]},
            )

        registry = ToolRegistry({"primary_tool": (_manifest("primary_tool"), primary)})
        runner = runtime.ToolRunner(
            registry,
            policy=runtime.ToolRunnerPolicy(max_attempts=1),
            fallback_adapters={"primary_tool": fallback},
            sleep=lambda _seconds: None,
        )

        result = runner.run("primary_tool", {"caseId": "fallback"})

        self.assertEqual(result.tool_result.status, "COMPLETED")
        self.assertTrue(result.tool_result.output["fallback"])
        self.assertEqual(result.tool_result.output["sourceError"], "TOOL_RUNTIME_ERROR")
        self.assertTrue(result.span["fallback"])
        self.assertIn("tool.fallback_used", [event["type"] for event in result.events])


if __name__ == "__main__":
    unittest.main()
