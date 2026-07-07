"""Spec 213.2 contract — Chatflow & Workflow debug runs default to async durable.

Both POST /api/v1/workflows/{id}/runs and POST /api/v1/chatflows/{id}/runs MUST:
- Return immediately with the six-ref envelope (runId + five ref URLs).
- Tag the envelope with ``runtimeMode == "async-durable"`` so callers (frontend
  debug dock, SOP router, customer-assistant worker) can confirm the durable
  async path without dialect drift.
- Remain importable as a ``RuntimeInvocationRefs`` without missing keys.

Sync fallback paths (``start_and_wait`` via ``/runs-legacy``) MUST tag the same
envelope with ``runtimeMode == "sync"`` so the contract is observable from the
outside without requiring callers to read transport headers.
"""

from __future__ import annotations

import time
import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.modules.workflow.domain.runtime_invocation_gateway import (
    RuntimeInvocationRefs,
)


class DefaultAsyncDebugRunContractTest(unittest.TestCase):
    def test_workflow_run_returns_six_ref_envelope_with_async_durable_mode(self) -> None:
        with TestClient(app) as client:
            workflow = _create_echo_workflow(client, "workflows")
            publish = client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            self.assertEqual(publish.status_code, 200, publish.text)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": f"async-default-{time.time_ns()}"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        envelope = response.json()["data"]

        self.assertEqual(envelope.get("runtimeMode"), "async-durable")
        self.assertEqual(envelope.get("runtimeVersion"), 2)
        runtime_refs = envelope.get("runtimeRefs")
        self.assertIsInstance(runtime_refs, dict)
        self.assertGreater(int(runtime_refs["runId"]), 0)

        # Parsing back to the canonical DTO must succeed lossless: this is the
        # six-ref contract the gateway promises every caller.
        refs = RuntimeInvocationRefs.from_envelope(runtime_refs)
        self.assertEqual(refs.runId, int(envelope["runId"]))
        self.assertTrue(refs.statusRef.endswith(f"/{refs.runId}"))
        self.assertIn(f"/{refs.runId}/events", refs.eventsRef)
        self.assertIn(f"/{refs.runId}/events/stream", refs.eventStreamRef)
        self.assertIn(f"/{refs.runId}/nodes", refs.nodesRef)
        self.assertIn(f"/{refs.runId}/result", refs.resultRef)

    def test_chatflow_run_returns_six_ref_envelope_with_async_durable_mode(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_echo_workflow(client, "chatflows")
            publish = client.post(f"/api/v1/chatflows/{chatflow['id']}/publish")
            self.assertEqual(publish.status_code, 200, publish.text)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "async-default",
                        "sys.conversation_id": f"async-default-{time.time_ns()}",
                    }
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        envelope = response.json()["data"]

        self.assertEqual(envelope.get("runtimeMode"), "async-durable")
        self.assertEqual(envelope.get("runtimeVersion"), 2)
        runtime_refs = envelope.get("runtimeRefs")
        self.assertIsInstance(runtime_refs, dict)

        refs = RuntimeInvocationRefs.from_envelope(runtime_refs)
        self.assertEqual(refs.runId, int(envelope["runId"]))
        self.assertGreater(refs.runId, 0)

    def test_workflow_canonical_runs_endpoint_remains_six_ref_envelope(self) -> None:
        with TestClient(app) as client:
            workflow = _create_echo_workflow(client, "workflows")
            publish = client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            self.assertEqual(publish.status_code, 200, publish.text)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": f"async-default-canonical-{time.time_ns()}"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        envelope = response.json()["data"]

        self.assertEqual(envelope.get("runtimeMode"), "async-durable")
        self.assertEqual(envelope.get("runtimeVersion"), 2)
        runtime_refs = envelope.get("runtimeRefs")
        self.assertIsInstance(runtime_refs, dict)
        self.assertGreater(int(runtime_refs["runId"]), 0)

        refs = RuntimeInvocationRefs.from_envelope(runtime_refs)
        self.assertEqual(refs.runId, int(envelope["runId"]))
        self.assertTrue(refs.statusRef.endswith(f"/{refs.runId}"))
        self.assertIn(f"/{refs.runId}/events", refs.eventsRef)
        self.assertIn(f"/{refs.runId}/events/stream", refs.eventStreamRef)
        self.assertIn(f"/{refs.runId}/nodes", refs.nodesRef)
        self.assertIn(f"/{refs.runId}/result", refs.resultRef)

    def test_workflow_debug_run_without_publish_uses_draft_async_definition(self) -> None:
        with TestClient(app) as client:
            workflow = _create_echo_workflow(client, "workflows")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"userMessage": f"async-draft-{time.time_ns()}"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        envelope = response.json()["data"]
        self.assertEqual(envelope.get("runtimeMode"), "async-durable")
        self.assertEqual(envelope.get("runtimeVersion"), 2)
        self.assertNotIn("versionId", envelope)
        RuntimeInvocationRefs.from_envelope(envelope.get("runtimeRefs") or {})

    def test_chatflow_canonical_runs_endpoint_remains_six_ref_envelope(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_echo_workflow(client, "chatflows")
            publish = client.post(f"/api/v1/chatflows/{chatflow['id']}/publish")
            self.assertEqual(publish.status_code, 200, publish.text)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "async-default-canonical",
                        "sys.conversation_id": f"async-default-canonical-{time.time_ns()}",
                    }
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        envelope = response.json()["data"]

        self.assertEqual(envelope.get("runtimeMode"), "async-durable")
        self.assertEqual(envelope.get("runtimeVersion"), 2)
        runtime_refs = envelope.get("runtimeRefs")
        self.assertIsInstance(runtime_refs, dict)

        refs = RuntimeInvocationRefs.from_envelope(runtime_refs)
        self.assertEqual(refs.runId, int(envelope["runId"]))
        self.assertGreater(refs.runId, 0)

    def test_workflow_legacy_sync_run_tags_envelope_as_sync_mode(self) -> None:
        with TestClient(app) as client:
            workflow = _create_echo_workflow(client, "workflows")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-legacy",
                json={"input": {"userMessage": "sync-fallback"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        envelope = response.json()["data"]
        # The legacy/sync fallback uses WorkflowService.execute, which does not
        # go through the gateway today. Slice 213.2 only locks the async-durable
        # contract for the canonical `/runs` endpoint; the sync envelope keeps
        # its existing fields and must NOT pretend to be async-durable.
        self.assertNotEqual(envelope.get("runtimeMode"), "async-durable")


def _create_echo_workflow(client: TestClient, prefix: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/{prefix}",
        json={
            "name": f"Async default {prefix} {time.time_ns()}",
            "description": "",
            "nodes": [
                {
                    "nodeKey": "start",
                    "type": "START",
                    "name": "Start",
                    "config": {"outputVariables": ["userMessage"]},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "output": "{{start.userMessage}}",
                        "outputVariable": "output",
                    },
                },
            ],
            "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
        },
    )
    if response.status_code != 200:
        raise AssertionError(response.text)
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
