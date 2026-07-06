import hashlib
import os
import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantFileWorkspaceApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_file_workspace_contract",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._workspace_dir = tempfile.TemporaryDirectory()
        self._previous_workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT")
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace_dir.name
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        if self._previous_workspace_root is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = self._previous_workspace_root
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._workspace_dir.cleanup()

    def test_read_list_search_run_without_approval_and_publish_metadata(self) -> None:
        root = Path(self._workspace_dir.name)
        (root / "docs").mkdir()
        (root / "docs" / "alpha.txt").write_text("alpha\nneedle\n", encoding="utf-8")
        (root / "docs" / "beta.txt").write_text("beta\nneedle\n", encoding="utf-8")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "File read"}).json()["data"][
                "id"
            ]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "inspect workspace",
                    "idempotencyKey": "file-read-list-search",
                    "approvalMode": "smart_approval",
                    "toolCalls": [
                        {"toolName": "read_workspace_file", "toolInput": {"path": "docs/alpha.txt"}},
                        {"toolName": "list_workspace_files", "toolInput": {"path": "docs", "pattern": "*.txt"}},
                        {"toolName": "search_workspace_files", "toolInput": {"path": "docs", "query": "needle"}},
                    ],
                },
            )
            approvals = client.get("/api/v1/ai-assistant/approvals").json()["data"]["list"]
            events = client.get(f"/api/v1/ai-assistant/runs/{turn.json()['data']['runId']}/events").json()["data"][
                "list"
            ]

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(approvals, [])
        self.assertEqual(
            [tool["toolName"] for tool in data["toolCalls"]],
            ["read_workspace_file", "list_workspace_files", "search_workspace_files"],
        )
        self.assertEqual(data["toolCalls"][0]["output"]["checksum"], _sha256("alpha\nneedle\n"))
        self.assertEqual(
            [item["path"] for item in data["toolCalls"][1]["output"]["files"]],
            ["docs/alpha.txt", "docs/beta.txt"],
        )
        self.assertEqual(len(data["toolCalls"][2]["output"]["matches"]), 2)
        self.assertNotIn("approval.required", [event["type"] for event in events])
        self.assertIn("tool.call_completed", [event["type"] for event in events])

    def test_list_search_can_omit_path_and_default_to_workspace_root(self) -> None:
        root = Path(self._workspace_dir.name)
        (root / "root.txt").write_text("needle at root\n", encoding="utf-8")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "File root"}).json()["data"][
                "id"
            ]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "inspect workspace root",
                    "idempotencyKey": "file-root-list-search",
                    "approvalMode": "smart_approval",
                    "toolCalls": [
                        {"toolName": "list_workspace_files", "toolInput": {"pattern": "*.txt"}},
                        {"toolName": "search_workspace_files", "toolInput": {"query": "needle", "pattern": "*.txt"}},
                    ],
                },
            )

        self.assertEqual(turn.status_code, 200, turn.text)
        data = turn.json()["data"]
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["toolCalls"][0]["output"]["path"], ".")
        self.assertEqual([item["path"] for item in data["toolCalls"][0]["output"]["files"]], ["root.txt"])
        self.assertEqual(data["toolCalls"][1]["output"]["matches"][0]["path"], "root.txt")

    def test_approved_edit_returns_diff_snapshot_and_inspector_audit(self) -> None:
        root = Path(self._workspace_dir.name)
        target = root / "draft.md"
        target.write_text("old line\nkeep\n", encoding="utf-8")
        checksum = _sha256("old line\nkeep\n")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "File edit"}).json()["data"][
                "id"
            ]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "edit workspace file",
                    "idempotencyKey": "file-edit-approval",
                    "approvalMode": "smart_approval",
                    "toolName": "edit_workspace_file",
                    "toolInput": {
                        "path": "draft.md",
                        "oldText": "old line",
                        "newText": "new line",
                        "expectedChecksum": checksum,
                    },
                },
            )
            approval_id = turn.json()["data"]["approvalId"]
            approved = client.post(
                f"/api/v1/ai-assistant/approvals/{approval_id}/approve",
                json={"actorId": "operator-file"},
            )
            run = client.get(f"/api/v1/ai-assistant/runs/{turn.json()['data']['runId']}").json()["data"]
            inspector = client.get(f"/api/v1/ai-assistant/runs/{turn.json()['data']['runId']}/inspector").json()[
                "data"
            ]

        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(run["status"], "COMPLETED")
        tool = run["result"]["toolCalls"][0]
        self.assertEqual(tool["toolName"], "edit_workspace_file")
        self.assertEqual(tool["status"], "COMPLETED")
        self.assertIn("-old line", tool["output"]["diffPreview"])
        self.assertIn("+new line", tool["output"]["diffPreview"])
        self.assertEqual(tool["output"]["previousChecksum"], checksum)
        self.assertIn("rollbackSnapshot", tool["output"])
        self.assertEqual(target.read_text(encoding="utf-8"), "new line\nkeep\n")
        self.assertEqual(inspector["toolCalls"][0]["output"]["diffPreview"], tool["output"]["diffPreview"])

    def test_workspace_path_escape_is_denied_for_new_file_tools(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "File sandbox"}).json()["data"][
                "id"
            ]
            turn = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "escape workspace",
                    "idempotencyKey": "file-sandbox-escape",
                    "approvalMode": "always_approve",
                    "toolName": "apply_workspace_patch",
                    "toolInput": {
                        "path": "../outside.txt",
                        "operations": [{"oldText": "x", "newText": "y"}],
                    },
                },
            )

        self.assertEqual(turn.status_code, 200, turn.text)
        self.assertEqual(turn.json()["data"]["status"], "DENIED")
        self.assertTrue(turn.json()["data"]["sandboxDenied"])

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    unittest.main()
