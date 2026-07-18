import asyncio
import threading
import time
import unittest
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.core.db_write import insert_and_get_id
from app.main import app
from app.modules.knowledge.api.facade import KnowledgeSearchResult
from app.modules.mcp.domain.client import McpCallResult
from app.modules.workflow.domain.runtime_v2 import WorkflowRuntimeV2Service
from app.modules.runtime.domain.runtime_job_worker import RuntimeJobWorker
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.publish_repository import WorkflowPublishRepository
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository


class RuntimeV2ParallelWavesTest(unittest.TestCase):
    def setUp(self) -> None:
        _cleanup_parallel_wave_agent()

    def tearDown(self) -> None:
        _cleanup_parallel_wave_agent()

    def test_workflow_fanout_runs_independent_llm_nodes_in_one_overlapping_wave(self) -> None:
        _seed_parallel_wave_agent()
        provider = _OverlappingAsyncLlmProvider()

        with patch("app.modules.workflow.domain.service.ProviderBackedOpenAIChatClient", lambda _config: provider):
            with TestClient(app) as client:
                workflow = _create_parallel_llm_workflow(client)
                published = client.post(f"/api/v1/workflows/{workflow['id']}/publish")
                self.assertEqual(published.status_code, 200, published.text)
                started = client.post(
                    f"/api/v1/workflows/{workflow['id']}/runs",
                    json={"input": {"sys.query": "parallel wave"}},
                ).json()["data"]
                terminal = _wait_for_terminal(client, str(started["resultRef"]))

        self.assertEqual(terminal["status"], "SUCCEEDED", terminal)
        self.assertTrue(provider.overlapped.is_set(), "independent LLM nodes did not overlap")
        self.assertEqual(provider.async_stream_calls, 2)
        self.assertEqual(terminal["output"], {"final": "parallel: llm_a"})

    def test_workflow_fanout_runs_independent_knowledge_nodes_in_one_overlapping_wave(self) -> None:
        knowledge = _OverlappingKnowledgeFacade()
        with TestClient(app) as client:
            workflow = _create_parallel_knowledge_workflow(client)

        with get_session_factory()() as session:
            runtime = WorkflowRuntimeV2Service(
                WorkflowRepository(session),
                ChatflowStateRepository(session),
                WorkflowPublishRepository(session),
                completion_delay_seconds=0,
                knowledge_facade=knowledge,
            )
            started = runtime.start_run(int(workflow["id"]), {"sys.query": "parallel knowledge wave"})
            runtime.complete_run(int(started["runId"]))
            terminal = runtime.get_result(int(started["runId"]))

        self.assertEqual(terminal["status"], "SUCCEEDED", terminal)
        self.assertTrue(knowledge.overlapped.is_set(), "independent knowledge nodes did not overlap")
        self.assertEqual(knowledge.search_calls, 2)
        self.assertEqual(terminal["output"], {"final": "knowledge: knowledge_a"})

    def test_workflow_fanout_runs_only_receipted_idempotent_tools_in_one_overlapping_wave(self) -> None:
        tools = _ReceiptedParallelToolExecutor()
        with TestClient(app) as client:
            workflow = _create_parallel_safe_tool_workflow(client)

        with get_session_factory()() as session:
            runtime = WorkflowRuntimeV2Service(
                WorkflowRepository(session),
                ChatflowStateRepository(session),
                WorkflowPublishRepository(session),
                completion_delay_seconds=0,
                mcp_tool_executor=tools,
            )
            started = runtime.start_run(int(workflow["id"]), {"sys.query": "parallel tool wave"})
            runtime.complete_run(int(started["runId"]))
            terminal = runtime.get_result(int(started["runId"]))
            nodes = runtime.list_nodes(int(started["runId"]))["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED", terminal)
        self.assertTrue(tools.overlapped.is_set(), "safe tools did not overlap")
        expected_keys = {
            f"runtime-v2:{started['runId']}:tool_a:TOOL_CALL",
            f"runtime-v2:{started['runId']}:tool_b:TOOL_CALL",
        }
        self.assertEqual(set(tools.idempotency_keys), expected_keys)
        for node in nodes:
            if node["nodeKey"] not in {"tool_a", "tool_b"}:
                continue
            evidence = node["outputs"]["evidence"]
            self.assertEqual(evidence["idempotencyKey"], f"runtime-v2:{started['runId']}:{node['nodeKey']}:TOOL_CALL")
            self.assertEqual(evidence["receipt"]["operationId"], evidence["idempotencyKey"])

    def test_parallel_safe_config_without_receipted_adapter_stays_serial(self) -> None:
        tools = _SerialOnlyToolExecutor()
        with TestClient(app) as client:
            workflow = _create_parallel_safe_tool_workflow(client)

        with get_session_factory()() as session:
            runtime = WorkflowRuntimeV2Service(
                WorkflowRepository(session),
                ChatflowStateRepository(session),
                WorkflowPublishRepository(session),
                completion_delay_seconds=0,
                mcp_tool_executor=tools,
            )
            started = runtime.start_run(int(workflow["id"]), {"sys.query": "serial fallback tool wave"})
            runtime.complete_run(int(started["runId"]))
            terminal = runtime.get_result(int(started["runId"]))

        self.assertEqual(terminal["status"], "SUCCEEDED", terminal)
        self.assertEqual(tools.max_active, 1)
        self.assertEqual(tools.call_count, 2)

    def test_worker_takeover_reuses_parallel_safe_tool_operation_key_after_crash(self) -> None:
        tools = _DeduplicatingToolExecutor()
        with TestClient(app) as client:
            workflow = _create_parallel_safe_tool_workflow(client)

        with get_session_factory()() as session:
            crashing_runtime = _CrashAfterParallelToolRuntime(
                WorkflowRepository(session),
                ChatflowStateRepository(session),
                WorkflowPublishRepository(session),
                completion_delay_seconds=0,
                mcp_tool_executor=tools,
            )
            started = crashing_runtime.start_run(int(workflow["id"]), {"sys.query": "crash takeover"})
            run_id = int(started["runId"])
            jobs = RuntimeJobRepository(session)
            job = jobs.enqueue(run_id=run_id, owner_type="WORKFLOW", owner_id=int(workflow["id"]))
            crashed_worker = RuntimeJobWorker(
                job_repository=jobs,
                complete_run=crashing_runtime.complete_run,
                worker_id="parallel-tool-crashed-worker",
                owner_types=("WORKFLOW",),
            )
            with self.assertRaises(SystemExit):
                crashed_worker.run_once(job_id=int(job["id"]))

            job_table = Base.metadata.tables["runtime_jobs"]
            session.execute(
                job_table.update()
                .where(job_table.c.id == int(job["id"]))
                .values(lease_expires_at=datetime.now() - timedelta(seconds=1))
            )
            session.commit()
            takeover_runtime = WorkflowRuntimeV2Service(
                WorkflowRepository(session),
                ChatflowStateRepository(session),
                WorkflowPublishRepository(session),
                completion_delay_seconds=0,
                mcp_tool_executor=tools,
            )
            takeover_worker = RuntimeJobWorker(
                job_repository=jobs,
                complete_run=takeover_runtime.complete_run,
                worker_id="parallel-tool-takeover-worker",
                owner_types=("WORKFLOW",),
            )
            takeover = takeover_worker.run_once(job_id=int(job["id"]))
            terminal = takeover_runtime.get_result(run_id)

        expected_keys = {
            f"runtime-v2:{run_id}:tool_a:TOOL_CALL",
            f"runtime-v2:{run_id}:tool_b:TOOL_CALL",
        }
        self.assertEqual(takeover["status"], "COMPLETED")
        self.assertEqual(terminal["status"], "SUCCEEDED", terminal)
        self.assertEqual(set(tools.side_effect_operation_keys), expected_keys)
        self.assertGreaterEqual(tools.idempotency_keys.count(f"runtime-v2:{run_id}:tool_a:TOOL_CALL"), 2)
        self.assertTrue(set(tools.idempotency_keys).issubset(expected_keys))

    def test_parallel_llm_timeout_fails_run_without_waiting_for_cancellable_peers(self) -> None:
        completer = _WaveCancellableLlmCompleter()
        with TestClient(app) as client:
            workflow = _create_parallel_timeout_llm_workflow(client)

        with get_session_factory()() as session:
            runtime = WorkflowRuntimeV2Service(
                WorkflowRepository(session),
                ChatflowStateRepository(session),
                WorkflowPublishRepository(session),
                completion_delay_seconds=0,
                llm_completer=completer,
            )
            started = runtime.start_run(int(workflow["id"]), {"sys.query": "timeout wave"})
            started_at = time.monotonic()
            runtime.complete_run(int(started["runId"]))
            elapsed = time.monotonic() - started_at
            terminal = runtime.get_result(int(started["runId"]))
            events = runtime.list_events(int(started["runId"]))["list"]

        self.assertEqual(terminal["status"], "FAILED", terminal)
        expected_failure = {
            "code": "WORKFLOW_NODE_TIMEOUT",
            "kind": "timeout",
            "message": "A workflow node timed out.",
            "runId": int(started["runId"]),
            "nodeKey": "timeout_a",
            "nodeType": "LLM",
            "retryable": False,
        }
        self.assertEqual(terminal["errorCode"], "WORKFLOW_NODE_TIMEOUT")
        self.assertEqual(terminal["failure"], expected_failure)
        run_failure = next(event for event in events if event["type"] == "workflow_run_failed")
        self.assertEqual(run_failure["payload"]["failure"], expected_failure)
        self.assertLess(elapsed, 0.35, f"timeout was not fail-fast: {elapsed:.3f}s")
        self.assertTrue(completer.cancelled.wait(timeout=1), "cancellable LLM peers did not receive cancellation")

    def test_timeout_fences_late_blocking_knowledge_result_after_terminal_failure(self) -> None:
        completer = _WaveCancellableLlmCompleter(expected_cancellations=1)
        knowledge = _LateBlockingKnowledgeFacade()
        with TestClient(app) as client:
            workflow = _create_timeout_with_blocking_knowledge_workflow(client)

        with get_session_factory()() as session:
            runtime = WorkflowRuntimeV2Service(
                WorkflowRepository(session),
                ChatflowStateRepository(session),
                WorkflowPublishRepository(session),
                completion_delay_seconds=0,
                llm_completer=completer,
                knowledge_facade=knowledge,
            )
            started = runtime.start_run(int(workflow["id"]), {"sys.query": "fence late knowledge"})
            runtime.complete_run(int(started["runId"]))
            terminal = runtime.get_result(int(started["runId"]))
            before_release = runtime.list_nodes(int(started["runId"]))["list"]
            knowledge.release.set()
            self.assertTrue(knowledge.finished.wait(timeout=1), "blocking knowledge call did not return")
            time.sleep(0.05)
            after_release = runtime.list_nodes(int(started["runId"]))["list"]
            events = runtime.list_events(int(started["runId"]))["list"]

        self.assertEqual(terminal["status"], "FAILED", terminal)
        before_statuses = {node["nodeKey"]: node["status"] for node in before_release}
        after_statuses = {node["nodeKey"]: node["status"] for node in after_release}
        self.assertEqual(before_statuses["timeout_llm"], "FAILED")
        self.assertEqual(before_statuses["late_knowledge"], "CANCELLED")
        self.assertEqual(after_statuses["late_knowledge"], "CANCELLED")
        self.assertFalse(
            any(event["type"] == "workflow_node_completed" and event.get("nodeId") == "late_knowledge" for event in events),
            events,
        )

    def test_timeout_fences_delta_that_passed_callback_check_before_terminal_failure(self) -> None:
        release_delta = threading.Event()
        completer = _DeltaRaceLlmCompleter(release_delta)
        with TestClient(app) as client:
            workflow = _create_parallel_timeout_llm_workflow(client)

        with get_session_factory()() as session:
            runtime = _DelayedDeltaFenceRuntime(
                WorkflowRepository(session),
                ChatflowStateRepository(session),
                WorkflowPublishRepository(session),
                completion_delay_seconds=0,
                llm_completer=completer,
                release_delta=release_delta,
            )
            started = runtime.start_run(int(workflow["id"]), {"sys.query": "delta fence race"})
            runtime.complete_run(int(started["runId"]))
            terminal = runtime.get_result(int(started["runId"]))
            self.assertTrue(runtime.delta_entered.wait(timeout=0.5), "LLM delta never passed its pre-check")
            release_delta.set()
            self.assertTrue(runtime.delta_finished.wait(timeout=1), "late LLM delta did not finish")
            self.assertTrue(completer.delta_returned.wait(timeout=1), "LLM delta callback did not return")
            session.rollback()
            events = runtime.list_events(int(started["runId"]))["list"]

        self.assertEqual(terminal["status"], "FAILED", terminal)
        self.assertIsNone(runtime.delta_error)
        self.assertFalse(
            any(event["type"] == "llm_delta" and event["payload"].get("content") == "late delta" for event in events),
            events,
        )


class _OverlappingAsyncLlmProvider:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._both_started = threading.Event()
        self.overlapped = threading.Event()
        self.async_stream_calls = 0

    async def stream_complete_async(self, payload: dict[str, Any], on_delta=None) -> dict[str, Any]:
        prompt = str((payload.get("messages") or [{}])[-1].get("content") or "")
        with self._lock:
            self.async_stream_calls += 1
            call_number = self.async_stream_calls
            if call_number == 2:
                self.overlapped.set()
                self._both_started.set()
        if not await asyncio.to_thread(self._both_started.wait, 0.35):
            raise AssertionError("second independent LLM did not start before the first completed")
        node_key = "llm_a" if "llm_a" in prompt else "llm_b"
        content = f"parallel: {node_key}"
        if on_delta is not None:
            on_delta(content)
        return _assistant_payload(content)


class _OverlappingKnowledgeFacade:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._both_started = threading.Event()
        self.overlapped = threading.Event()
        self.search_calls = 0

    def search_chunks(
        self,
        _knowledge_base_id: int,
        query: str,
        *,
        top_k: int,
        retrieval_mode: str | None,
        score_threshold: float | None,
        rerank: bool,
    ) -> list[KnowledgeSearchResult]:
        del top_k, retrieval_mode, score_threshold, rerank
        with self._lock:
            self.search_calls += 1
            call_number = self.search_calls
            if call_number == 2:
                self.overlapped.set()
                self._both_started.set()
        if not self._both_started.wait(0.35):
            raise AssertionError("second independent knowledge node did not start before the first completed")
        node_key = "knowledge_a" if "knowledge_a" in query else "knowledge_b"
        return [
            KnowledgeSearchResult(
                chunk_id=1,
                document_id=1,
                chunk_index=0,
                content=f"knowledge: {node_key}",
                token_count=1,
                score=1.0,
            )
        ]


class _ReceiptedParallelToolExecutor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._both_started = threading.Event()
        self.overlapped = threading.Event()
        self.idempotency_keys: list[str] = []

    def execute_tool_call(self, *_args: object, **_kwargs: object) -> McpCallResult:
        raise AssertionError("parallel-safe Tool must receive idempotency before dispatch")

    def execute_tool_call_idempotent(
        self,
        _server_ids: list[int],
        tool_name: str,
        _arguments: dict[str, object],
        *,
        idempotency_key: str,
    ) -> tuple[McpCallResult, dict[str, str]]:
        with self._lock:
            self.idempotency_keys.append(idempotency_key)
            if len(self.idempotency_keys) == 2:
                self.overlapped.set()
                self._both_started.set()
        if not self._both_started.wait(0.35):
            raise AssertionError("second safe Tool did not start before the first completed")
        return (
            McpCallResult(success=True, result=f"tool: {tool_name}", elapsed_ms=1),
            {"operationId": idempotency_key},
        )


class _SerialOnlyToolExecutor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.call_count = 0
        self.max_active = 0
        self._active = 0

    def execute_tool_call(
        self,
        _server_ids: list[int],
        tool_name: str,
        _arguments: dict[str, object],
    ) -> McpCallResult:
        with self._lock:
            self.call_count += 1
            self._active += 1
            self.max_active = max(self.max_active, self._active)
        try:
            time.sleep(0.05)
            return McpCallResult(success=True, result=f"serial: {tool_name}", elapsed_ms=50)
        finally:
            with self._lock:
                self._active -= 1


class _DeduplicatingToolExecutor:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.idempotency_keys: list[str] = []
        self.side_effect_operation_keys: list[str] = []

    def execute_tool_call_idempotent(
        self,
        _server_ids: list[int],
        tool_name: str,
        _arguments: dict[str, object],
        *,
        idempotency_key: str,
    ) -> tuple[McpCallResult, dict[str, str]]:
        with self._lock:
            self.idempotency_keys.append(idempotency_key)
            if idempotency_key not in self.side_effect_operation_keys:
                self.side_effect_operation_keys.append(idempotency_key)
        return (
            McpCallResult(success=True, result=f"tool: {tool_name}", elapsed_ms=1),
            {"operationId": idempotency_key},
        )


class _CrashAfterParallelToolRuntime(WorkflowRuntimeV2Service):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._crash_once = True

    def _complete_prestarted_node_success(self, **kwargs: Any) -> dict[str, Any]:
        node = kwargs["node"]
        if self._crash_once and str(node["node_key"]) == "tool_a":
            self._crash_once = False
            raise SystemExit("simulated worker crash after tool provider accepted operation")
        return super()._complete_prestarted_node_success(**kwargs)


class _WaveCancellableLlmCompleter:
    def __init__(self, *, expected_cancellations: int = 2) -> None:
        self._lock = threading.Lock()
        self._cancellation_check = None
        self._cancelled_nodes: set[str] = set()
        self._expected_cancellations = expected_cancellations
        self.cancelled = threading.Event()

    def set_cancellation_check(self, cancellation_check) -> None:
        self._cancellation_check = cancellation_check

    def stream_prompt(self, prompt: str, _options: dict[str, Any], _on_delta) -> str:
        node_key = "timeout_a" if "timeout_a" in prompt else "timeout_b"
        deadline = time.monotonic() + 0.5
        while time.monotonic() < deadline:
            if self._cancellation_check is not None and self._cancellation_check():
                with self._lock:
                    self._cancelled_nodes.add(node_key)
                    if len(self._cancelled_nodes) == self._expected_cancellations:
                        self.cancelled.set()
                raise RuntimeError(f"{node_key} observed wave cancellation")
            time.sleep(0.01)
        raise AssertionError("timeout controller did not cancel the LLM wave")

    def complete_prompt(self, _prompt: str, _options: dict[str, Any] | None = None) -> str:
        raise AssertionError("parallel timeout test requires streaming completion")

    def supports_tool_calls(self) -> bool:
        return False


class _DelayedDeltaFenceRuntime(WorkflowRuntimeV2Service):
    def __init__(self, *args: Any, release_delta: threading.Event, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.delta_entered = threading.Event()
        self.delta_finished = threading.Event()
        self.delta_error: Exception | None = None
        self._release_delta = release_delta

    def _append_live_llm_delta(self, **kwargs: Any) -> None:
        self.delta_entered.set()
        self._release_delta.wait(timeout=1)
        try:
            super()._append_live_llm_delta(**kwargs)
        except Exception as exc:
            self.delta_error = exc
            raise
        finally:
            self.delta_finished.set()


class _DeltaRaceLlmCompleter:
    def __init__(self, release_delta: threading.Event) -> None:
        self._release_delta = release_delta
        self.delta_returned = threading.Event()

    def stream_prompt(self, prompt: str, _options: dict[str, Any], on_delta) -> str:
        if "timeout_a" in prompt:
            on_delta("late delta")
            self.delta_returned.set()
            return "late delta result"
        self._release_delta.wait(timeout=1)
        return "peer result"

    def complete_prompt(self, _prompt: str, _options: dict[str, Any] | None = None) -> str:
        raise AssertionError("delta race test requires streaming completion")

    def supports_tool_calls(self) -> bool:
        return False


class _LateBlockingKnowledgeFacade:
    def __init__(self) -> None:
        self.release = threading.Event()
        self.finished = threading.Event()

    def search_chunks(
        self,
        _knowledge_base_id: int,
        _query: str,
        *,
        top_k: int,
        retrieval_mode: str | None,
        score_threshold: float | None,
        rerank: bool,
    ) -> list[KnowledgeSearchResult]:
        del top_k, retrieval_mode, score_threshold, rerank
        try:
            self.release.wait(timeout=1)
            return [
                KnowledgeSearchResult(
                    chunk_id=1,
                    document_id=1,
                    chunk_index=0,
                    content="late knowledge result",
                    token_count=1,
                    score=1.0,
                )
            ]
        finally:
            self.finished.set()


def _assistant_payload(content: str) -> dict[str, Any]:
    return {
        "model": "runtime-v2-parallel-wave-model",
        "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def _create_parallel_llm_workflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Parallel LLM Wave {time.time_ns()}",
            "description": "independent ready LLM nodes overlap in one Runtime V2 wave",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"ports": [{"key": "default", "allowFanOut": True}]},
                },
                {
                    "nodeKey": "llm_a",
                    "type": "LLM",
                    "name": "LLM A",
                    "config": {"prompt": "llm_a: {{start.sys.query}}", "outputVariable": "answer"},
                },
                {
                    "nodeKey": "llm_b",
                    "type": "LLM",
                    "name": "LLM B",
                    "config": {"prompt": "llm_b: {{start.sys.query}}", "outputVariable": "answer"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{llm_a.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "llm_a", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "llm_b", "condition": None},
                {"sourceNodeKey": "llm_a", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "llm_b", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_parallel_knowledge_workflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Parallel Knowledge Wave {time.time_ns()}",
            "description": "independent ready knowledge nodes overlap in one Runtime V2 wave",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"ports": [{"key": "default", "allowFanOut": True}]},
                },
                {
                    "nodeKey": "knowledge_a",
                    "type": "KNOWLEDGE",
                    "name": "Knowledge A",
                    "config": {
                        "knowledgeBaseId": 1,
                        "query": "knowledge_a: {{start.sys.query}}",
                        "topK": 1,
                        "outputVariable": "answer",
                    },
                },
                {
                    "nodeKey": "knowledge_b",
                    "type": "KNOWLEDGE",
                    "name": "Knowledge B",
                    "config": {
                        "knowledgeBaseId": 1,
                        "query": "knowledge_b: {{start.sys.query}}",
                        "topK": 1,
                        "outputVariable": "answer",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{knowledge_a.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "knowledge_a", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "knowledge_b", "condition": None},
                {"sourceNodeKey": "knowledge_a", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "knowledge_b", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_parallel_safe_tool_workflow(client: TestClient) -> dict[str, Any]:
    tool_config = {
        "resourceType": "MCP_TOOL",
        "resourceId": "mcp:1:safe_lookup",
        "serverIds": [1],
        "parallelSafe": True,
        "outputParameters": [
            {"name": "result", "type": "string"},
            {"name": "success", "type": "boolean"},
            {"name": "evidence", "type": "object"},
        ],
    }
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Parallel Safe Tool Wave {time.time_ns()}",
            "description": "only receipted idempotent safe tools may overlap",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"ports": [{"key": "default", "allowFanOut": True}]},
                },
                {
                    "nodeKey": "tool_a",
                    "type": "TOOL_CALL",
                    "name": "Safe Tool A",
                    "config": {**tool_config, "toolName": "safe_lookup_a"},
                },
                {
                    "nodeKey": "tool_b",
                    "type": "TOOL_CALL",
                    "name": "Safe Tool B",
                    "config": {**tool_config, "toolName": "safe_lookup_b"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{tool_a.result}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "tool_a", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "tool_b", "condition": None},
                {"sourceNodeKey": "tool_a", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "tool_b", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_parallel_timeout_llm_workflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Parallel Timeout LLM Wave {time.time_ns()}",
            "description": "per-node timeout fails a cancellable LLM wave promptly",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"ports": [{"key": "default", "allowFanOut": True}]},
                },
                {
                    "nodeKey": "timeout_a",
                    "type": "LLM",
                    "name": "Timeout A",
                    "config": {
                        "prompt": "timeout_a: {{start.sys.query}}",
                        "outputVariable": "answer",
                        "model": "runtime-v2-timeout-wave-model",
                        "timeoutMs": 80,
                    },
                },
                {
                    "nodeKey": "timeout_b",
                    "type": "LLM",
                    "name": "Timeout B",
                    "config": {
                        "prompt": "timeout_b: {{start.sys.query}}",
                        "outputVariable": "answer",
                        "model": "runtime-v2-timeout-wave-model",
                        "timeoutMs": 80,
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{timeout_a.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "timeout_a", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "timeout_b", "condition": None},
                {"sourceNodeKey": "timeout_a", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "timeout_b", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_timeout_with_blocking_knowledge_workflow(client: TestClient) -> dict[str, Any]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Timeout Fencing Wave {time.time_ns()}",
            "description": "late blocking knowledge cannot commit after timeout",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"ports": [{"key": "default", "allowFanOut": True}]},
                },
                {
                    "nodeKey": "timeout_llm",
                    "type": "LLM",
                    "name": "Timeout LLM",
                    "config": {
                        "prompt": "timeout_llm: {{start.sys.query}}",
                        "outputVariable": "answer",
                        "model": "runtime-v2-timeout-fence-model",
                        "timeoutMs": 80,
                    },
                },
                {
                    "nodeKey": "late_knowledge",
                    "type": "KNOWLEDGE",
                    "name": "Late Knowledge",
                    "config": {
                        "knowledgeBaseId": 1,
                        "query": "{{start.sys.query}}",
                        "topK": 1,
                        "outputVariable": "answer",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{late_knowledge.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "timeout_llm", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "late_knowledge", "condition": None},
                {"sourceNodeKey": "timeout_llm", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "late_knowledge", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _wait_for_terminal(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "CANCELLED", "INTERRUPTED"}:
            return latest
        time.sleep(0.05)
    raise AssertionError(f"Timed out waiting for terminal result: {latest}")


def _seed_parallel_wave_agent() -> None:
    now = datetime.now()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    with get_session_factory()() as session:
        provider_id = insert_and_get_id(
            session,
            provider,
            {
                "name": f"Runtime V2 Parallel Wave Provider {time.time_ns()}",
                "type": "OPENAI",
                "base_url": "https://runtime-v2-parallel-wave.example.test/v1",
                "auth_config": {"api_key": "parallel-wave-test-key"},
                "description": "",
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
                "name": "runtime-v2-parallel-wave-model",
                "model_id": "runtime-v2-parallel-wave-model",
                "context_size": 128000,
                "extra_params": {},
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        insert_and_get_id(
            session,
            agent,
            {
                "name": f"Runtime V2 Parallel Wave Agent {time.time_ns()}",
                "description": "",
                "system_prompt": "You are a Runtime V2 parallel-wave test agent.",
                "model_config_id": model_config_id,
                "temperature": 0.0,
                "max_tokens": 16,
                "max_context_turns": 1,
                "opening_message": "",
                "suggested_questions": [],
                "workflow_id": None,
                "enabled": True,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        session.commit()


def _cleanup_parallel_wave_agent() -> None:
    now = datetime.now()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    with get_session_factory()() as session:
        session.execute(
            agent.update()
            .where(agent.c.name.like("Runtime V2 Parallel Wave Agent %"))
            .values(deleted=True, enabled=False, updated_at=now)
        )
        session.execute(
            model_config.update()
            .where(model_config.c.model_id == "runtime-v2-parallel-wave-model")
            .values(deleted=True, enabled=False, updated_at=now)
        )
        session.execute(
            provider.update()
            .where(provider.c.name.like("Runtime V2 Parallel Wave Provider %"))
            .values(deleted=True, enabled=False, updated_at=now)
        )
        session.commit()
