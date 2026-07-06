import hashlib
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


class AiAssistantFileWorkspaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self._workspace = tempfile.TemporaryDirectory()
        self._previous_workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT")
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace.name

    def tearDown(self) -> None:
        if self._previous_workspace_root is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = self._previous_workspace_root
        self._workspace.cleanup()

    def test_registry_exposes_complete_workspace_tool_surface(self) -> None:
        from app.modules.ai_assistant.domain.tools import RiskLevel, ToolRegistry

        registry = ToolRegistry.with_builtin_tools()

        expected = {
            "read_workspace_file": RiskLevel.READ,
            "list_workspace_files": RiskLevel.READ,
            "search_workspace_files": RiskLevel.READ,
            "edit_workspace_file": RiskLevel.BUSINESS_WRITE,
            "write_workspace_file": RiskLevel.BUSINESS_WRITE,
            "apply_workspace_patch": RiskLevel.BUSINESS_WRITE,
        }
        for tool_name, risk_level in expected.items():
            manifest = registry.get_manifest(tool_name)
            self.assertEqual(manifest.risk_level, risk_level)
            self.assertIn("path", manifest.input_schema["properties"])

    def test_read_list_and_search_return_file_metadata(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        root = Path(self._workspace.name)
        (root / "notes").mkdir()
        (root / "notes" / "alpha.txt").write_text("alpha\nneedle one\n", encoding="utf-8")
        (root / "notes" / "beta.txt").write_text("beta\nneedle two\n", encoding="utf-8")

        registry = ToolRegistry.with_builtin_tools()
        read = registry.dispatch("read_workspace_file", {"path": "notes/alpha.txt"})
        listed = registry.dispatch("list_workspace_files", {"path": "notes", "pattern": "*.txt"})
        searched = registry.dispatch("search_workspace_files", {"path": "notes", "query": "needle"})

        self.assertEqual(read.status, "COMPLETED")
        self.assertEqual(read.output["checksum"], _sha256("alpha\nneedle one\n"))
        self.assertGreater(read.output["mtimeNs"], 0)
        self.assertEqual(read.output["sizeBytes"], len("alpha\nneedle one\n"))
        self.assertEqual(listed.status, "COMPLETED")
        self.assertEqual(
            [item["path"] for item in listed.output["files"]],
            ["notes/alpha.txt", "notes/beta.txt"],
        )
        self.assertEqual(searched.status, "COMPLETED")
        self.assertEqual(
            [(match["path"], match["lineNumber"]) for match in searched.output["matches"]],
            [("notes/alpha.txt", 2), ("notes/beta.txt", 2)],
        )

    def test_list_and_search_can_default_to_workspace_root_through_sandbox(self) -> None:
        from app.modules.ai_assistant.domain.sandbox import SandboxPolicy, SandboxVerdict
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        root = Path(self._workspace.name)
        (root / "root.txt").write_text("needle at root\n", encoding="utf-8")
        registry = ToolRegistry.with_builtin_tools()

        list_decision = SandboxPolicy().evaluate("list_workspace_files", {"pattern": "*.txt"})
        search_decision = SandboxPolicy().evaluate("search_workspace_files", {"query": "needle", "pattern": "*.txt"})
        listed = registry.dispatch("list_workspace_files", {"pattern": "*.txt"})
        searched = registry.dispatch("search_workspace_files", {"query": "needle", "pattern": "*.txt"})

        self.assertEqual(list_decision.verdict, SandboxVerdict.ALLOW)
        self.assertEqual(search_decision.verdict, SandboxVerdict.ALLOW)
        self.assertEqual([item["path"] for item in listed.output["files"]], ["root.txt"])
        self.assertEqual([(match["path"], match["lineNumber"]) for match in searched.output["matches"]], [("root.txt", 1)])

    def test_write_uses_preconditions_atomic_write_and_rollback_snapshot(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        root = Path(self._workspace.name)
        target = root / "draft.md"
        target.write_text("old content\n", encoding="utf-8")
        old_checksum = _sha256("old content\n")
        registry = ToolRegistry.with_builtin_tools()

        written = registry.dispatch(
            "write_workspace_file",
            {"path": "draft.md", "content": "new content\n", "expectedChecksum": old_checksum},
        )
        stale = registry.dispatch(
            "write_workspace_file",
            {"path": "draft.md", "content": "stale overwrite\n", "expectedChecksum": old_checksum},
        )

        self.assertEqual(written.status, "COMPLETED")
        self.assertEqual(target.read_text(encoding="utf-8"), "new content\n")
        self.assertEqual(written.output["previousChecksum"], old_checksum)
        self.assertEqual(written.output["checksum"], _sha256("new content\n"))
        snapshot = root / written.output["rollbackSnapshot"]["path"]
        self.assertTrue(snapshot.exists())
        self.assertEqual(snapshot.read_text(encoding="utf-8"), "old content\n")
        self.assertTrue(written.output["atomic"])
        self.assertEqual(stale.status, "PRECONDITION_FAILED")
        self.assertEqual(target.read_text(encoding="utf-8"), "new content\n")

    def test_edit_supports_context_whitespace_preview_and_unique_match_checks(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        root = Path(self._workspace.name)
        target = root / "edit.md"
        target.write_text("alpha\nmarker one\nbeta\nmarker one\ngamma\n", encoding="utf-8")
        registry = ToolRegistry.with_builtin_tools()

        duplicate = registry.dispatch(
            "edit_workspace_file",
            {"path": "edit.md", "oldText": "marker one", "newText": "replaced"},
        )
        preview = registry.dispatch(
            "edit_workspace_file",
            {
                "path": "edit.md",
                "oldText": "marker one",
                "newText": "replaced",
                "beforeContext": "beta\n",
                "afterContext": "\ngamma",
                "dryRun": True,
            },
        )
        self.assertEqual(preview.status, "PREVIEW")
        self.assertIn("-marker one", preview.output["diffPreview"])
        self.assertIn("+replaced", preview.output["diffPreview"])
        self.assertEqual(target.read_text(encoding="utf-8"), "alpha\nmarker one\nbeta\nmarker one\ngamma\n")
        edited = registry.dispatch(
            "edit_workspace_file",
            {
                "path": "edit.md",
                "oldText": "marker one",
                "newText": "replaced",
                "beforeContext": "beta\n",
                "afterContext": "\ngamma",
            },
        )
        whitespace_target = root / "whitespace.md"
        whitespace_target.write_text("hello    world\n", encoding="utf-8")
        whitespace = registry.dispatch(
            "edit_workspace_file",
            {
                "path": "whitespace.md",
                "oldText": "hello world",
                "newText": "hello there",
                "whitespaceTolerant": True,
            },
        )

        self.assertEqual(duplicate.status, "FAILED")
        self.assertEqual(duplicate.output["error"]["code"], "NON_UNIQUE_MATCH")
        self.assertEqual(edited.status, "COMPLETED")
        self.assertEqual(target.read_text(encoding="utf-8"), "alpha\nmarker one\nbeta\nreplaced\ngamma\n")
        self.assertEqual(whitespace.status, "COMPLETED")
        self.assertEqual(whitespace_target.read_text(encoding="utf-8"), "hello there\n")

    def test_apply_patch_and_file_lock_prevent_lost_update(self) -> None:
        from app.modules.ai_assistant.domain.tools import ToolRegistry

        root = Path(self._workspace.name)
        target = root / "patch.md"
        target.write_text("one\ntwo\n", encoding="utf-8")
        registry = ToolRegistry.with_builtin_tools()
        patch = registry.dispatch(
            "apply_workspace_patch",
            {
                "path": "patch.md",
                "operations": [
                    {"oldText": "one", "newText": "uno"},
                    {"oldText": "two", "newText": "dos"},
                ],
                "expectedChecksum": _sha256("one\ntwo\n"),
            },
        )
        race_target = root / "race.md"
        race_target.write_text("start\n", encoding="utf-8")
        race_checksum = _sha256("start\n")

        def write(content: str):
            return registry.dispatch(
                "write_workspace_file",
                {"path": "race.md", "content": content, "expectedChecksum": race_checksum},
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(write, ["winner-a\n", "winner-b\n"]))

        self.assertEqual(patch.status, "COMPLETED")
        self.assertEqual(target.read_text(encoding="utf-8"), "uno\ndos\n")
        self.assertEqual(patch.output["operationCount"], 2)
        self.assertIn("-one", patch.output["diffPreview"])
        self.assertIn("+uno", patch.output["diffPreview"])
        self.assertEqual([result.status for result in results].count("COMPLETED"), 1)
        self.assertEqual([result.status for result in results].count("PRECONDITION_FAILED"), 1)
        self.assertIn(race_target.read_text(encoding="utf-8"), {"winner-a\n", "winner-b\n"})


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


if __name__ == "__main__":
    unittest.main()
