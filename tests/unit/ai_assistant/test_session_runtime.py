import unittest


class AiAssistantSessionRuntimeTest(unittest.TestCase):
    def test_checkpoint_payload_tracks_phase_status_cursor_and_request(self) -> None:
        from app.modules.ai_assistant.domain.session_runtime import build_run_checkpoint

        checkpoint = build_run_checkpoint(
            run_id=42,
            status="QUEUED",
            phase="queued",
            last_sequence=7,
            request={"message": "hello", "toolName": "echo_context"},
        )

        self.assertEqual(checkpoint["runId"], 42)
        self.assertEqual(checkpoint["status"], "QUEUED")
        self.assertEqual(checkpoint["phase"], "queued")
        self.assertEqual(checkpoint["streamCursor"]["lastSequence"], 7)
        self.assertEqual(checkpoint["request"]["toolName"], "echo_context")
        self.assertIn("checkpointAt", checkpoint)

    def test_control_transitions_are_explicit_and_auditable(self) -> None:
        from app.modules.ai_assistant.domain.session_runtime import apply_control_transition

        paused = apply_control_transition({"status": "QUEUED"}, action="pause", actor_id="operator")
        resumed = apply_control_transition({"status": "PAUSED"}, action="resume", actor_id="operator")
        cancelled = apply_control_transition({"status": "QUEUED"}, action="cancel", actor_id="operator")

        self.assertEqual(paused["status"], "PAUSED")
        self.assertEqual(paused["control"]["action"], "pause")
        self.assertEqual(resumed["status"], "QUEUED")
        self.assertEqual(resumed["control"]["action"], "resume")
        self.assertEqual(cancelled["status"], "CANCELLED")
        self.assertEqual(cancelled["control"]["action"], "cancel")
        self.assertEqual(cancelled["control"]["actorId"], "operator")


if __name__ == "__main__":
    unittest.main()
