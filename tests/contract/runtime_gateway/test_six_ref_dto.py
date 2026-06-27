from __future__ import annotations

import unittest

from app.modules.workflow.domain.runtime_invocation_gateway import (
    RuntimeInvocationGateway,
    RuntimeInvocationRefs,
)


class RuntimeInvocationRefsSixRefDtoTest(unittest.TestCase):
    """Contract: invocation gateway returns the six-ref envelope mandated by spec 213.

    The DTO must expose the six canonical refs: runId, statusRef, eventsRef,
    eventStreamRef, nodesRef, resultRef. Frozen + typed so any drift breaks
    contract before reaching runtime.
    """

    def test_refs_dto_exposes_six_canonical_fields(self) -> None:
        # The DTO must be importable and define exactly these six fields.
        refs = RuntimeInvocationRefs(
            runId=999,
            statusRef="/api/v1/runtime-runs/999",
            eventsRef="/api/v1/runtime-runs/999/events",
            eventStreamRef="/api/v1/runtime-runs/999/events/stream?afterSequence=0",
            nodesRef="/api/v1/runtime-runs/999/nodes",
            resultRef="/api/v1/runtime-runs/999/result",
        )
        self.assertEqual(refs.runId, 999)
        self.assertEqual(refs.statusRef, "/api/v1/runtime-runs/999")
        self.assertEqual(refs.eventsRef, "/api/v1/runtime-runs/999/events")
        self.assertEqual(refs.eventStreamRef, "/api/v1/runtime-runs/999/events/stream?afterSequence=0")
        self.assertEqual(refs.nodesRef, "/api/v1/runtime-runs/999/nodes")
        self.assertEqual(refs.resultRef, "/api/v1/runtime-runs/999/result")

    def test_gateway_start_only_returns_refs_matching_dto_contract(self) -> None:
        service = _FakeService()
        gateway = RuntimeInvocationGateway(service)
        envelope = gateway.start_only(owner_id=1, input_data={})

        # envelope must still surface the six fields and they must be parseable
        # into RuntimeInvocationRefs without loss.
        refs = RuntimeInvocationRefs(
            runId=int(envelope["runId"]),
            statusRef=str(envelope["statusRef"]),
            eventsRef=str(envelope["eventsRef"]),
            eventStreamRef=str(envelope["eventStreamRef"]),
            nodesRef=str(envelope["nodesRef"]),
            resultRef=str(envelope["resultRef"]),
        )
        self.assertEqual(refs.runId, 555)
        self.assertTrue(refs.statusRef.endswith("/runtime-runs/555"))
        self.assertTrue(refs.eventsRef.endswith("/runtime-runs/555/events"))
        self.assertIn("eventStreamRef", envelope["runtimeRefs"])

    def test_refs_dto_serialises_to_camelcase_dict_matching_envelope_keys(self) -> None:
        refs = RuntimeInvocationRefs(
            runId=42,
            statusRef="/a",
            eventsRef="/b",
            eventStreamRef="/c",
            nodesRef="/d",
            resultRef="/e",
        )
        as_dict = refs.to_dict()
        self.assertEqual(
            set(as_dict.keys()),
            {"runId", "statusRef", "eventsRef", "eventStreamRef", "nodesRef", "resultRef"},
        )
        self.assertEqual(as_dict["runId"], 42)


class _FakeService:
    def start_run(self, owner_id, input_data, idempotency_key=None, version_id=None):
        return {
            "runId": 555,
            "status": "RUNNING",
            "statusRef": "/api/v1/runtime-runs/555",
            "eventsRef": "/api/v1/runtime-runs/555/events",
            "eventStreamRef": "/api/v1/runtime-runs/555/events/stream?afterSequence=0",
            "nodesRef": "/api/v1/runtime-runs/555/nodes",
            "resultRef": "/api/v1/runtime-runs/555/result",
        }

    def complete_run(self, run_id): pass
    def resume_run(self, run_id, resume_data, idempotency_key=None): return {}
    def get_result(self, run_id): return {}
    def list_events(self, run_id, after_sequence=0): return {"list": [], "total": 0}


if __name__ == "__main__":
    unittest.main()
