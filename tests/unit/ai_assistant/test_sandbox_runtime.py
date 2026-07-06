import tempfile
import unittest
from pathlib import Path


class AiAssistantSandboxRuntimeTest(unittest.TestCase):
    def test_session_sandbox_exposes_fixed_paths_env_shell_policy_and_redaction(self) -> None:
        from app.modules.ai_assistant.domain.sandbox_runtime import (
            SessionSandboxConfig,
            SessionSandboxRuntime,
        )

        with tempfile.TemporaryDirectory() as workspace:
            runtime = SessionSandboxRuntime(
                SessionSandboxConfig(
                    workspace_root=Path(workspace),
                    run_temp_root=Path(workspace) / ".ai-assistant" / "runs" / "77" / "tmp",
                    cwd=Path(workspace),
                    env_allowlist=["SAFE_TOKEN"],
                    secret_values=["super-secret"],
                    network_policy="deny",
                    resource_limits={"timeoutMs": 1000},
                    allowed_executables=["node"],
                )
            )

            decision = runtime.evaluate(
                session_id=7,
                run_id=77,
                tool_name="run_shell",
                tool_input={"command": "node tmp/script.mjs"},
                env={"SAFE_TOKEN": "ok", "UNSAFE_TOKEN": "blocked"},
            )

            self.assertEqual(decision.verdict, "allow")
            self.assertEqual(decision.effective_env, {"SAFE_TOKEN": "ok"})
            self.assertEqual(decision.event["type"], "sandbox.evaluated")
            payload = decision.event["payload"]
            self.assertEqual(payload["sessionId"], 7)
            self.assertEqual(payload["runId"], 77)
            self.assertEqual(payload["toolName"], "run_shell")
            self.assertEqual(payload["cwd"], workspace)
            self.assertEqual(payload["workspaceRoot"], workspace)
            self.assertTrue(payload["runTempRoot"].endswith(".ai-assistant/runs/77/tmp"))
            self.assertEqual(payload["allowedExecutables"], ["node"])
            self.assertEqual(payload["networkPolicy"], "deny")
            self.assertFalse(payload["redactionApplied"])
            self.assertEqual(runtime.redact_text("value=super-secret"), "value=[REDACTED]")

    def test_session_sandbox_denies_non_node_shell_and_paths_outside_workspace(self) -> None:
        from app.modules.ai_assistant.domain.sandbox_runtime import (
            SessionSandboxConfig,
            SessionSandboxRuntime,
        )

        with tempfile.TemporaryDirectory() as workspace:
            runtime = SessionSandboxRuntime(
                SessionSandboxConfig(
                    workspace_root=Path(workspace),
                    run_temp_root=Path(workspace) / ".ai-assistant" / "runs" / "88" / "tmp",
                    cwd=Path(workspace),
                    allowed_executables=["node"],
                )
            )
            shell = runtime.evaluate(
                session_id=8,
                run_id=88,
                tool_name="run_shell",
                tool_input={"command": "python tmp/script.py"},
            )
            file_write = runtime.evaluate(
                session_id=8,
                run_id=88,
                tool_name="write_workspace_file",
                tool_input={"path": "../outside.txt", "content": "x"},
            )

            self.assertEqual(shell.verdict, "deny")
            self.assertIn("not allowed", shell.reason)
            self.assertEqual(shell.event["payload"]["allowedExecutables"], ["node"])
            self.assertEqual(file_write.verdict, "deny")
            self.assertIn("workspace", file_write.reason)

    def test_session_sandbox_denies_node_preload_flags(self) -> None:
        from app.modules.ai_assistant.domain.sandbox_runtime import (
            SessionSandboxConfig,
            SessionSandboxRuntime,
        )

        with tempfile.TemporaryDirectory() as workspace:
            runtime = SessionSandboxRuntime(
                SessionSandboxConfig(
                    workspace_root=Path(workspace),
                    run_temp_root=Path(workspace) / ".ai-assistant" / "runs" / "89" / "tmp",
                    cwd=Path(workspace),
                    allowed_executables=["node"],
                )
            )

            for command in (
                "node --import /tmp/escape.mjs tmp/script.mjs",
                "node --loader /tmp/escape.mjs tmp/script.mjs",
                "node -r /tmp/escape.cjs tmp/script.mjs",
                "node --require /tmp/escape.cjs tmp/script.mjs",
            ):
                with self.subTest(command=command):
                    decision = runtime.evaluate(
                        session_id=8,
                        run_id=89,
                        tool_name="run_shell",
                        tool_input={"command": command},
                    )

                    self.assertEqual(decision.verdict, "deny")
                    self.assertIn("preload", decision.reason)


if __name__ == "__main__":
    unittest.main()
