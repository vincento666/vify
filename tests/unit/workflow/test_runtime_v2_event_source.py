"""Spec 213.3.5h — CHATFLOW-owned runtime v2 events tag source as chatflow_runtime_v2.

Events appended via _append_event carry an explicit source, but the
_format_runtime_event and normalize_runtime_stream_event fallbacks are
hardcoded to 'runtime_v2'. When an event payload lacks an explicit
source (or a stream frame is normalized from a DB row), the fallback
must derive the source from the payload's ownerType field so
CHATFLOW-owned runs emit 'chatflow_runtime_v2' and WORKFLOW-owned runs
emit 'workflow_runtime_v2'.
"""

import unittest

from app.modules.workflow.domain.runtime_v2 import _format_runtime_event
from app.modules.workflow.infra.chatflow_state_repository import _chatflow_event_payload
from app.modules.workflow.infra.realtime.redis_streams import (
    normalize_runtime_stream_event,
)


class RuntimeV2EventSourceTaggingTest(unittest.TestCase):
    def test_format_runtime_event_falls_back_to_chatflow_runtime_v2_from_owner_type(self) -> None:
        event = {
            "id": 1,
            "run_id": 100,
            "sequence": 1,
            "event_type": "workflow_run_started",
            "node_key": "",
            "payload": {"ownerType": "CHATFLOW", "level": "L1"},
            "checkpoint_id": None,
            "created_at": "2026-07-01T00:00:00",
        }
        formatted = _format_runtime_event(event)
        self.assertEqual(formatted["source"], "chatflow_runtime_v2")

    def test_format_runtime_event_falls_back_to_workflow_runtime_v2_for_workflow_owner(self) -> None:
        event = {
            "id": 2,
            "run_id": 200,
            "sequence": 1,
            "event_type": "workflow_run_started",
            "node_key": "",
            "payload": {"ownerType": "WORKFLOW", "level": "L1"},
            "checkpoint_id": None,
            "created_at": "2026-07-01T00:00:00",
        }
        formatted = _format_runtime_event(event)
        self.assertEqual(formatted["source"], "workflow_runtime_v2")

    def test_format_runtime_event_preserves_explicit_source_over_fallback(self) -> None:
        event = {
            "id": 3,
            "run_id": 300,
            "sequence": 1,
            "event_type": "workflow_run_started",
            "node_key": "",
            "payload": {"source": "custom_source", "ownerType": "CHATFLOW"},
            "checkpoint_id": None,
            "created_at": "2026-07-01T00:00:00",
        }
        formatted = _format_runtime_event(event)
        self.assertEqual(formatted["source"], "custom_source")

    def test_normalize_runtime_stream_event_falls_back_to_chatflow_runtime_v2(self) -> None:
        event = {
            "id": 1,
            "runId": 100,
            "sequence": 1,
            "type": "workflow_run_started",
            "payload": {"ownerType": "CHATFLOW"},
        }
        normalized = normalize_runtime_stream_event(event)
        self.assertEqual(normalized["source"], "chatflow_runtime_v2")

    def test_normalize_runtime_stream_event_falls_back_to_workflow_runtime_v2(self) -> None:
        event = {
            "id": 2,
            "runId": 200,
            "sequence": 1,
            "type": "workflow_run_started",
            "payload": {"ownerType": "WORKFLOW"},
        }
        normalized = normalize_runtime_stream_event(event)
        self.assertEqual(normalized["source"], "workflow_runtime_v2")

    def test_normalize_preserves_explicit_source_over_fallback(self) -> None:
        event = {
            "id": 3,
            "runId": 300,
            "sequence": 1,
            "type": "workflow_run_started",
            "source": "custom_source",
            "payload": {"ownerType": "CHATFLOW"},
        }
        normalized = normalize_runtime_stream_event(event)
        self.assertEqual(normalized["source"], "custom_source")

    def test_chatflow_state_repository_payload_defaults_to_chatflow_runtime_v2(self) -> None:
        payload = _chatflow_event_payload({"content": "hello"})

        self.assertEqual(payload["ownerType"], "CHATFLOW")
        self.assertEqual(payload["source"], "chatflow_runtime_v2")

    def test_chatflow_state_repository_payload_preserves_explicit_source(self) -> None:
        payload = _chatflow_event_payload({"source": "custom_source", "ownerType": "WORKFLOW"})

        self.assertEqual(payload["ownerType"], "WORKFLOW")
        self.assertEqual(payload["source"], "custom_source")


if __name__ == "__main__":
    unittest.main()
