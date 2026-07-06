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


class AiAssistantFileWorkspaceE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_file_workspace_e2e",
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

    def test_file_workspace_edit_patch_and_readback_roundtrip(self) -> None:
        root = Path(self._workspace_dir.name)
        target = root / "story.md"
        target.write_text("title\nfirst draft\nstatus: raw\n", encoding="utf-8")

        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "File E2E"}).json()["data"][
                "id"
            ]
            edit = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "edit story",
                    "idempotencyKey": "file-e2e-edit",
                    "approvalMode": "smart_approval",
                    "toolName": "edit_workspace_file",
                    "toolInput": {
                        "path": "story.md",
                        "oldText": "first draft",
                        "newText": "second draft",
                        "expectedChecksum": _sha256("title\nfirst draft\nstatus: raw\n"),
                    },
                },
            )
            client.post(
                f"/api/v1/ai-assistant/approvals/{edit.json()['data']['approvalId']}/approve",
                json={"actorId": "operator-e2e"},
            )
            after_edit = target.read_text(encoding="utf-8")
            patch = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "patch story",
                    "idempotencyKey": "file-e2e-patch",
                    "approvalMode": "smart_approval",
                    "toolName": "apply_workspace_patch",
                    "toolInput": {
                        "path": "story.md",
                        "expectedChecksum": _sha256(after_edit),
                        "operations": [{"oldText": "status: raw", "newText": "status: reviewed"}],
                    },
                },
            )
            client.post(
                f"/api/v1/ai-assistant/approvals/{patch.json()['data']['approvalId']}/approve",
                json={"actorId": "operator-e2e"},
            )
            readback = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "read story",
                    "idempotencyKey": "file-e2e-readback",
                    "approvalMode": "smart_approval",
                    "toolName": "read_workspace_file",
                    "toolInput": {"path": "story.md"},
                },
            )
            snapshot = client.get(f"/api/v1/ai-assistant/runs/{readback.json()['data']['runId']}/snapshot").json()[
                "data"
            ]

        self.assertEqual(target.read_text(encoding="utf-8"), "title\nsecond draft\nstatus: reviewed\n")
        self.assertEqual(readback.json()["data"]["status"], "COMPLETED")
        output = readback.json()["data"]["toolCalls"][0]["output"]
        self.assertEqual(output["content"], "title\nsecond draft\nstatus: reviewed\n")
        self.assertEqual(output["checksum"], _sha256("title\nsecond draft\nstatus: reviewed\n"))
        self.assertEqual(snapshot["inspector"]["toolCalls"][0]["output"]["checksum"], output["checksum"])

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    unittest.main()
